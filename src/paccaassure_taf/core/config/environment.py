"""The single place PaccaAssureTAF reads the process environment (CODING_STANDARDS).

Everything else receives an ``environ`` mapping, which keeps behaviour explicit and testable.

Example:
    >>> is_ci({"GITHUB_ACTIONS": "true"}), is_ci({"CI": "false"}), is_ci({})
    (True, False, False)
"""

import os
from collections.abc import Mapping
from typing import Final

__all__ = ["CI_VARIABLES", "is_ci", "process_environment"]

# Set by common CI systems; any one with a truthy value means "running in CI".
CI_VARIABLES: Final = (
    "CI",
    "TF_BUILD",
    "GITHUB_ACTIONS",
    "JENKINS_URL",
    "GITLAB_CI",
    "BUILDKITE",
    "TEAMCITY_VERSION",
)
_FALSY: Final = frozenset({"", "0", "false", "no", "off"})


def process_environment() -> Mapping[str, str]:
    """Return a snapshot of the process environment.

    Example:
        >>> "PATH" in process_environment() or "Path" in process_environment()
        True
    """
    return dict(os.environ)


def is_ci(environ: Mapping[str, str]) -> bool:
    """Return True when running under a CI system.

    Example:
        >>> is_ci({"TF_BUILD": "True"})
        True
    """
    return any(environ.get(name, "").strip().lower() not in _FALSY for name in CI_VARIABLES)
