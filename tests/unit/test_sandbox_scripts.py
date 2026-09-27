"""Unit tests for the sandbox helpers in scripts/ (sandbox_smoke.py, dev.py sandbox tasks)."""

import doctest
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
SANDBOX = SCRIPTS.parent / "sandbox"


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


smoke = _load("sandbox_smoke")
dev = _load("dev")


def test_docstring_examples_run() -> None:
    assert doctest.testmod(smoke).failed == 0


def test_parse_env_file_handles_comments_quotes_and_export() -> None:
    text = '# comment\n\nA=1\nexport B="two words"\nC=\nnot a pair\n'
    assert smoke.parse_env_file(text) == {"A": "1", "B": "two words", "C": ""}


def test_ports_precedence_environment_then_env_file_then_defaults(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("NWH_SANDBOX_API_PORT=28083\nNWH_SANDBOX_DB_PORT=25433\n", encoding="utf-8")
    template = tmp_path / "env.example"
    template.write_text("NWH_SANDBOX_WEB_PORT=39999\n", encoding="utf-8")
    ports = smoke.resolve_ports({"NWH_SANDBOX_DB_PORT": "35433"}, env_file, template)
    # .env exists, so the template is not read (compose falls back to its own defaults instead).
    assert ports == {
        "NWH_SANDBOX_WEB_PORT": 18081,
        "NWH_SANDBOX_API_PORT": 28083,
        "NWH_SANDBOX_DB_PORT": 35433,
    }


def test_template_used_when_env_file_missing(tmp_path: Path) -> None:
    template = tmp_path / "env.example"
    template.write_text("NWH_SANDBOX_WEB_PORT=39999\n", encoding="utf-8")
    assert smoke.resolve_ports({}, tmp_path / ".env", template)["NWH_SANDBOX_WEB_PORT"] == 39999


def test_committed_template_matches_compose_defaults() -> None:
    template = smoke.parse_env_file((SANDBOX / "env.example").read_text(encoding="utf-8"))
    compose = (SANDBOX / "compose.yaml").read_text(encoding="utf-8")
    for key, value in template.items():
        if key in compose:
            assert f"${{{key}:-{value}}}" in compose, key
    for key, default in smoke.PORT_DEFAULTS.items():
        assert template[key] == str(default)


def test_run_reports_failures_in_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    def broken() -> str:
        raise RuntimeError("down")

    assert smoke.run([smoke.Probe("ok", lambda: "fine")]) == 0
    assert smoke.run([smoke.Probe("ok", lambda: "fine"), smoke.Probe("bad", broken)]) == 1
    out = capsys.readouterr().out
    assert "FAIL  bad" in out
    assert "1/2 sandbox probes passed." in out


@pytest.mark.parametrize("as_array", [False, True])
def test_container_health_parses_compose_ps(monkeypatch: pytest.MonkeyPatch, as_array: bool) -> None:
    rows = [{"Service": service, "Health": "healthy", "State": "running"} for service in smoke.SERVICES]
    stdout = json.dumps(rows) if as_array else "\n".join(json.dumps(row) for row in rows)

    def fake_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(smoke.subprocess, "run", fake_run)
    assert smoke.container_health() == "postgres=healthy api=healthy web=healthy"


def test_container_health_fails_when_a_service_is_unhealthy(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = json.dumps({"Service": "postgres", "Health": "starting", "State": "running"})

    def fake_run(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(smoke.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="postgres=starting api=missing web=missing"):
        smoke.container_health()


def test_ensure_sandbox_env_copies_once_and_never_overwrites(tmp_path: Path) -> None:
    (tmp_path / "env.example").write_text("NWH_SANDBOX_WEB_PORT=18081\n", encoding="utf-8")
    assert dev.ensure_sandbox_env(tmp_path) is True
    (tmp_path / ".env").write_text("NWH_SANDBOX_WEB_PORT=28081\n", encoding="utf-8")
    assert dev.ensure_sandbox_env(tmp_path) is False
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "NWH_SANDBOX_WEB_PORT=28081\n"


def test_sandbox_tasks_are_registered() -> None:
    for name in ("sandbox-up", "sandbox-smoke", "sandbox-down", "sandbox-typecheck", "sandbox-licenses"):
        assert name in dev.TASKS
    assert dev.sandbox_compose("ps")[-1] == "ps"
    assert dev.TASKS["sandbox-down"].commands()[0][-3:] == ["down", "-v", "--remove-orphans"]
