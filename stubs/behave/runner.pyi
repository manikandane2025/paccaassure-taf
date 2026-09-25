from collections.abc import Callable
from typing import Any

from _typeshed import Incomplete
from behave.model import Feature, Scenario, Table

class Context:
    # behave's Context is a dynamic attribute bag by design; paccaassure_taf.bdd wraps it in a typed World.
    feature: Feature
    scenario: Scenario
    table: Table | None
    text: str | None
    config: Incomplete
    def add_cleanup(self, cleanup_func: Callable[..., object], *args: Any, **kwargs: Any) -> None: ...
    def execute_steps(self, steps_text: str) -> bool: ...
    def __getattr__(self, name: str) -> Incomplete: ...

def __getattr__(name: str) -> Incomplete: ...
