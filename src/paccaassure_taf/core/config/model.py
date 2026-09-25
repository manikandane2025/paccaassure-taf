"""Typed core configuration (``PatafConfig``) — validated after layers are merged.

Every section forbids unknown keys, so a typo (``loging:``) is an error that names the
file it came from instead of a silently ignored setting.

Example:
    >>> config = PatafConfig.model_validate({"env": "qa", "logging": {"level": "DEBUG"}})
    >>> config.env, config.logging.level.value, config.wait.timeout_s
    ('qa', 'DEBUG', 30.0)
"""

import re
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat, PositiveInt, field_validator

from paccaassure_taf.core.log import LogFormat, LogLevel
from paccaassure_taf.core.masking import DEFAULT_MAX_LEARNED_VALUES, MASK
from paccaassure_taf.core.secrets import SecretRef

__all__ = [
    "LicenseConfig",
    "LoggingConfig",
    "MaskingConfig",
    "PatafConfig",
    "SecretsConfig",
    "UserCredentials",
    "WaitConfig",
]

Slug = Annotated[str, Field(pattern=r"^[a-z][a-z0-9-]*$", max_length=64)]
RoleName = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)]  # matches UserRole values


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LoggingConfig(_Section):
    """``logging:`` — level and output format.

    Example:
        >>> LoggingConfig(level=LogLevel.DEBUG).format.value
        'console'
    """

    level: LogLevel = LogLevel.INFO
    format: LogFormat = LogFormat.CONSOLE


class WaitConfig(_Section):
    """``wait:`` — defaults for ``wait.until`` and driver timeouts.

    Example:
        >>> WaitConfig().interval_s
        0.25
    """

    timeout_s: PositiveFloat = 30.0
    interval_s: PositiveFloat = 0.25


class MaskingConfig(_Section):
    r"""``masking:`` — masking is always on; this only adds patterns or changes the mask text.

    Example:
        >>> MaskingConfig(extra_patterns=[r"NWH-M\d{6}"]).mask
        '***'
    """

    mask: str = Field(default=MASK, min_length=1)
    extra_patterns: list[str] = Field(default_factory=list)
    max_learned_values: PositiveInt = DEFAULT_MAX_LEARNED_VALUES

    @field_validator("extra_patterns")
    @classmethod
    def _patterns_compile(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as error:
                raise ValueError(f"invalid regular expression {pattern!r}: {error}") from error
        return patterns


class SecretsConfig(_Section):
    """``secrets:`` — ``allow_file_refs`` defaults to "yes locally, never in CI".

    Example:
        >>> SecretsConfig().allow_file_refs is None
        True
    """

    allow_file_refs: bool | None = None


class LicenseConfig(_Section):
    """``license:`` — where the signed license file is (checked only at CLI entry points).

    Example:
        >>> LicenseConfig().file is None
        True
    """

    file: Path | None = None


class UserCredentials(_Section):
    """One role's credentials: a username and a *reference* to its password.

    Example:
        >>> UserCredentials(username="eligibility_worker", password="env://EW_PASSWORD").password.path
        'EW_PASSWORD'
    """

    username: str = Field(min_length=1)
    password: SecretRef


class PatafConfig(_Section):
    """Root configuration. App packs and variant suites add sections via plugins (Phase 2).

    Example:
        >>> PatafConfig().env
        'local'
    """

    project: Slug = "default"
    app: Slug | None = None
    variant: Slug | None = None
    env: Slug = "local"
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    wait: WaitConfig = Field(default_factory=WaitConfig)
    masking: MaskingConfig = Field(default_factory=MaskingConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    license: LicenseConfig = Field(default_factory=LicenseConfig)
    users: dict[RoleName, UserCredentials] = Field(default_factory=dict)
