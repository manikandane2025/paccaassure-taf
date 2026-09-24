import sys
import types
from abc import ABC, abstractmethod
from collections.abc import Callable
from importlib.metadata import EntryPoint
from typing import override

import pytest

from paccaassure_taf.core.errors import PluginError
from paccaassure_taf.core.plugins import PLUGIN_GROUP, PluginKind, PluginRegistry


class Provider(ABC):
    @abstractmethod
    def fetch(self) -> str: ...


class EnvProvider(Provider):
    @override
    def fetch(self) -> str:
        return "env"


class OtherProvider(Provider):
    @override
    def fetch(self) -> str:
        return "other"


class NotAProvider:
    pass


FAKE_MODULE = "pataf_fake_plugins"


@pytest.fixture(autouse=True)
def fake_module(monkeypatch: pytest.MonkeyPatch) -> None:
    module = types.ModuleType(FAKE_MODULE)
    module.EnvProvider = EnvProvider  # type: ignore[attr-defined]  # dynamic test module
    module.OtherProvider = OtherProvider  # type: ignore[attr-defined]  # dynamic test module
    module.NotAProvider = NotAProvider  # type: ignore[attr-defined]  # dynamic test module
    monkeypatch.setitem(sys.modules, FAKE_MODULE, module)


def _eps(*pairs: tuple[str, str]) -> Callable[[], list[EntryPoint]]:
    return lambda: [EntryPoint(name=n, value=f"{FAKE_MODULE}:{v}", group=PLUGIN_GROUP) for n, v in pairs]


def _registry(*pairs: tuple[str, str]) -> PluginRegistry[Provider]:
    return PluginRegistry[Provider](PluginKind.SECRET_PROVIDER, Provider, entry_points=_eps(*pairs))


def test_discovers_only_its_kind_by_prefix() -> None:
    registry = _registry(("secret_provider.env", "EnvProvider"), ("auth_provider.basic", "OtherProvider"))
    assert registry.names() == ["env"]
    assert registry.get("ENV") is EnvProvider
    assert registry.origin("env") == f"entry point {FAKE_MODULE}:EnvProvider"


def test_missing_plugin_lists_available_and_how_to_fix() -> None:
    registry = _registry(("secret_provider.env", "EnvProvider"))
    with pytest.raises(PluginError) as info:
        registry.get("kv")
    assert info.value.cause == "available secret_provider plugins: env"
    assert info.value.fix is not None
    assert '"secret_provider.kv"' in info.value.fix


def test_duplicate_names_fail_instead_of_silently_winning() -> None:
    registry = _registry(("secret_provider.env", "EnvProvider"), ("secret_provider.env", "OtherProvider"))
    with pytest.raises(PluginError, match="Two secret_provider plugins are named 'env'"):
        registry.names()


def test_registering_the_same_class_twice_is_idempotent() -> None:
    registry = _registry(("secret_provider.env", "EnvProvider"))
    registry.register("env", EnvProvider)
    assert registry.get("env") is EnvProvider


def test_programmatic_registration_conflicts_with_entry_point() -> None:
    registry = _registry(("secret_provider.env", "EnvProvider"))
    with pytest.raises(PluginError, match="Two"):
        registry.register("env", OtherProvider)


def test_wrong_base_class_is_rejected() -> None:
    registry = _registry(("secret_provider.bad", "NotAProvider"))
    with pytest.raises(PluginError, match="is not a Provider"):
        registry.names()


def test_import_failure_is_actionable() -> None:
    registry = PluginRegistry[Provider](
        PluginKind.SECRET_PROVIDER,
        Provider,
        entry_points=lambda: [
            EntryPoint(name="secret_provider.kv", value="no_such_module:X", group=PLUGIN_GROUP)
        ],
    )
    with pytest.raises(PluginError) as info:
        registry.names()
    assert "ModuleNotFoundError" in str(info.value.cause)
    assert info.value.fix is not None
    assert "extra" in info.value.fix


def test_entry_points_are_loaded_once() -> None:
    calls = {"n": 0}

    def source() -> list[EntryPoint]:
        calls["n"] += 1
        return _eps(("secret_provider.env", "EnvProvider"))()

    registry = PluginRegistry[Provider](PluginKind.SECRET_PROVIDER, Provider, entry_points=source)
    registry.names()
    registry.get("env")
    assert calls["n"] == 1


def test_default_source_reads_installed_entry_points() -> None:
    registry = PluginRegistry[Provider](PluginKind.CONNECTION_PROVIDER, Provider)
    assert isinstance(registry.names(), list)
