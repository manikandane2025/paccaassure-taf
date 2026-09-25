import pytest

from paccaassure_taf.core.errors import (
    ConfigError,
    ExitCode,
    ExpectationError,
    PatafError,
    SecretError,
    WaitTimeoutError,
)


def test_message_has_what_cause_and_fix() -> None:
    err = ConfigError("bad level", cause="typo", fix="use INFO")
    assert str(err) == "bad level\n  Likely cause: typo\n  How to fix: use INFO"
    assert (err.what, err.cause, err.fix) == ("bad level", "typo", "use INFO")


def test_message_omits_missing_parts() -> None:
    assert str(PatafError("only what")) == "only what"


@pytest.mark.parametrize("error_type", [ConfigError, SecretError, WaitTimeoutError])
def test_framework_errors_map_to_exit_code_2(error_type: type[PatafError]) -> None:
    assert error_type("x").exit_code is ExitCode.CONFIG_OR_FRAMEWORK_ERROR
    assert issubclass(error_type, PatafError)


def test_expectation_error_is_an_assertion_error() -> None:
    with pytest.raises(AssertionError):
        raise ExpectationError("rows differ")


def test_exit_codes_match_reporting_spec() -> None:
    assert [int(c) for c in ExitCode] == [0, 1, 2, 3]
