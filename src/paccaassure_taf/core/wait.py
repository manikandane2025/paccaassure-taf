"""Polling waits: the only sanctioned way to wait for a condition (hard rule 5).

``time.sleep`` is banned in PaccaAssureTAF. UI waits use Playwright auto-wait;
everything else (a job finishing, a row appearing in a DB, a file landing) uses
:func:`until`, which polls, gives up after a timeout, and explains what it saw.

Example:
    >>> from paccaassure_taf.core import wait
    >>> readings = iter([None, None, "done"])
    >>> wait.until(lambda: next(readings), description="the export job", timeout=5, interval=0.01)
    'done'
"""

import threading
import time
from collections.abc import Callable

from paccaassure_taf.core.errors import WaitTimeoutError
from paccaassure_taf.core.masking import default_masker

__all__ = ["until"]


def _pause(seconds: float) -> None:
    # An Event that is never set: waits exactly `seconds` without using the banned time.sleep.
    threading.Event().wait(seconds)


def until[T](
    probe: Callable[[], T],
    *,
    description: str,
    timeout: float = 30.0,
    interval: float = 0.25,
    accept: Callable[[T], bool] = bool,
    ignoring: tuple[type[Exception], ...] = (),
    clock: Callable[[], float] = time.monotonic,
    pause: Callable[[float], object] = _pause,
) -> T:
    """Call ``probe`` until ``accept(result)`` is true; return that result.

    Args:
        probe: Reads the current state (no side effects, safe to call repeatedly).
        description: What is awaited, for the timeout message ("the claim to be ADJUDICATED").
        timeout: Seconds before giving up. The probe always runs at least once.
        interval: Seconds between probes.
        accept: Decides whether a result is final (default: truthiness).
        ignoring: Exception types treated as "not yet" (e.g. a transient connection error).
        clock: Monotonic clock (injectable for tests).
        pause: Waits between probes (injectable for tests).

    Returns:
        The first accepted probe result.

    Raises:
        WaitTimeoutError: With the last result or ignored exception (masked) and a fix hint.
        ValueError: If ``timeout`` is negative or ``interval`` is not positive.

    Example:
        >>> status = iter(["QUEUED", "RUNNING", "ADJUDICATED"])
        >>> until(lambda: next(status), accept=lambda s: s == "ADJUDICATED",
        ...       description="the claim to be adjudicated", timeout=5, interval=0.01)
        'ADJUDICATED'
    """
    if timeout < 0:
        raise ValueError(f"timeout must be >= 0, got {timeout}")
    if interval <= 0:
        raise ValueError(f"interval must be > 0, got {interval}")
    deadline = clock() + timeout
    attempts = 0
    last_result: object = None
    last_error: Exception | None = None
    while True:
        attempts += 1
        try:
            result = probe()
        except ignoring as error:
            last_error = error
        else:
            if accept(result):
                return result
            last_result, last_error = result, None
        remaining = deadline - clock()
        if remaining <= 0:
            break
        pause(min(interval, remaining))

    masker = default_masker()
    if last_error is not None:
        cause = f"last attempt raised {type(last_error).__name__}: {masker.scrub(str(last_error))}"
    else:
        cause = f"last value was {masker.scrub(repr(last_result))}"
    raise WaitTimeoutError(
        f"Timed out after {timeout:g}s waiting for {description} ({attempts} attempts)",
        cause=cause,
        fix=(
            "Check the condition and the system state first. Raise the timeout only if the system "
            "is legitimately slower (config wait.timeout_s or timeout=); never add sleeps."
        ),
    )
