from pathlib import Path

import pytest

from paccaassure_taf.core.config import (
    ConfigEntry,
    PatafConfig,
    is_ci,
    load_config,
    process_environment,
)
from paccaassure_taf.core.errors import ConfigError
from paccaassure_taf.core.log import LogLevel
from paccaassure_taf.core.secrets import SecretScheme


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def suite(tmp_path: Path) -> Path:
    _write(
        tmp_path / "pataf.variant.yaml",
        "project: northwind\nvariant: state-ga\nlogging:\n  level: WARNING\n  format: json\n"
        "users:\n  eligibility_worker:\n    username: ew01\n    password: env://EW_PASSWORD\n",
    )
    _write(tmp_path / "envs" / "qa.yaml", "logging:\n  level: INFO\nwait:\n  timeout_s: 60\n")
    return tmp_path


def test_defaults_only(tmp_path: Path) -> None:
    resolved = load_config(tmp_path, environ={})
    assert resolved.config == PatafConfig()
    assert resolved.source_of("logging.level") == "default"
    assert resolved.ci is False


def test_layer_order_and_provenance(suite: Path, tmp_path: Path) -> None:
    app = _write(
        tmp_path / "pack" / "pataf.app.yaml", "app: claims\nwait:\n  interval_s: 0.5\n  timeout_s: 10\n"
    )
    resolved = load_config(
        suite,
        env="qa",
        app_files=[app],
        overrides={"wait.interval_s": "0.1"},
        environ={"PATAF_LOGGING__LEVEL": "DEBUG"},
    )
    config = resolved.config
    assert (config.app, config.project, config.variant, config.env) == (
        "claims",
        "northwind",
        "state-ga",
        "qa",
    )
    assert config.logging.level is LogLevel.DEBUG
    assert config.wait.timeout_s == 60
    assert config.wait.interval_s == 0.1
    assert resolved.source_of("app") == "pataf.app.yaml"
    assert resolved.source_of("project") == "pataf.variant.yaml"
    assert resolved.source_of("wait.timeout_s") == "envs/qa.yaml"
    assert resolved.source_of("logging.level") == "env PATAF_LOGGING__LEVEL"
    assert resolved.source_of("logging.format") == "pataf.variant.yaml"
    assert resolved.source_of("wait.interval_s") == "cli"
    assert resolved.source_of("env") == "cli"
    assert resolved.source_of("users.eligibility_worker.password") == "pataf.variant.yaml"


def test_env_name_from_pataf_env(suite: Path) -> None:
    resolved = load_config(suite, environ={"PATAF_ENV": "qa"})
    assert resolved.config.env == "qa"
    assert resolved.config.wait.timeout_s == 60
    assert resolved.source_of("env") == "env PATAF_ENV"


def test_missing_env_file_is_actionable(suite: Path) -> None:
    with pytest.raises(ConfigError) as info:
        load_config(suite, env="uat", environ={})
    assert info.value.what == "Environment 'uat' has no config file"
    assert info.value.fix is not None
    assert "envs/uat.yaml" in info.value.fix


def test_secret_refs_are_typed(suite: Path) -> None:
    password = load_config(suite, environ={}).config.users["eligibility_worker"].password
    assert (password.scheme, password.path) == (SecretScheme.ENV, "EW_PASSWORD")


def test_env_values_can_be_json_and_nested_dict_replacement_clears_provenance(tmp_path: Path) -> None:
    resolved = load_config(tmp_path, environ={"PATAF_MASKING__EXTRA_PATTERNS": '["NWH-M\\\\d{6}"]'})
    assert resolved.config.masking.extra_patterns == [r"NWH-M\d{6}"]
    not_json = load_config(tmp_path, environ={"PATAF_MASKING__MASK": "{redacted"})
    assert not_json.config.masking.mask == "{redacted"  # invalid JSON stays a plain string


def test_invalid_values_name_key_message_and_source(suite: Path) -> None:
    _write(suite / "envs" / "qa.yaml", "logging:\n  level: LOUD\nwait:\n  timeout_s: -1\n")
    with pytest.raises(ConfigError) as info:
        load_config(suite, env="qa", environ={})
    err = info.value
    assert err.what == "Invalid configuration (2 problems)"
    assert err.cause is not None
    assert "logging.level:" in err.cause
    assert "(set by envs/qa.yaml)" in err.cause
    assert "wait.timeout_s:" in err.cause


def test_typo_in_section_name_is_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "pataf.variant.yaml", "loging:\n  level: DEBUG\n")
    with pytest.raises(ConfigError) as info:
        load_config(tmp_path, environ={})
    assert info.value.cause is not None
    assert "loging: Extra inputs are not permitted (set by pataf.variant.yaml)" in info.value.cause


def test_unknown_pataf_env_var_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Invalid configuration") as info:
        load_config(tmp_path, environ={"PATAF_NOPE": "1"})
    assert "(set by env PATAF_NOPE)" in str(info.value.cause)


def test_plaintext_password_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path / "pataf.variant.yaml",
        "users:\n  admin:\n    username: a\n    password: pw-Northwind-plain\n",
    )
    with pytest.raises(ConfigError) as info:
        load_config(tmp_path, environ={})
    assert "users.admin.password" in str(info.value.cause)
    assert "pw-Northwind-plain" not in str(info.value)
    assert "value hidden" in str(info.value.cause)


@pytest.mark.parametrize(
    ("text", "fragment"),
    [
        ("logging:\n  level: [unclosed\n", "line 3"),
        ("- just\n- a list\n", "top level is list"),
    ],
)
def test_bad_yaml_is_actionable(tmp_path: Path, text: str, fragment: str) -> None:
    _write(tmp_path / "pataf.variant.yaml", text)
    with pytest.raises(ConfigError) as info:
        load_config(tmp_path, environ={})
    assert fragment in str(info.value.cause)


def test_unreadable_app_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="could not be read"):
        load_config(tmp_path, app_files=[tmp_path / "missing" / "pataf.app.yaml"], environ={})


def test_empty_yaml_is_fine(tmp_path: Path) -> None:
    _write(tmp_path / "pataf.variant.yaml", "# nothing yet\n")
    assert load_config(tmp_path, environ={}).config == PatafConfig()


def test_invalid_extra_pattern_regex(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Invalid configuration") as info:
        load_config(tmp_path, overrides={"masking.extra_patterns": '["("]'}, environ={})
    assert "invalid regular expression" in str(info.value.cause)


def test_entries_are_masked_and_sourced(suite: Path) -> None:
    resolved = load_config(suite, environ={"PATAF_PROJECT": "northwind"})
    by_key = {e.key: e for e in resolved.entries()}
    assert by_key["project"] == ConfigEntry("project", "northwind", "env PATAF_PROJECT")
    assert (
        by_key["users.eligibility_worker.password"].value == "env://EW_PASSWORD"
    )  # a reference, not a secret
    assert by_key["wait.timeout_s"].source == "default"
    rendered = resolved.render()
    assert "project" in rendered
    assert "[env PATAF_PROJECT]" in rendered


def test_allow_file_refs_follows_ci_unless_configured(tmp_path: Path) -> None:
    assert load_config(tmp_path, environ={}).allow_file_refs is True
    assert load_config(tmp_path, environ={"GITHUB_ACTIONS": "true"}).allow_file_refs is False
    forced = load_config(tmp_path, overrides={"secrets.allow_file_refs": "true"}, environ={"CI": "1"})
    assert forced.allow_file_refs is True


@pytest.mark.parametrize(
    ("environ", "expected"),
    [
        ({"CI": "true"}, True),
        ({"TF_BUILD": "True"}, True),
        ({"CI": "0"}, False),
        ({"CI": ""}, False),
        ({}, False),
    ],
)
def test_is_ci(environ: dict[str, str], expected: bool) -> None:
    assert is_ci(environ) is expected


def test_process_environment_is_a_snapshot() -> None:
    snapshot = process_environment()
    assert isinstance(snapshot, dict)


def test_new_section_from_a_later_layer_does_not_claim_its_siblings(tmp_path: Path) -> None:
    resolved = load_config(tmp_path, overrides={"wait.timeout_s": "5"}, environ={})
    assert resolved.source_of("wait.timeout_s") == "cli"
    assert resolved.source_of("wait.interval_s") == "default"


def test_json_object_env_var_merges_into_section(tmp_path: Path) -> None:
    _write(tmp_path / "pataf.variant.yaml", "masking:\n  mask: '[x]'\n")
    resolved = load_config(tmp_path, environ={"PATAF_MASKING": '{"extra_patterns": ["a+"]}'})
    assert resolved.config.masking.extra_patterns == ["a+"]
    assert resolved.source_of("masking.extra_patterns") == "env PATAF_MASKING"
    assert resolved.source_of("masking.mask") == "pataf.variant.yaml"


def test_section_source_is_the_layers_that_set_its_values(suite: Path) -> None:
    resolved = load_config(suite, env="qa", environ={})
    assert resolved.source_of("logging") == "envs/qa.yaml + pataf.variant.yaml"
    assert resolved.source_of("secrets") == "default"
