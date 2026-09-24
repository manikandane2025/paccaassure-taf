r"""Layered config loading with per-value provenance (LAYERING "Config resolution order", ADR-0015).

Order (later wins): core defaults → each app pack's ``pataf.app.yaml`` → ``pataf.variant.yaml``
→ ``envs/<env>.yaml`` → ``PATAF_*`` environment variables → CLI overrides.
Every resolved value remembers which layer set it, so errors and ``pataf config show --resolved``
can say *where* a value came from.

Example:
    >>> import tempfile
    >>> root = Path(tempfile.mkdtemp())
    >>> _ = (root / "pataf.variant.yaml").write_text("project: northwind\nlogging: {level: DEBUG}\n")
    >>> resolved = load_config(root, environ={"PATAF_WAIT__TIMEOUT_S": "45"})
    >>> resolved.config.logging.level.value, resolved.config.wait.timeout_s
    ('DEBUG', 45.0)
    >>> resolved.source_of("logging.level"), resolved.source_of("wait.timeout_s"), resolved.source_of("env")
    ('pataf.variant.yaml', 'env PATAF_WAIT__TIMEOUT_S', 'default')
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import yaml
from pydantic import ValidationError

from paccaassure_taf.core.config.environment import is_ci, process_environment
from paccaassure_taf.core.config.model import PatafConfig
from paccaassure_taf.core.errors import ConfigError
from paccaassure_taf.core.masking import DEFAULT_SENSITIVE_KEYS, JsonValue, default_masker

__all__ = [
    "APP_FILE",
    "ENV_DIR",
    "ENV_PREFIX",
    "VARIANT_FILE",
    "ConfigEntry",
    "ConfigLayer",
    "ResolvedConfig",
    "load_config",
]

APP_FILE: Final = "pataf.app.yaml"
VARIANT_FILE: Final = "pataf.variant.yaml"
ENV_DIR: Final = "envs"
ENV_PREFIX: Final = "PATAF_"
_NESTED: Final = "__"
_DEFAULT_ENV: Final = "local"

type _Tree = dict[str, object]


@dataclass(frozen=True)
class ConfigLayer:
    """One source of config values, e.g. a YAML file or the ``PATAF_*`` environment.

    Example:
        >>> ConfigLayer("cli", {"logging": {"level": "DEBUG"}}).name
        'cli'
    """

    name: str
    data: _Tree


@dataclass(frozen=True)
class ConfigEntry:
    """One resolved leaf value (masked) and the layer that set it.

    Example:
        >>> ConfigEntry("logging.level", "INFO", "default").key
        'logging.level'
    """

    key: str
    value: JsonValue
    source: str


@dataclass(frozen=True)
class ResolvedConfig:
    """The validated config plus provenance.

    Example:
        >>> resolved = load_config(Path("."), environ={})
        >>> resolved.allow_file_refs
        True
    """

    config: PatafConfig
    sources: Mapping[str, str]
    ci: bool

    @property
    def allow_file_refs(self) -> bool:
        """Whether ``file://`` secrets may be used: config value if set, else "not in CI".

        Example:
            >>> load_config(Path("."), environ={"CI": "true"}).allow_file_refs
            False
        """
        configured = self.config.secrets.allow_file_refs
        return (not self.ci) if configured is None else configured

    def source_of(self, key: str) -> str:
        """Return the layer that set dotted ``key``, else ``default``.

        A leaf inherits from its nearest parent (a scalar or list replaced wholesale); a section is
        attributed to the layers that set its values (joined with ``+`` if several).

        Example:
            >>> load_config(Path("."), environ={}).source_of("logging.level")
            'default'
        """
        parts = key.split(".")
        for size in range(len(parts), 0, -1):
            source = self.sources.get(".".join(parts[:size]))
            if source is not None:
                return source
        children = {source for dotted, source in self.sources.items() if dotted.startswith(f"{key}.")}
        return " + ".join(sorted(children)) if children else "default"

    def entries(self) -> list[ConfigEntry]:
        """Every resolved leaf value, masked, with its source — for ``pataf config show --resolved``.

        Example:
            >>> entries = load_config(Path("."), environ={}).entries()
            >>> ("env", "local", "default") in [(e.key, e.value, e.source) for e in entries]
            True
        """
        masker = default_masker()
        flat = _flatten(self.config.model_dump(mode="json"))
        return [
            ConfigEntry(key, masker.mask(value), self.source_of(key)) for key, value in sorted(flat.items())
        ]

    def render(self) -> str:
        """Render entries as aligned ``key = value  [source]`` lines.

        Example:
            >>> lines = load_config(Path("."), environ={}).render().splitlines()
            >>> next(line for line in lines if line.startswith("env ")).split()
            ['env', '=', "'local'", '[default]']
        """
        entries = self.entries()
        width = max((len(e.key) for e in entries), default=0)
        return "\n".join(f"{e.key.ljust(width)} = {e.value!r}  [{e.source}]" for e in entries)


def load_config(
    root: Path,
    *,
    env: str | None = None,
    app_files: Sequence[Path] = (),
    overrides: Mapping[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> ResolvedConfig:
    """Load, merge and validate configuration for the suite rooted at ``root``.

    Args:
        root: Variant-suite (or project) root containing ``pataf.variant.yaml`` and ``envs/``.
        env: Environment name from the CLI (``--env``); else ``PATAF_ENV``; else ``local``.
        app_files: Packaged ``pataf.app.yaml`` files of installed app packs, in dependency order.
        overrides: CLI overrides as dotted keys (``{"logging.level": "DEBUG"}``).
        environ: Environment mapping (default: the real process environment).

    Raises:
        ConfigError: Unreadable/invalid YAML, a missing env file, or values that fail validation.
            The message names the offending key and the layer it came from.

    Example:
        >>> load_config(Path("."), env="local", overrides={"project": "northwind"}, environ={}).config.project
        'northwind'
    """
    environ = process_environment() if environ is None else environ
    env_name = env or environ.get(f"{ENV_PREFIX}ENV") or _DEFAULT_ENV

    layers = [ConfigLayer(path.name, _read_yaml(path)) for path in app_files]
    variant_file = root / VARIANT_FILE
    if variant_file.is_file():
        layers.append(ConfigLayer(VARIANT_FILE, _read_yaml(variant_file)))
    env_file = root / ENV_DIR / f"{env_name}.yaml"
    if env_file.is_file():
        layers.append(ConfigLayer(f"{ENV_DIR}/{env_file.name}", _read_yaml(env_file)))
    elif env_name != _DEFAULT_ENV:
        raise ConfigError(
            f"Environment '{env_name}' has no config file",
            cause=f"{env_file} does not exist",
            fix=f"Create {ENV_DIR}/{env_name}.yaml (it may be empty), or pass the right --env.",
        )
    layers.extend(_environment_layers(environ))
    cli: _Tree = {}
    for key, value in (overrides or {}).items():
        _set_dotted(cli, key, _parse_scalar(value))
    if env is not None:
        cli["env"] = env
    if cli:
        layers.append(ConfigLayer("cli", cli))

    merged: _Tree = {}
    sources: dict[str, str] = {}
    for layer in layers:
        _merge(merged, layer.data, layer.name, sources, prefix="")
    return ResolvedConfig(_validate(merged, sources), sources, is_ci(environ))


def _read_yaml(path: Path) -> _Tree:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(
            f"Config file {path} could not be read",
            cause=f"{type(error).__name__}: {error.strerror}",
            fix="Check the path and permissions.",
        ) from error
    try:
        data: object = yaml.safe_load(text)
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        where = f"line {mark.line + 1}, column {mark.column + 1}: " if mark is not None else ""
        raise ConfigError(
            f"{path.name} is not valid YAML",
            cause=f"{where}{getattr(error, 'problem', None) or error}",
            fix="Fix the YAML syntax (indentation uses spaces; quote values containing ':' or '#').",
        ) from error
    if data is None:
        return {}
    if not isinstance(data, dict) or not all(isinstance(k, str) for k in data):
        raise ConfigError(
            f"{path.name} must be a mapping of setting names to values",
            cause=f"top level is {type(data).__name__}",
            fix="Start the file with keys such as 'project:' or 'logging:'.",
        )
    return data


def _environment_layers(environ: Mapping[str, str]) -> list[ConfigLayer]:
    layers = []
    for name in sorted(environ):
        if not name.upper().startswith(ENV_PREFIX):
            continue
        key = name[len(ENV_PREFIX) :].lower().replace(_NESTED, ".")
        tree: _Tree = {}
        _set_dotted(tree, key, _parse_scalar(environ[name]))
        layers.append(ConfigLayer(f"env {name}", tree))
    return layers


def _parse_scalar(text: str) -> object:
    stripped = text.strip()
    if stripped.startswith(("[", "{")):
        try:
            parsed: object = json.loads(stripped)
        except json.JSONDecodeError:
            return text
        return parsed
    return text


def _set_dotted(tree: _Tree, key: str, value: object) -> None:
    parts = [p for p in key.split(".") if p]
    node = tree
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = node[part] = {}
        node = child
    node[parts[-1]] = value


def _merge(base: _Tree, update: _Tree, source: str, sources: dict[str, str], *, prefix: str) -> None:
    for key, value in update.items():
        dotted = f"{prefix}{key}"
        existing = base.get(key)
        if isinstance(value, dict) and isinstance(existing, dict):
            _merge(existing, value, source, sources, prefix=f"{dotted}.")
            continue
        for stale in [k for k in sources if k.startswith(f"{dotted}.")]:
            del sources[stale]
        if isinstance(value, dict):
            # A new section: only its leaves get a source, so untouched siblings keep "default".
            child: _Tree = {}
            base[key] = child
            sources.pop(dotted, None)
            _merge(child, value, source, sources, prefix=f"{dotted}.")
        else:
            base[key] = value
            sources[dotted] = source


def _flatten(data: object, prefix: str = "") -> dict[str, object]:
    if isinstance(data, dict) and data:
        flat: dict[str, object] = {}
        for key, value in data.items():
            flat.update(_flatten(value, f"{prefix}{key}."))
        return flat
    return {prefix.rstrip("."): data}


def _is_sensitive_key(dotted: str) -> bool:
    return any(part.lower() in DEFAULT_SENSITIVE_KEYS for part in dotted.split("."))


def _validate(merged: _Tree, sources: Mapping[str, str]) -> PatafConfig:
    try:
        return PatafConfig.model_validate(merged)
    except ValidationError as error:
        resolved = ResolvedConfig(PatafConfig(), sources, ci=False)
        masker = default_masker()
        problems = []
        for detail in error.errors():
            key = ".".join(str(part) for part in detail["loc"])
            message = str(detail["msg"])
            bad_input = detail.get("input")
            if isinstance(bad_input, str) and bad_input and _is_sensitive_key(key):
                message = message.replace(bad_input, masker.mask_text)
            problems.append(f"{key}: {masker.scrub(message)} (set by {resolved.source_of(key)})")
        raise ConfigError(
            f"Invalid configuration ({len(problems)} problem{'s' if len(problems) > 1 else ''})",
            cause=f"{len(problems)} invalid setting{'s' if len(problems) > 1 else ''}:\n    - "
            + "\n    - ".join(problems),
            fix="Correct the values above in the named layer; `pataf config show --resolved` lists "
            "every value and its source.",
        ) from error
