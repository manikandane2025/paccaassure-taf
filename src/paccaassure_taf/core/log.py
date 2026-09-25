"""Structured logging with masking and correlation ids (structlog).

Every event passes through the :class:`~paccaassure_taf.core.masking.Masker`
*before* rendering, so secrets and ``Sensitive`` values never reach a log stream.
Correlation ids (run, test, step) are bound per context and added to every event.

Example:
    >>> import io, json
    >>> buffer = io.StringIO()
    >>> configure_logging(fmt=LogFormat.JSON, stream=buffer)
    >>> with correlation(run_id="20260924T101500Z-ab12cd"):
    ...     get_logger("demo").info("login", user="eligibility_worker", password="pw-Northwind-1")
    >>> event = json.loads(buffer.getvalue())
    >>> event["password"], event["run_id"], event["event"]
    ('***', '20260924T101500Z-ab12cd', 'login')
"""

import logging
import sys
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from enum import StrEnum
from typing import TextIO

import structlog
from structlog.typing import EventDict, FilteringBoundLogger, WrappedLogger

from paccaassure_taf.core.masking import Masker, default_masker

__all__ = [
    "LogFormat",
    "LogLevel",
    "MaskingProcessor",
    "bind_correlation",
    "clear_correlation",
    "configure_logging",
    "correlation",
    "get_logger",
]


class LogLevel(StrEnum):
    """Log levels accepted in config (``logging.level``).

    Example:
        >>> LogLevel("DEBUG").as_int()
        10
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

    def as_int(self) -> int:
        """Return the stdlib numeric level.

        Example:
            >>> LogLevel.ERROR.as_int()
            40
        """
        return logging.getLevelNamesMapping()[self.value]


class LogFormat(StrEnum):
    """Rendering: ``json`` for CI and machines, ``console`` for humans.

    Example:
        >>> LogFormat.JSON.value
        'json'
    """

    JSON = "json"
    CONSOLE = "console"


class MaskingProcessor:
    """structlog processor that masks the whole event dict.

    Example:
        >>> MaskingProcessor(Masker())(None, "info", {"event": "x", "token": "abc12345"})
        {'event': 'x', 'token': '***'}
    """

    def __init__(self, masker: Masker) -> None:
        self._masker = masker

    def __call__(
        self,
        logger: WrappedLogger,  # noqa: ARG002 - signature required by structlog
        method_name: str,  # noqa: ARG002 - signature required by structlog
        event_dict: EventDict,
    ) -> EventDict:
        """Return a masked copy of ``event_dict``."""
        masked = self._masker.mask(event_dict)
        result: MutableMapping[str, object] = dict(masked) if isinstance(masked, dict) else {"event": masked}
        return result


def configure_logging(
    *,
    level: LogLevel = LogLevel.INFO,
    fmt: LogFormat = LogFormat.CONSOLE,
    stream: TextIO | None = None,
    masker: Masker | None = None,
) -> None:
    """Configure process-wide structured logging. Call once at a CLI entry point.

    Args:
        level: Minimum level emitted.
        fmt: JSON lines or human-readable console output.
        stream: Where to write (default ``sys.stderr``).
        masker: Masker to apply (default: the shared :func:`default_masker`).

    Example:
        >>> configure_logging(level=LogLevel.DEBUG, fmt=LogFormat.CONSOLE)
    """
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer(sort_keys=True)
        if fmt is LogFormat.JSON
        else structlog.dev.ConsoleRenderer(colors=False)
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.format_exc_info,  # render tracebacks to text *before* masking them
            MaskingProcessor(masker or default_masker()),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level.as_int()),
        logger_factory=structlog.PrintLoggerFactory(file=stream if stream is not None else sys.stderr),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Return a logger that tags every event with ``logger=<name>``.

    Example:
        >>> log = get_logger("paccaassure_taf.core.config")
    """
    logger: FilteringBoundLogger = structlog.get_logger()
    return logger.bind(logger=name)


def bind_correlation(
    *, run_id: str | None = None, test_key: str | None = None, step: str | None = None
) -> None:
    """Bind correlation ids to the current context (thread / task). ``None`` values are skipped.

    Example:
        >>> bind_correlation(run_id="20260924T101500Z-ab12cd")
        >>> clear_correlation()
    """
    values = {
        k: v for k, v in {"run_id": run_id, "test_key": test_key, "step": step}.items() if v is not None
    }
    structlog.contextvars.bind_contextvars(**values)


def clear_correlation() -> None:
    """Remove all correlation ids from the current context.

    Example:
        >>> clear_correlation()
    """
    structlog.contextvars.clear_contextvars()


@contextmanager
def correlation(
    *, run_id: str | None = None, test_key: str | None = None, step: str | None = None
) -> Iterator[None]:
    """Bind correlation ids for the duration of a ``with`` block, then restore the previous ones.

    Example:
        >>> with correlation(test_key="a1b2c3", step="Given an active adult member exists"):
        ...     pass
    """
    values = {
        k: v for k, v in {"run_id": run_id, "test_key": test_key, "step": step}.items() if v is not None
    }
    with structlog.contextvars.bound_contextvars(**values):
        yield
