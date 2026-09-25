r"""Apply a resolved configuration to the process: masking, then logging.

Every CLI entry point calls :func:`apply_config` right after ``load_config`` so the
``masking:`` and ``logging:`` sections actually take effect before anything is logged.

Example:
    >>> import io
    >>> from pathlib import Path
    >>> from paccaassure_taf.core.config import load_config
    >>> overrides = {"masking.extra_patterns": '["NWH-M\\\\d{6}"]'}
    >>> resolved = load_config(Path("."), overrides=overrides, environ={})
    >>> stream = io.StringIO()
    >>> masker = apply_config(resolved, masker=Masker(), log_stream=stream)
    >>> masker.scrub("member NWH-M000123 not found")
    'member *** not found'
"""

from typing import TextIO

from paccaassure_taf.core.config import ResolvedConfig
from paccaassure_taf.core.log import configure_logging
from paccaassure_taf.core.masking import Masker, default_masker

__all__ = ["apply_config"]


def apply_config(
    resolved: ResolvedConfig, *, masker: Masker | None = None, log_stream: TextIO | None = None
) -> Masker:
    """Configure the masker from ``masking:`` and logging from ``logging:``; return the masker.

    Args:
        resolved: Output of ``core.config.load_config``.
        masker: Masker to configure (default: the process-wide :func:`default_masker`).
        log_stream: Where logs go (default ``sys.stderr``).

    Example:
        >>> from pathlib import Path
        >>> from paccaassure_taf.core.config import load_config
        >>> _ = apply_config(load_config(Path("."), environ={}), masker=Masker())
    """
    config = resolved.config
    target = masker or default_masker()
    target.configure(extra_patterns=config.masking.extra_patterns, mask=config.masking.mask)
    configure_logging(level=config.logging.level, fmt=config.logging.format, stream=log_stream, masker=target)
    return target
