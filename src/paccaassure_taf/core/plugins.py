"""Plugin registry over Python entry points (ARCHITECTURE §5).

App packs, variant suites and optional extras extend PaccaAssureTAF by declaring
entry points in the ``paccaassure_taf.plugins`` group, named ``<kind>.<name>``::

    [project.entry-points."paccaassure_taf.plugins"]
    "secret_provider.kv" = "paccaassure_taf.core.secrets_azure:KeyVaultSecretProvider"

Core never hardcodes a vendor: it asks a :class:`PluginRegistry` for the kind it needs.

Example:
    >>> from abc import ABC
    >>> class Greeter(ABC): ...
    >>> class English(Greeter): ...
    >>> registry = PluginRegistry[Greeter](PluginKind.DATA_PROVIDER, Greeter, entry_points=list)
    >>> registry.register("english", English)
    >>> registry.get("english") is English
    True
"""

import threading
from collections.abc import Callable, Iterable
from enum import StrEnum
from importlib.metadata import EntryPoint, entry_points
from typing import Final, cast

from paccaassure_taf.core.errors import PluginError

__all__ = ["PLUGIN_GROUP", "PluginKind", "PluginRegistry"]

PLUGIN_GROUP: Final = "paccaassure_taf.plugins"


class PluginKind(StrEnum):
    """Kinds of plugin in the ``paccaassure_taf.plugins`` entry-point group.

    Example:
        >>> PluginKind.SECRET_PROVIDER.value
        'secret_provider'
    """

    ELEMENT_TYPE = "element_type"
    PARSE_TYPE = "parse_type"
    DRIVER_FACTORY = "driver_factory"
    AUTH_PROVIDER = "auth_provider"
    SECRET_PROVIDER = "secret_provider"  # noqa: S105 - a plugin kind, not a credential
    DATA_PROVIDER = "data_provider"
    CONNECTION_PROVIDER = "connection_provider"


def _default_entry_points(group: str) -> Callable[[], Iterable[EntryPoint]]:
    return lambda: entry_points(group=group)


def _origin(entry_point: EntryPoint) -> str:
    dist = entry_point.dist
    return f"{dist.name} {dist.version}" if dist is not None else f"entry point {entry_point.value}"


class PluginRegistry[T]:
    """Discovers, validates and serves plugins of one kind.

    Plugins load lazily on first use and are cached. Two plugins with the same
    name are a startup error (never "last one wins").

    Args:
        kind: The plugin kind; entry points are matched by the ``<kind>.`` name prefix.
        base: The class every plugin must subclass (may be abstract). Pass the same class as the
            type parameter: ``PluginRegistry[SecretProvider](PluginKind.SECRET_PROVIDER, SecretProvider)``.
        group: Entry-point group (default ``paccaassure_taf.plugins``).
        entry_points: Entry-point source (injectable for tests).

    Example:
        >>> registry = PluginRegistry[object](PluginKind.PARSE_TYPE, object, entry_points=list)
        >>> registry.names()
        []
    """

    def __init__(
        self,
        kind: PluginKind,
        base: type,
        *,
        group: str = PLUGIN_GROUP,
        entry_points: Callable[[], Iterable[EntryPoint]] | None = None,
    ) -> None:
        self.kind = kind
        self._base = base
        self._group = group
        self._entry_points = entry_points or _default_entry_points(group)
        self._plugins: dict[str, type[T]] = {}
        self._origins: dict[str, str] = {}
        self._loaded = threading.Event()
        self._lock = threading.Lock()

    def register(self, name: str, plugin: type[T], *, origin: str = "registered in code") -> None:
        """Register a plugin programmatically (tests, or code that cannot declare entry points).

        Example:
            >>> registry = PluginRegistry[object](PluginKind.PARSE_TYPE, object, entry_points=list)
            >>> registry.register("member_ref", str)
        """
        self._ensure_loaded()
        with self._lock:
            self._add(name, plugin, origin)

    def get(self, name: str) -> type[T]:
        """Return the plugin registered under ``name``.

        Raises:
            PluginError: If no plugin has that name (the message lists the available ones).

        Example:
            >>> registry = PluginRegistry[object](PluginKind.PARSE_TYPE, object, entry_points=list)
            >>> registry.register("user_role", str)
            >>> registry.get("user_role")
            <class 'str'>
        """
        self._ensure_loaded()
        key = name.lower()
        if key not in self._plugins:
            available = ", ".join(self.names()) or "none"
            raise PluginError(
                f"No {self.kind.value} plugin named '{name}'",
                cause=f"available {self.kind.value} plugins: {available}",
                fix=(
                    f"Install the package or extra that provides it, or declare an entry point "
                    f'"{self.kind.value}.{key}" in group "{self._group}".'
                ),
            )
        return self._plugins[key]

    def names(self) -> list[str]:
        """Return the registered plugin names, sorted.

        Example:
            >>> PluginRegistry[object](PluginKind.AUTH_PROVIDER, object, entry_points=list).names()
            []
        """
        self._ensure_loaded()
        return sorted(self._plugins)

    def origin(self, name: str) -> str:
        """Return where a plugin came from (distribution and version), for diagnostics.

        Example:
            >>> registry = PluginRegistry[object](PluginKind.PARSE_TYPE, object, entry_points=list)
            >>> registry.register("x", str)
            >>> registry.origin("x")
            'registered in code'
        """
        self.get(name)
        return self._origins[name.lower()]

    def _ensure_loaded(self) -> None:
        if self._loaded.is_set():
            return
        with self._lock:
            if self._loaded.is_set():
                return
            prefix = f"{self.kind.value}."
            for entry_point in self._entry_points():
                if entry_point.name.lower().startswith(prefix):
                    self._add(entry_point.name[len(prefix) :], self._load(entry_point), _origin(entry_point))
            self._loaded.set()

    def _load(self, entry_point: EntryPoint) -> type[T]:
        try:
            loaded: object = entry_point.load()
        except Exception as error:
            raise PluginError(
                f"Could not load {self.kind.value} plugin '{entry_point.name}' ({entry_point.value})",
                cause=f"{type(error).__name__}: {error} — from {_origin(entry_point)}",
                fix="Install the plugin's optional dependencies (its extra), or fix/remove the entry point.",
            ) from error
        if not (isinstance(loaded, type) and issubclass(loaded, self._base)):
            raise PluginError(
                f"{self.kind.value} plugin '{entry_point.name}' is not a {self._base.__name__}",
                cause=f"{entry_point.value} resolved to {loaded!r} — from {_origin(entry_point)}",
                fix=f"Point the entry point at a class that subclasses {self._base.__name__}.",
            )
        return cast("type[T]", loaded)  # safe: issubclass(loaded, base) checked above

    def _add(self, name: str, plugin: type[T], origin: str) -> None:
        key = name.lower()
        if key in self._plugins and self._plugins[key] is not plugin:
            raise PluginError(
                f"Two {self.kind.value} plugins are named '{key}'",
                cause=f"{self._origins[key]} and {origin}",
                fix="Uninstall one of them or rename one entry point; PaccaAssureTAF never picks silently.",
            )
        self._plugins[key] = plugin
        self._origins[key] = origin
