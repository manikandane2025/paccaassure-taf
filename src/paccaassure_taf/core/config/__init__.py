"""Layered, typed configuration with provenance (CONFIG_SECRETS_DATA, LAYERING, ADR-0015).

This package is the only place allowed to read the process environment.

Example:
    >>> from pathlib import Path
    >>> from paccaassure_taf.core.config import load_config
    >>> resolved = load_config(Path("."), overrides={"logging.level": "DEBUG"}, environ={})
    >>> resolved.config.logging.level.value, resolved.source_of("logging.level")
    ('DEBUG', 'cli')
"""

from paccaassure_taf.core.config.environment import is_ci, process_environment
from paccaassure_taf.core.config.loader import (
    APP_FILE,
    ENV_DIR,
    ENV_PREFIX,
    VARIANT_FILE,
    ConfigEntry,
    ConfigLayer,
    ResolvedConfig,
    load_config,
)
from paccaassure_taf.core.config.model import (
    LicenseConfig,
    LoggingConfig,
    MaskingConfig,
    PatafConfig,
    SecretsConfig,
    UserCredentials,
    WaitConfig,
)

__all__ = [
    "APP_FILE",
    "ENV_DIR",
    "ENV_PREFIX",
    "VARIANT_FILE",
    "ConfigEntry",
    "ConfigLayer",
    "LicenseConfig",
    "LoggingConfig",
    "MaskingConfig",
    "PatafConfig",
    "ResolvedConfig",
    "SecretsConfig",
    "UserCredentials",
    "WaitConfig",
    "is_ci",
    "load_config",
    "process_environment",
]
