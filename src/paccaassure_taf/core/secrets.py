"""Secret references and resolution (ADR-0009, CONFIG_SECRETS_DATA).

Config files only ever contain *references* (``SecretRef``) such as ``env://DB_PASSWORD``
or ``kv://northwind-qa/claims-db-password``. A :class:`SecretResolver` turns a reference
into a ``SecretStr`` on first use, caches it for the process, and registers the value with
the masker so it can never appear in a log, report or sink payload.

Example:
    >>> resolver = SecretResolver([EnvSecretProvider({"DB_PASSWORD": "pw-Northwind-1"})])
    >>> secret = resolver.resolve("env://DB_PASSWORD")
    >>> secret
    SecretStr('**********')
    >>> secret.get_secret_value()
    'pw-Northwind-1'
"""

import re
import threading
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import ClassVar, Final, Self, override

from pydantic import BaseModel, ConfigDict, SecretStr, ValidationError, model_serializer, model_validator

from paccaassure_taf.core.errors import SecretError
from paccaassure_taf.core.masking import Masker, default_masker
from paccaassure_taf.core.plugins import PluginKind, PluginRegistry

__all__ = [
    "EnvSecretProvider",
    "FileSecretProvider",
    "SecretProvider",
    "SecretRef",
    "SecretResolver",
    "SecretScheme",
    "build_secret_resolver",
]


class SecretScheme(StrEnum):
    """Where a secret lives.

    Example:
        >>> SecretScheme("kv") is SecretScheme.KEY_VAULT
        True
    """

    ENV = "env"
    KEY_VAULT = "kv"
    HASHICORP_VAULT = "hcv"
    FILE = "file"


_REF_PATTERN: Final = re.compile(r"^(?P<scheme>[a-z]+)://(?P<path>[^#\s]+)(?:#(?P<key>[^#\s]+))?$")
_ENV_NAME: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FORMS: Final = "env://VAR, kv://<vault>/<name>, hcv://<path>#<key>, file://<path>"


class SecretRef(BaseModel):
    """A typed pointer to a secret. Validates from and serializes to its string form.

    Example:
        >>> ref = SecretRef.parse("kv://northwind-qa/claims-db-password")
        >>> ref.scheme, ref.path, str(ref)
        (<SecretScheme.KEY_VAULT: 'kv'>, 'northwind-qa/claims-db-password', 'kv://northwind-qa/claims-db-password')
    """

    model_config = ConfigDict(frozen=True)

    scheme: SecretScheme
    path: str
    key: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _from_string(cls, data: object) -> object:
        if not isinstance(data, str):
            return data
        match = _REF_PATTERN.match(data.strip())
        if match is None:
            # Never echo the value: a misplaced value may itself be a plaintext secret.
            raise ValueError(f"value is not a secret reference (value hidden). Expected one of: {_FORMS}")
        return match.groupdict()

    @model_validator(mode="after")
    def _check_shape(self) -> Self:
        if self.scheme is SecretScheme.ENV and not _ENV_NAME.match(self.path):
            raise ValueError("env:// needs an environment variable name ([A-Za-z_][A-Za-z0-9_]*)")
        if self.scheme is SecretScheme.KEY_VAULT and self.path.count("/") != 1:
            raise ValueError("kv:// needs exactly '<vault>/<name>'")
        if self.scheme is SecretScheme.HASHICORP_VAULT and not self.key:
            raise ValueError("hcv:// needs '<path>#<key>'")
        return self

    @model_serializer
    def _to_string(self) -> str:
        return str(self)

    @classmethod
    def parse(cls, text: str) -> "SecretRef":
        """Parse a reference string, raising an actionable SecretError if it is malformed.

        Example:
            >>> SecretRef.parse("env://DB_PASSWORD").scheme
            <SecretScheme.ENV: 'env'>
        """
        try:
            return cls.model_validate(text)
        except ValidationError as error:
            details = "; ".join(str(e["msg"]) for e in error.errors())
            raise SecretError(
                "Invalid secret reference (value hidden)", cause=details, fix=f"Use {_FORMS}."
            ) from error

    @override
    def __str__(self) -> str:
        return f"{self.scheme.value}://{self.path}" + (f"#{self.key}" if self.key else "")


class SecretProvider(ABC):
    """Resolves references of one scheme. Plugin providers must be constructible without arguments.

    Example:
        >>> class Fixed(SecretProvider):
        ...     scheme = SecretScheme.HASHICORP_VAULT
        ...     def fetch(self, ref: SecretRef) -> SecretStr:
        ...         return SecretStr("pw-Northwind-2")
    """

    scheme: ClassVar[SecretScheme]

    @abstractmethod
    def fetch(self, ref: SecretRef) -> SecretStr:
        """Return the secret value, or raise SecretError with an actionable message."""


class EnvSecretProvider(SecretProvider):
    """Resolves ``env://VAR`` from an injected environment mapping.

    Args:
        environ: The process environment (supplied by ``core.config``, the only module that reads it).

    Example:
        >>> EnvSecretProvider({"TOKEN": "tok-Northwind"}).fetch(SecretRef.parse("env://TOKEN"))
        SecretStr('**********')
    """

    scheme = SecretScheme.ENV

    def __init__(self, environ: Mapping[str, str]) -> None:
        self._environ = environ

    @override
    def fetch(self, ref: SecretRef) -> SecretStr:
        value = self._environ.get(ref.path)
        if value is None:
            raise SecretError(
                f"Secret {ref} is not set",
                cause=f"environment variable {ref.path} is not defined in this process",
                fix=f"Set {ref.path} (CI: map it from your secret store / service connection).",
            )
        return SecretStr(value)


class FileSecretProvider(SecretProvider):
    """Resolves ``file://path`` — local development only; blocked in CI.

    Args:
        allowed: False in CI, where secrets must come from a real secret store.
        base_dir: Relative paths resolve against this directory (default: current directory).

    Example:
        >>> provider = FileSecretProvider(allowed=False)  # as in CI: file:// refs raise SecretError
        >>> provider.scheme.value
        'file'
    """

    scheme = SecretScheme.FILE

    def __init__(self, *, allowed: bool, base_dir: Path | None = None) -> None:
        self._allowed = allowed
        self._base_dir = base_dir or Path.cwd()

    @override
    def fetch(self, ref: SecretRef) -> SecretStr:
        if not self._allowed:
            raise SecretError(
                f"file:// secrets are blocked in CI ({ref})",
                cause="file references are for local development only (CONFIG_SECRETS_DATA)",
                fix="Use kv://, hcv:// or env:// in CI configuration.",
            )
        path = Path(ref.path)
        path = path if path.is_absolute() else self._base_dir / path
        try:
            return SecretStr(path.read_text(encoding="utf-8").rstrip("\r\n"))
        except OSError as error:
            raise SecretError(
                f"Secret {ref} could not be read",
                cause=f"{type(error).__name__} for {path}",
                fix="Create the file (never commit it) or point the reference at the right path.",
            ) from error


_MISSING_SCHEME_FIX: Final = {
    SecretScheme.KEY_VAULT: "Install the extra: paccaassure-taf-core[secrets-azure].",
    SecretScheme.HASHICORP_VAULT: "Install a SecretProvider plugin for hcv:// (not shipped in core yet).",
}


class SecretResolver:
    """Resolves references through providers; caches per process; registers values for masking.

    Example:
        >>> resolver = SecretResolver([EnvSecretProvider({"A": "pw-Northwind-3"})])
        >>> resolver.resolve(SecretRef.parse("env://A")).get_secret_value()
        'pw-Northwind-3'
    """

    def __init__(self, providers: Iterable[SecretProvider], *, masker: Masker | None = None) -> None:
        self._providers = {provider.scheme: provider for provider in providers}
        self._masker = masker or default_masker()
        self._cache: dict[str, SecretStr] = {}
        self._lock = threading.Lock()

    @property
    def schemes(self) -> frozenset[SecretScheme]:
        """The schemes this resolver can serve.

        Example:
            >>> SecretResolver([EnvSecretProvider({})]).schemes
            frozenset({<SecretScheme.ENV: 'env'>})
        """
        return frozenset(self._providers)

    def resolve(self, ref: SecretRef | str) -> SecretStr:
        """Return the secret for ``ref`` (a SecretRef or its string form).

        Raises:
            SecretError: If the reference is malformed, no provider serves its scheme, or the provider fails.

        Example:
            >>> SecretResolver([]).resolve("kv://northwind-qa/db")  # doctest: +SKIP
            Traceback (most recent call last):
            paccaassure_taf.core.errors.SecretError: No secret provider for kv:// ...
        """
        parsed = SecretRef.parse(ref) if isinstance(ref, str) else ref
        cache_key = str(parsed)
        with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        provider = self._providers.get(parsed.scheme)
        if provider is None:
            raise SecretError(
                f"No secret provider for {parsed.scheme.value}:// (needed by {parsed})",
                cause=f"available: {', '.join(sorted(s.value for s in self._providers)) or 'none'}",
                fix=_MISSING_SCHEME_FIX.get(
                    parsed.scheme, "Install a SecretProvider plugin for this scheme."
                ),
            )
        try:
            secret = provider.fetch(parsed)
        except SecretError:
            raise
        except Exception as error:
            raise SecretError(
                f"Secret provider for {parsed.scheme.value}:// failed on {parsed}",
                cause=f"{type(error).__name__}: {self._masker.scrub(str(error))}",
                fix="Check access to the secret store (identity, network, permissions) and the secret name.",
            ) from error
        self._masker.register(secret.get_secret_value())
        with self._lock:
            self._cache[cache_key] = secret
        return secret


def build_secret_resolver(
    *,
    environ: Mapping[str, str],
    allow_file_refs: bool,
    base_dir: Path | None = None,
    registry: PluginRegistry[SecretProvider] | None = None,
    masker: Masker | None = None,
) -> SecretResolver:
    """Build the standard resolver: env + file built in, plus every installed provider plugin.

    Args:
        environ: Process environment (from ``core.config``).
        allow_file_refs: False in CI.
        base_dir: Base for relative ``file://`` paths.
        registry: Secret-provider plugins (default: installed entry points).
        masker: Masker to register resolved values with.

    Example:
        >>> resolver = build_secret_resolver(environ={}, allow_file_refs=True)
        >>> SecretScheme.ENV in resolver.schemes
        True
    """
    plugins = registry or PluginRegistry[SecretProvider](PluginKind.SECRET_PROVIDER, SecretProvider)
    providers: list[SecretProvider] = [
        EnvSecretProvider(environ),
        FileSecretProvider(allowed=allow_file_refs, base_dir=base_dir),
    ]
    providers.extend(plugins.get(name)() for name in plugins.names())
    return SecretResolver(providers, masker=masker)
