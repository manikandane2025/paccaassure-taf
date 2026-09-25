"""PaccaAssureTAF error hierarchy and process exit codes.

Every framework error is *actionable*: it states what failed, the likely cause,
and how to fix it, so a scripter (or an agent) can act without reading source.

Example:
    >>> from paccaassure_taf.core.errors import ConfigError
    >>> err = ConfigError("logging.level is invalid", cause="'LOUD' is not a level", fix="Use INFO or DEBUG.")
    >>> print(err)
    logging.level is invalid
      Likely cause: 'LOUD' is not a level
      How to fix: Use INFO or DEBUG.
"""

from enum import IntEnum
from typing import ClassVar

__all__ = [
    "ConfigError",
    "DataError",
    "ExitCode",
    "ExpectationError",
    "IntegrationError",
    "LicenseError",
    "LocatorError",
    "PatafError",
    "PluginError",
    "SecretError",
    "WaitTimeoutError",
]


class ExitCode(IntEnum):
    """Process exit codes; the quality gate decides them (REPORTING §6).

    Example:
        >>> int(ExitCode.GATE_BREACHED)
        1
    """

    GATE_PASSED = 0
    GATE_BREACHED = 1
    CONFIG_OR_FRAMEWORK_ERROR = 2
    SINK_ERROR = 3


class PatafError(Exception):
    """Base class for every PaccaAssureTAF error.

    Args:
        what: What failed, in one sentence.
        cause: The most likely cause, if known.
        fix: How to fix it, if known.

    Example:
        >>> err = PatafError("Report could not be written", fix="Check the results folder is writable.")
        >>> err.exit_code
        <ExitCode.CONFIG_OR_FRAMEWORK_ERROR: 2>
    """

    exit_code: ClassVar[ExitCode] = ExitCode.CONFIG_OR_FRAMEWORK_ERROR

    def __init__(self, what: str, *, cause: str | None = None, fix: str | None = None) -> None:
        self.what = what
        self.cause = cause
        self.fix = fix
        super().__init__(self.render())

    def render(self) -> str:
        """Return the multi-line, human-readable message.

        Example:
            >>> print(PatafError("Boom", cause="gremlins").render())
            Boom
              Likely cause: gremlins
        """
        lines = [self.what]
        if self.cause:
            lines.append(f"  Likely cause: {self.cause}")
        if self.fix:
            lines.append(f"  How to fix: {self.fix}")
        return "\n".join(lines)


class ConfigError(PatafError):
    """Configuration is missing, malformed, or invalid.

    Example:
        >>> raise ConfigError("env 'qa' has no envs/qa.yaml")  # doctest: +SKIP
    """


class SecretError(PatafError):
    """A secret reference could not be parsed or resolved.

    Example:
        >>> raise SecretError("env://DB_PASSWORD is not set")  # doctest: +SKIP
    """


class PluginError(PatafError):
    """A plugin could not be found, loaded, or conflicts with another.

    Example:
        >>> raise PluginError("secret_provider 'kv' is registered twice")  # doctest: +SKIP
    """


class LicenseError(PatafError):
    """A license file is unreadable or malformed (expiry never raises; it degrades).

    Example:
        >>> raise LicenseError("license.json is not valid JSON")  # doctest: +SKIP
    """


class WaitTimeoutError(PatafError):
    """A ``wait.until`` condition was not met within its timeout.

    Example:
        >>> raise WaitTimeoutError("Timed out after 5.0s waiting for the job to finish")  # doctest: +SKIP
    """


class LocatorError(PatafError):
    """An element could not be located (a ``broken`` result, not ``failed``).

    Example:
        >>> raise LocatorError("MemberSearchPage.search_btn not found")  # doctest: +SKIP
    """


class ExpectationError(PatafError, AssertionError):
    """An ``expect`` assertion failed (a ``failed`` result).

    Subclasses AssertionError so Behave reports the step as failed, not errored.

    Example:
        >>> isinstance(ExpectationError("rows differ"), AssertionError)
        True
    """


class DataError(PatafError):
    """Test data is missing, malformed, or could not be reserved.

    Example:
        >>> raise DataError("profile 'active_adult' not found in data/profiles/qa.yaml")  # doctest: +SKIP
    """


class IntegrationError(PatafError):
    """An external integration (sink, TMS, history store) failed.

    Example:
        >>> raise IntegrationError("ADO rejected the test run")  # doctest: +SKIP
    """
