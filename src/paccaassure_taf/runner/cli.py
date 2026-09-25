"""The ``pataf`` command line (Typer). Also runnable as ``python -m paccaassure_taf``.

Commands are thin: they parse arguments, call a package API, print, and map
``PatafError`` to its exit code (REPORTING §6).

Example:
    >>> from typer.testing import CliRunner
    >>> result = CliRunner().invoke(app, ["--version"])
    >>> result.output.startswith("paccaassure-taf-core ")
    True
"""

import json
from collections.abc import Callable, Sequence
from functools import wraps
from pathlib import Path
from typing import Annotated

import typer

from paccaassure_taf import __version__
from paccaassure_taf.core.config import load_config
from paccaassure_taf.core.errors import PatafError
from paccaassure_taf.core.masking import default_masker
from paccaassure_taf.core.runtime import apply_config

__all__ = ["app", "main"]

app = typer.Typer(
    name="pataf",
    help="PaccaAssureTAF — typed, AI-native enterprise test automation.",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
config_app = typer.Typer(help="Inspect the layered configuration.", no_args_is_help=True)
app.add_typer(config_app, name="config")


def _handles_errors[**P](command: Callable[P, None]) -> Callable[P, None]:
    """Print a PatafError's what/cause/fix to stderr and exit with its exit code."""

    @wraps(command)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            command(*args, **kwargs)
        except PatafError as error:
            typer.echo(f"Error: {error}", err=True)
            raise typer.Exit(code=int(error.exit_code)) from error

    return wrapper


def _parse_overrides(pairs: Sequence[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for pair in pairs:
        key, separator, value = pair.partition("=")
        if not separator or not key.strip():
            raise typer.BadParameter(
                f"expected KEY=VALUE (e.g. logging.level=DEBUG), got '{pair}'", param_hint="--set"
            )
        overrides[key.strip()] = value
    return overrides


@app.callback(invoke_without_command=True)
def root(
    version: Annotated[bool, typer.Option("--version", help="Print the installed version and exit.")] = False,
) -> None:
    """PaccaAssureTAF command line."""
    if version:
        typer.echo(f"paccaassure-taf-core {__version__}")
        raise typer.Exit


@config_app.command("show")
@_handles_errors
def config_show(
    root: Annotated[Path, typer.Option(help="Suite root containing pataf.variant.yaml and envs/.")] = Path(),
    env: Annotated[str | None, typer.Option(help="Environment name (else PATAF_ENV, else local).")] = None,
    set_: Annotated[
        list[str] | None, typer.Option("--set", help="Override a value: KEY=VALUE (repeatable).")
    ] = None,
    resolved: Annotated[
        bool, typer.Option("--resolved", help="List every value with the layer that set it.")
    ] = False,
) -> None:
    """Show the merged, validated configuration (secrets are references; sensitive values masked)."""
    config = load_config(root, env=env, overrides=_parse_overrides(set_ or []))
    apply_config(config)  # masking + logging from config take effect before any output
    if resolved:
        typer.echo(config.render())
    else:
        # Secret *references* (env://, kv://) are shown, like --resolved: validation guarantees they are
        # references, never plaintext. String values are still scrubbed for known sensitive patterns.
        typer.echo(json.dumps(_scrub(config.config.model_dump(mode="json")), indent=2))


def _scrub(value: object) -> object:
    if isinstance(value, str):
        return default_masker().scrub(value)
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def main() -> None:
    """Console-script entry point for ``pataf``.

    Example:
        >>> main  # doctest: +ELLIPSIS
        <function main at ...>
    """
    app(prog_name="pataf")
