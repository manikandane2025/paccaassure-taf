import io
import json
from collections.abc import Iterator

import pytest
import structlog
from pydantic import SecretStr

from paccaassure_taf.core.log import (
    LogFormat,
    LogLevel,
    bind_correlation,
    clear_correlation,
    configure_logging,
    correlation,
    get_logger,
)
from paccaassure_taf.core.masking import Masker


@pytest.fixture
def buffer() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    configure_logging(level=LogLevel.DEBUG, fmt=LogFormat.JSON, stream=stream, masker=Masker())
    yield stream
    clear_correlation()
    structlog.reset_defaults()


def _events(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_json_event_has_level_timestamp_and_logger(buffer: io.StringIO) -> None:
    get_logger("paccaassure_taf.tests").info("hello", count=3)
    (event,) = _events(buffer)
    assert event["event"] == "hello"
    assert event["level"] == "info"
    assert event["logger"] == "paccaassure_taf.tests"
    assert event["count"] == 3
    assert str(event["timestamp"]).endswith("Z")


def test_secrets_are_masked_before_rendering(buffer: io.StringIO) -> None:
    get_logger("t").info(
        "login", user="eligibility_worker", password="pw-Northwind-1", token=SecretStr("tok-123456")
    )
    raw = buffer.getvalue()
    assert "pw-Northwind-1" not in raw
    assert "tok-123456" not in raw
    (event,) = _events(buffer)
    assert event["password"] == "***"
    assert event["token"] == "***"
    assert event["user"] == "eligibility_worker"


def test_learned_secret_is_scrubbed_from_messages_and_tracebacks() -> None:
    stream = io.StringIO()
    masker = Masker()
    masker.register("hunter22-value")
    configure_logging(fmt=LogFormat.JSON, stream=stream, masker=masker)
    log = get_logger("t")
    log.info("connecting with hunter22-value")
    try:
        raise ValueError("bad credential hunter22-value")
    except ValueError:
        log.exception("failed")
    structlog.reset_defaults()
    assert "hunter22-value" not in stream.getvalue()
    assert "ValueError" in stream.getvalue()


def test_correlation_ids_are_bound_and_restored(buffer: io.StringIO) -> None:
    log = get_logger("t")
    bind_correlation(run_id="run-1")
    with correlation(test_key="tk-1", step="Given x"):
        log.info("inside")
    log.info("outside")
    inside, outside = _events(buffer)
    assert (inside["run_id"], inside["test_key"], inside["step"]) == ("run-1", "tk-1", "Given x")
    assert outside["run_id"] == "run-1"
    assert "test_key" not in outside


def test_level_filtering() -> None:
    stream = io.StringIO()
    configure_logging(level=LogLevel.WARNING, fmt=LogFormat.JSON, stream=stream)
    log = get_logger("t")
    log.info("dropped")
    log.warning("kept")
    structlog.reset_defaults()
    assert [e["event"] for e in _events(stream)] == ["kept"]


def test_console_format_is_human_readable() -> None:
    stream = io.StringIO()
    configure_logging(fmt=LogFormat.CONSOLE, stream=stream)
    get_logger("t").info("ready", password="pw-Northwind-1")
    structlog.reset_defaults()
    out = stream.getvalue()
    assert "ready" in out
    assert "pw-Northwind-1" not in out


def test_log_level_ints() -> None:
    assert [lvl.as_int() for lvl in LogLevel] == [10, 20, 30, 40]
