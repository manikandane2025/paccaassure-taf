"""The local behave stubs (stubs/behave) must match the installed behave at runtime.

mypy checks this file against the stubs; pytest checks the same names exist at runtime.
"""

import behave
from behave.model import Row, Table
from behave.model_core import Status
from behave.runner import Context


def test_step_decorators_exist() -> None:
    for decorator in (behave.given, behave.when, behave.then, behave.step):
        assert callable(decorator)


def test_status_members_match_runtime() -> None:
    assert {s.name for s in Status} >= {"passed", "failed", "skipped", "error", "hook_error", "undefined"}


def test_table_and_row_typed_access() -> None:
    table = Table(["Member ID", "Status"], rows=[Row(["Member ID", "Status"], ["NWH-M000001", "Active"])])
    first: Row = table[0]
    assert first["Status"] == "Active"
    assert first.as_dict() == {"Member ID": "NWH-M000001", "Status": "Active"}
    assert [row.cells for row in table] == [["NWH-M000001", "Active"]]


def test_context_type_is_importable() -> None:
    assert hasattr(Context, "add_cleanup")
