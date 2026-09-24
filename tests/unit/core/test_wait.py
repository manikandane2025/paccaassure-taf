from collections.abc import Callable

import pytest

from paccaassure_taf.core import wait
from paccaassure_taf.core.errors import WaitTimeoutError
from paccaassure_taf.core.masking import default_masker


class FakeClock:
    """Deterministic time: pausing advances the clock instead of waiting."""

    def __init__(self) -> None:
        self.now = 0.0
        self.pauses: list[float] = []

    def __call__(self) -> float:
        return self.now

    def pause(self, seconds: float) -> None:
        self.pauses.append(seconds)
        self.now += seconds


def _sequence[T](*values: T) -> Callable[[], T]:
    items = iter(values)
    return lambda: next(items)


def test_returns_first_accepted_result() -> None:
    clock = FakeClock()
    result = wait.until(
        _sequence(0, 0, 3), description="count", timeout=10, interval=1, clock=clock, pause=clock.pause
    )
    assert result == 3
    assert clock.pauses == [1, 1]


def test_custom_accept() -> None:
    clock = FakeClock()
    result = wait.until(
        _sequence("QUEUED", "DONE"),
        accept=lambda s: s == "DONE",
        description="job",
        clock=clock,
        pause=clock.pause,
    )
    assert result == "DONE"


def test_timeout_reports_last_value_attempts_and_fix() -> None:
    clock = FakeClock()
    with pytest.raises(WaitTimeoutError) as info:
        wait.until(lambda: "RUNNING", accept=lambda s: s == "DONE", description="the job", timeout=2,
                   interval=1, clock=clock, pause=clock.pause)  # fmt: skip
    err = info.value
    assert err.what == "Timed out after 2s waiting for the job (3 attempts)"
    assert err.cause == "last value was 'RUNNING'"
    assert err.fix is not None
    assert "never add sleeps" in err.fix


def test_ignored_exceptions_are_retried_and_reported() -> None:
    clock = FakeClock()
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("refused")
        return "ok"

    assert (
        wait.until(flaky, description="db", ignoring=(ConnectionError,), clock=clock, pause=clock.pause)
        == "ok"
    )

    def always_down() -> str:
        raise ConnectionError("refused")

    with pytest.raises(WaitTimeoutError) as info:
        wait.until(always_down, description="db", ignoring=(ConnectionError,), timeout=1, interval=0.5,
                   clock=clock, pause=clock.pause)  # fmt: skip
    assert info.value.cause == "last attempt raised ConnectionError: refused"


def test_unexpected_exceptions_propagate_immediately() -> None:
    def broken() -> str:
        raise KeyError("x")

    with pytest.raises(KeyError):
        wait.until(broken, description="x", timeout=5)


def test_probe_runs_once_even_with_zero_timeout() -> None:
    clock = FakeClock()
    assert wait.until(lambda: 1, description="x", timeout=0, clock=clock, pause=clock.pause) == 1
    with pytest.raises(WaitTimeoutError, match=r"\(1 attempts\)"):
        wait.until(lambda: 0, description="x", timeout=0, clock=clock, pause=clock.pause)


def test_last_pause_is_trimmed_to_the_deadline() -> None:
    clock = FakeClock()
    with pytest.raises(WaitTimeoutError):
        wait.until(lambda: False, description="x", timeout=2.5, interval=1, clock=clock, pause=clock.pause)
    assert clock.pauses == [1, 1, 0.5]


def test_timeout_message_masks_sensitive_values() -> None:
    default_masker().register("pw-Northwind-9")
    clock = FakeClock()
    with pytest.raises(WaitTimeoutError) as info:
        wait.until(lambda: "pw-Northwind-9", accept=lambda _: False, description="x", timeout=0,
                   clock=clock, pause=clock.pause)  # fmt: skip
    assert "pw-Northwind-9" not in str(info.value)


@pytest.mark.parametrize(("timeout", "interval"), [(-1, 1), (1, 0), (1, -0.5)])
def test_invalid_arguments(timeout: float, interval: float) -> None:
    with pytest.raises(ValueError, match="must be"):
        wait.until(lambda: 1, description="x", timeout=timeout, interval=interval)


def test_default_pause_really_waits() -> None:
    readings = iter([None, "ok"])
    assert wait.until(lambda: next(readings), description="x", timeout=1, interval=0.01) == "ok"
