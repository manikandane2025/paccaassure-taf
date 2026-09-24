"""PaccaAssureTAF core: typed, AI-native enterprise test automation.

The import root for every PaccaAssureTAF capability. Authors import from the
subpackages (for example ``paccaassure_taf.web`` or ``paccaassure_taf.bdd``);
this module only exposes the installed version.

Example:
    >>> import paccaassure_taf
    >>> isinstance(paccaassure_taf.__version__, str)
    True
"""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__: str = version("paccaassure-taf-core")
except PackageNotFoundError:  # pragma: no cover - only when running from an unbuilt source tree
    __version__ = "0.0.0+unknown"
