import io
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

from paccaassure_taf.core.config import load_config
from paccaassure_taf.core.log import get_logger
from paccaassure_taf.core.masking import Masker
from paccaassure_taf.core.runtime import apply_config

MEMBER_ID_PATTERN = r"NWH-M\d{6}"


@pytest.fixture(autouse=True)
def reset_logging() -> Iterator[None]:
    yield
    structlog.reset_defaults()


def _write_variant(root: Path, text: str) -> None:
    (root / "pataf.variant.yaml").write_text(text, encoding="utf-8")


def test_config_pattern_masks_member_id_in_a_log_line(tmp_path: Path) -> None:
    _write_variant(
        tmp_path,
        "logging:\n  format: json\nmasking:\n  extra_patterns:\n    - 'NWH-M\\d{6}'\n",
    )
    resolved = load_config(tmp_path, environ={})
    assert resolved.config.masking.extra_patterns == [MEMBER_ID_PATTERN]
    stream = io.StringIO()
    apply_config(resolved, masker=Masker(), log_stream=stream)

    get_logger("claims").info("member NWH-M000123 not eligible", member="NWH-M000456")

    raw = stream.getvalue()
    assert "NWH-M000123" not in raw
    assert "NWH-M000456" not in raw
    event = json.loads(raw)
    assert event["event"] == "member *** not eligible"
    assert event["member"] == "***"


def test_config_mask_text_and_logging_settings_are_applied(tmp_path: Path) -> None:
    _write_variant(tmp_path, "logging:\n  level: WARNING\n  format: json\nmasking:\n  mask: '[redacted]'\n")
    stream = io.StringIO()
    masker = apply_config(load_config(tmp_path, environ={}), masker=Masker(), log_stream=stream)
    log = get_logger("t")
    log.info("dropped by level")
    log.warning("login", password="pw-Northwind-1")
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [e["event"] for e in events] == ["login"]
    assert events[0]["password"] == "[redacted]"
    assert masker.mask_text == "[redacted]"


def test_apply_config_is_idempotent(tmp_path: Path) -> None:
    resolved = load_config(tmp_path, overrides={"masking.extra_patterns": '["NWH-M\\\\d{6}"]'}, environ={})
    masker = Masker()
    apply_config(resolved, masker=masker, log_stream=io.StringIO())
    apply_config(resolved, masker=masker, log_stream=io.StringIO())
    assert masker.scrub("NWH-M000123") == "***"


def test_max_learned_values_from_config_reaches_the_masker(tmp_path: Path) -> None:
    resolved = load_config(tmp_path, overrides={"masking.max_learned_values": "2"}, environ={})
    masker = apply_config(resolved, masker=Masker(), log_stream=io.StringIO())
    for index in range(5):
        masker.register(f"learned-{index:03d}", pinned=False)
    assert masker.learned_count == 2
