from collections.abc import Iterator

from _typeshed import Incomplete
from behave.model_core import Status

class Row:
    headings: list[str]
    cells: list[str]
    line: int | None
    def __init__(
        self,
        headings: list[str],
        cells: list[str],
        line: int | None = None,
        comments: list[str] | None = None,
    ) -> None: ...
    def __getitem__(self, name: str | int) -> str: ...
    def __len__(self) -> int: ...
    def __iter__(self) -> Iterator[str]: ...
    def get(self, key: str, default: str | None = None) -> str | None: ...
    def as_dict(self) -> dict[str, str]: ...

class Table:
    headings: list[str]
    rows: list[Row]
    line: int | None
    def __init__(
        self, headings: list[str], rows: list[Row] | None = None, line: int | None = None
    ) -> None: ...
    def __iter__(self) -> Iterator[Row]: ...
    def __getitem__(self, index: int) -> Row: ...
    def __len__(self) -> int: ...

class Step:
    keyword: str
    step_type: str
    name: str
    text: str | None
    table: Table | None
    status: Status
    duration: float
    error_message: str | None
    filename: str
    line: int
    def __getattr__(self, name: str) -> Incomplete: ...

class Scenario:
    keyword: str
    name: str
    tags: list[str]
    effective_tags: set[str]
    steps: list[Step]
    status: Status
    duration: float
    filename: str
    line: int
    def __getattr__(self, name: str) -> Incomplete: ...

class ScenarioOutline(Scenario): ...

class Feature:
    keyword: str
    name: str
    tags: list[str]
    scenarios: list[Scenario]
    status: Status
    duration: float
    filename: str
    line: int
    def __getattr__(self, name: str) -> Incomplete: ...

def __getattr__(name: str) -> Incomplete: ...
