"""Sensitive-data marking and masking (ADR-0009, CONFIG_SECRETS_DATA).

Mark model fields with ``Sensitive[T]``; the type stays ``T`` for mypy and pydantic,
but every value that flows through a :class:`Masker` (logs, result events, evidence,
reports, sink payloads) is replaced by ``***`` before it is written anywhere.

Example:
    >>> from pydantic import BaseModel
    >>> class Member(BaseModel):
    ...     member_id: str
    ...     first_name: Sensitive[str]
    >>> Masker().mask(Member(member_id="NWH-M000001", first_name="Avery"))
    {'member_id': 'NWH-M000001', 'first_name': '***'}
"""

import re
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum, StrEnum
from functools import cache
from pathlib import PurePath
from typing import Annotated, Final, TypeVar

from pydantic import BaseModel, SecretBytes, SecretStr

__all__ = [
    "DEFAULT_PATTERNS",
    "DEFAULT_SENSITIVE_KEYS",
    "MASK",
    "JsonValue",
    "Masker",
    "Sensitive",
    "SensitiveCategory",
    "SensitiveMarker",
    "default_masker",
    "is_sensitive_field",
]

T = TypeVar("T")

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None
"""A JSON-serializable value — the output type of :meth:`Masker.mask`."""

MASK: Final = "***"


class SensitiveCategory(StrEnum):
    """Why a value is sensitive (reported in data dictionaries; masking is identical).

    Example:
        >>> SensitiveCategory.PHI.value
        'phi'
    """

    PII = "pii"
    PHI = "phi"
    PCI = "pci"
    SECRET = "secret"  # noqa: S105 - a category name, not a credential


@dataclass(frozen=True)
class SensitiveMarker:
    """Annotation metadata that flags a model field as sensitive.

    Use via ``Sensitive[T]`` (PII by default) or ``Annotated[T, SensitiveMarker(SensitiveCategory.PHI)]``.

    Example:
        >>> from typing import Annotated
        >>> Dob = Annotated[date, SensitiveMarker(SensitiveCategory.PHI)]
    """

    category: SensitiveCategory = SensitiveCategory.PII


Sensitive = Annotated[T, SensitiveMarker()]
"""Mark a field as sensitive: ``first_name: Sensitive[str]``. The value type is unchanged."""

# Free-text patterns masked everywhere (defense in depth; typed marking is the primary control).
DEFAULT_PATTERNS: Final[tuple[str, ...]] = (
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN-shaped
    r"(?i)\bbearer\s+[a-z0-9._~+/=-]{8,}",  # bearer tokens
    r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key)\s*[=:]\s*[^\s,;&]+",  # key=value credentials
)
_CARD_CANDIDATE: Final = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")

# Mapping keys whose values are always masked, whatever their type.
DEFAULT_SENSITIVE_KEYS: Final = frozenset(
    {"password", "passwd", "pwd", "secret", "token", "access_token", "refresh_token", "api_key", "apikey",
     "authorization", "cookie", "set-cookie", "client_secret", "private_key"}
)  # fmt: skip


def is_sensitive_field(model_type: type[BaseModel], field_name: str) -> bool:
    """Return True if ``field_name`` on ``model_type`` is annotated ``Sensitive[...]``.

    Example:
        >>> class M(BaseModel):
        ...     ssn: Sensitive[str]
        ...     plan: str
        >>> is_sensitive_field(M, "ssn"), is_sensitive_field(M, "plan")
        (True, False)
    """
    field = model_type.model_fields.get(field_name)
    return field is not None and any(isinstance(meta, SensitiveMarker) for meta in field.metadata)


# (prefix regex, allowed lengths) for major card brands. Luhn alone matches ~10% of all digit strings,
# so without a brand check long numeric ids (run ids, timestamps) would be masked in logs.
_CARD_BRANDS: Final[tuple[tuple[re.Pattern[str], frozenset[int]], ...]] = (
    (re.compile(r"4"), frozenset({13, 16, 19})),  # Visa
    (re.compile(r"5[1-5]|2(?:2[2-9][1-9]|2[3-9]\d|[3-6]\d\d|7[01]\d|720)"), frozenset({16})),  # Mastercard
    (re.compile(r"3[47]"), frozenset({15})),  # Amex
    (re.compile(r"6(?:011|5|4[4-9])"), frozenset({16, 19})),  # Discover
)


def _looks_like_card(digits: str) -> bool:
    return any(
        prefix.match(digits) and len(digits) in lengths for prefix, lengths in _CARD_BRANDS
    ) and _luhn_valid(digits)


def _luhn_valid(digits: str) -> bool:
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value = value * 2 - 9 if value > 4 else value * 2  # noqa: PLR2004 - Luhn doubling rule
        total += value
    return total % 10 == 0


class Masker:
    """Masks sensitive data in structured values and free text.

    Args:
        patterns: Regexes whose matches are masked in any text.
        sensitive_keys: Mapping keys whose values are always masked (case-insensitive).
        mask: Replacement text.
        min_value_length: Registered values shorter than this are not scrubbed from text
            (avoids masking every "a" or "1" in a log line).

    Example:
        >>> masker = Masker()
        >>> masker.register("s3cr3t-value")
        >>> masker.scrub("login failed for s3cr3t-value")
        'login failed for ***'
    """

    def __init__(
        self,
        *,
        patterns: Iterable[str] = DEFAULT_PATTERNS,
        sensitive_keys: Iterable[str] = DEFAULT_SENSITIVE_KEYS,
        mask: str = MASK,
        min_value_length: int = 4,
    ) -> None:
        self.mask_text = mask
        self._patterns = [re.compile(p) for p in patterns]
        self._sensitive_keys = frozenset(k.lower() for k in sensitive_keys)
        self._min_value_length = min_value_length
        self._values: set[str] = set()
        self._values_regex: re.Pattern[str] | None = None
        self._lock = threading.Lock()

    def register(self, value: str) -> None:
        """Remember a sensitive literal (e.g. a resolved secret) so it is scrubbed from all text.

        Example:
            >>> m = Masker()
            >>> m.register("hunter22")
            >>> m.scrub("pw is hunter22")
            'pw is ***'
        """
        if len(value) < self._min_value_length:
            return
        with self._lock:
            if value not in self._values:
                self._values.add(value)
                ordered = sorted(self._values, key=len, reverse=True)  # longest first: no partial leftovers
                self._values_regex = re.compile("|".join(re.escape(v) for v in ordered))

    def scrub(self, text: str) -> str:
        """Mask registered values, known patterns and Luhn-valid card numbers in free text.

        Example:
            >>> Masker().scrub("ssn 900-12-3456, card 4111 1111 1111 1111, run 20260924101500")
            'ssn ***, card ***, run 20260924101500'
        """
        regex = self._values_regex
        if regex is not None:
            text = regex.sub(self.mask_text, text)
        for pattern in self._patterns:
            text = pattern.sub(self.mask_text, text)
        return _CARD_CANDIDATE.sub(self._mask_card, text)

    def _mask_card(self, match: re.Match[str]) -> str:
        digits = re.sub(r"[ -]", "", match.group(0))
        return self.mask_text if _looks_like_card(digits) else match.group(0)

    def mask(self, value: object, *, learn: bool = True) -> JsonValue:
        """Return a JSON-safe copy of ``value`` with every sensitive part masked.

        Pydantic models: ``Sensitive[...]`` fields are masked (and, with ``learn=True``,
        their values are registered so they are also scrubbed from later free text).
        ``SecretStr``/``SecretBytes`` are always masked. Mappings mask values under
        sensitive keys. Strings are scrubbed.

        Example:
            >>> Masker().mask({"user": "eligibility_worker", "password": "pw-123456", "tags": ["@smoke"]})
            {'user': 'eligibility_worker', 'password': '***', 'tags': ['@smoke']}
        """
        return self._mask(value, learn=learn)

    def _mask(self, value: object, *, learn: bool) -> JsonValue:  # noqa: PLR0911 - one branch per type
        if value is None or isinstance(value, bool | int | float):
            return value
        if isinstance(value, SecretStr | SecretBytes):
            if learn and isinstance(value, SecretStr):
                self.register(value.get_secret_value())
            return self.mask_text
        if isinstance(value, str):
            return self.scrub(value)
        if isinstance(value, BaseModel):
            return self._mask_model(value, learn=learn)
        if isinstance(value, Mapping):
            return {
                str(key): self.mask_text
                if str(key).lower() in self._sensitive_keys
                else self._mask(item, learn=learn)
                for key, item in value.items()
            }
        if isinstance(value, list | tuple | set | frozenset):
            return [self._mask(item, learn=learn) for item in value]
        if isinstance(value, Enum):
            return self._mask(value.value, learn=learn)
        if isinstance(value, datetime | date | time):
            return value.isoformat()
        if isinstance(value, Decimal | PurePath):
            return str(value)
        return self.scrub(repr(value))

    def _mask_model(self, model: BaseModel, *, learn: bool) -> dict[str, JsonValue]:
        result: dict[str, JsonValue] = {}
        for name, field in type(model).model_fields.items():
            item = getattr(model, name)
            if any(isinstance(meta, SensitiveMarker) for meta in field.metadata):
                if learn and item is not None:
                    self._learn(item)
                result[name] = self.mask_text
            else:
                result[name] = self._mask(item, learn=learn)
        return result

    def _learn(self, value: object) -> None:
        if isinstance(value, SecretStr):
            self.register(value.get_secret_value())
        elif isinstance(value, datetime | date | time):
            self.register(value.isoformat())
        elif isinstance(value, str | int | Decimal):
            self.register(str(value))


@cache
def default_masker() -> Masker:
    """Return the process-wide masker shared by logging, results and secret resolution.

    Example:
        >>> default_masker() is default_masker()
        True
    """
    return Masker()
