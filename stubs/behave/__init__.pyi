# Partial stubs for behave 1.3.x (behave ships no type information).
# Only the surface paccaassure_taf.bdd / runner use is typed; everything else is Incomplete.
from collections.abc import Callable
from typing import Any, TypeVar

from _typeshed import Incomplete

_F = TypeVar("_F", bound=Callable[..., Any])

class _StepDecorator:
    def __call__(self, step_text: str, **kwargs: Any) -> Callable[[_F], _F]: ...

given: _StepDecorator
when: _StepDecorator
then: _StepDecorator
step: _StepDecorator
Given: _StepDecorator
When: _StepDecorator
Then: _StepDecorator
Step: _StepDecorator

def register_type(**kwargs: Callable[[str], object]) -> None: ...
def use_step_matcher(name: str) -> None: ...
def use_default_step_matcher(name: str | None = None) -> None: ...

__version__: str

def __getattr__(name: str) -> Incomplete: ...
