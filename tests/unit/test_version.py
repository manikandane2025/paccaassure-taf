from importlib.metadata import version

import paccaassure_taf


def test_version_matches_installed_distribution() -> None:
    assert paccaassure_taf.__version__ == version("paccaassure-taf-core")
