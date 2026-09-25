import json
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from paccaassure_taf import __version__
from paccaassure_taf.runner.cli import app

runner = CliRunner()


@pytest.fixture
def suite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "envs").mkdir()
    (tmp_path / "pataf.variant.yaml").write_text(
        "project: northwind\nusers:\n  eligibility_worker:\n    username: ew01\n    password: env://EW_PASSWORD\n",
        encoding="utf-8",
    )
    (tmp_path / "envs" / "qa.yaml").write_text("logging:\n  level: DEBUG\n", encoding="utf-8")
    for name in ("PATAF_ENV", "PATAF_PROJECT"):
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"paccaassure-taf-core {__version__}"


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "config" in result.output


def test_config_show_json(suite: Path) -> None:
    result = runner.invoke(app, ["config", "show", "--root", str(suite), "--env", "qa"])
    assert result.exit_code == 0, result.output
    shown = json.loads(result.output)
    assert shown["project"] == "northwind"
    assert shown["logging"]["level"] == "DEBUG"
    assert shown["users"]["eligibility_worker"]["password"] == "env://EW_PASSWORD"


def test_config_show_resolved_lists_sources(suite: Path) -> None:
    result = runner.invoke(
        app,
        ["config", "show", "--root", str(suite), "--env", "qa", "--resolved", "--set", "wait.timeout_s=5"],
    )
    assert result.exit_code == 0, result.output
    lines = {line.split()[0]: line for line in result.output.splitlines()}
    assert lines["project"].endswith("[pataf.variant.yaml]")
    assert lines["logging.level"].endswith("[envs/qa.yaml]")
    assert lines["wait.timeout_s"].endswith("[cli]")
    assert lines["wait.interval_s"].endswith("[default]")


def test_config_error_exits_2_with_actionable_message(suite: Path) -> None:
    result = runner.invoke(app, ["config", "show", "--root", str(suite), "--set", "logging.level=LOUD"])
    assert result.exit_code == 2
    assert "Invalid configuration" in result.output
    assert "(set by cli)" in result.output
    assert "How to fix" in result.output


def test_missing_env_file_exits_2(suite: Path) -> None:
    result = runner.invoke(app, ["config", "show", "--root", str(suite), "--env", "uat"])
    assert result.exit_code == 2
    assert "Environment 'uat' has no config file" in result.output


def test_bad_set_syntax_is_a_usage_error(suite: Path) -> None:
    result = runner.invoke(app, ["config", "show", "--root", str(suite), "--set", "no-equals-sign"])
    assert result.exit_code == 2
    assert "expected KEY=VALUE" in result.output


def test_python_dash_m_entry_point_works() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "paccaassure_taf", "--version"], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == f"paccaassure-taf-core {__version__}"


def test_config_show_applies_masking_config_at_startup(suite: Path) -> None:
    from paccaassure_taf.core.masking import default_masker  # noqa: PLC0415

    try:
        result = runner.invoke(
            app, ["config", "show", "--root", str(suite), "--set", 'masking.extra_patterns=["northwind"]']
        )
        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["project"] == "***"  # the configured pattern masked the output
    finally:
        default_masker.cache_clear()  # the CLI configures the process-wide masker
