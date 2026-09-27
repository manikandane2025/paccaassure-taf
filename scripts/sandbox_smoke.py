"""Smoke-probe the running Northwind Health sandbox: container health + one probe per app.

Ports come from the environment (``NWH_SANDBOX_*``, which docker compose also honours first),
then ``sandbox/.env``, then ``sandbox/env.example`` — the same precedence compose uses, so the
probe hits the ports the containers were published on.

Example:
    uv run python scripts/sandbox_smoke.py
    uv run python scripts/dev.py sandbox-smoke
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
SANDBOX = REPO_ROOT / "sandbox"
COMPOSE_FILE = SANDBOX / "compose.yaml"
ENV_FILE = SANDBOX / ".env"
ENV_TEMPLATE = SANDBOX / "env.example"
SERVICES = ("postgres", "api", "web")
SEEDED_MEMBERS = 250
PORT_DEFAULTS: dict[str, int] = {
    "NWH_SANDBOX_WEB_PORT": 18081,
    "NWH_SANDBOX_API_PORT": 18083,
    "NWH_SANDBOX_DB_PORT": 15433,
}
# Synthetic sandbox credential (sandbox/README.md), never a real secret.
EXAMINER = {"username": "examiner", "password": "pw-Northwind-examiner"}


def parse_env_file(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` lines as docker compose does for simple files (comments, blanks, quotes).

    Example:
        >>> parse_env_file("# ports" + chr(10) + "NWH_SANDBOX_WEB_PORT=18081" + chr(10) + "X='a b'")
        {'NWH_SANDBOX_WEB_PORT': '18081', 'X': 'a b'}
    """
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:  # noqa: PLR2004 - quote pair
            value = value[1:-1]
        values[key.strip()] = value
    return values


def resolve_ports(environ: Mapping[str, str], env_file: Path, template: Path) -> dict[str, int]:
    """Resolve sandbox ports: process environment, then ``sandbox/.env``, then the template, then defaults.

    Example:
        >>> ports = resolve_ports({"NWH_SANDBOX_WEB_PORT": "28081"}, Path("missing"), Path("missing"))
        >>> ports["NWH_SANDBOX_WEB_PORT"], ports["NWH_SANDBOX_API_PORT"]
        (28081, 18083)
    """
    layers = [environ]
    for path in (env_file, template):
        if path.is_file():
            layers.append(parse_env_file(path.read_text(encoding="utf-8")))
            break
    ports: dict[str, int] = {}
    for key, default in PORT_DEFAULTS.items():
        value = next((layer[key] for layer in layers if layer.get(key)), None)
        ports[key] = int(value) if value is not None else default
    return ports


@dataclass(frozen=True)
class Probe:
    """One named smoke check; ``run`` returns a short detail line or raises on failure."""

    name: str
    run: Callable[[], str]


def compose(*args: str) -> list[str]:
    """Build a ``docker compose`` command for the sandbox project.

    Example:
        compose("ps")  # -> ["docker", "compose", "-f", ".../sandbox/compose.yaml", "ps"]
    """
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *args]


def container_health() -> str:
    """Report ``docker compose ps`` health for every sandbox service; raise unless all are healthy.

    Example:
        container_health()  # -> "postgres=healthy api=healthy web=healthy"
    """
    completed = subprocess.run(
        compose("ps", "--all", "--format", "json"), capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "docker compose ps failed (is Docker running?)")
    # Compose prints one JSON object per line (older versions: one JSON array).
    text = completed.stdout.strip()
    rows = json.loads(text) if text.startswith("[") else [json.loads(line) for line in text.splitlines()]
    health = {row["Service"]: row.get("Health") or row.get("State", "?") for row in rows}
    summary = " ".join(f"{service}={health.get(service, 'missing')}" for service in SERVICES)
    if any(health.get(service) != "healthy" for service in SERVICES):
        raise RuntimeError(summary)
    return summary


def probe_postgres(port: int) -> str:
    """TCP reachability on the published port, then seed and history database checks via psql.

    Example:
        probe_postgres(15433)  # -> "127.0.0.1:15433 open; northwind members=250; pataf_history present"
    """
    with socket.create_connection(("127.0.0.1", port), timeout=5):
        pass
    query = (
        "SELECT (SELECT count(*) FROM members) || ' ' || "
        "(SELECT count(*) FROM pg_database WHERE datname = 'pataf_history')"
    )
    completed = subprocess.run(
        compose("exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "northwind", "-tAc", query),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    members, history = completed.stdout.split()
    if int(members) != SEEDED_MEMBERS or history != "1":
        raise RuntimeError(f"unexpected seed: members={members} pataf_history={history}")
    return f"127.0.0.1:{port} open; northwind members={members}; pataf_history present"


def probe_api(client: httpx.Client, port: int) -> str:
    """Health, token, and one authenticated read of the well-known member.

    Example:
        probe_api(httpx.Client(), 18083)  # -> "health ok; token (EXAMINER); NWH-M000123 = Ava Thompson"
    """
    base = f"http://127.0.0.1:{port}"
    health = client.get(f"{base}/health").raise_for_status().json()
    if health.get("status") != "ok":
        raise RuntimeError(f"health: {health}")
    token = client.post(f"{base}/auth/token", json=EXAMINER).raise_for_status().json()
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    member = client.get(f"{base}/members/NWH-M000123", headers=headers).raise_for_status().json()
    return f"health ok; token ({token['role']}); NWH-M000123 = {member['first_name']} {member['last_name']}"


def probe_web(client: httpx.Client, port: int) -> str:
    """SPA shell on a deep link (nginx history fallback) and the /api proxy.

    Example:
        probe_web(httpx.Client(), 18081)  # -> "deep link /members/NWH-M000123 -> SPA shell; /api/health ok"
    """
    base = f"http://127.0.0.1:{port}"
    page = client.get(f"{base}/members/NWH-M000123").raise_for_status()
    if '<div id="app">' not in page.text or "Northwind Health" not in page.text:
        raise RuntimeError("deep link did not return the SPA shell")
    health = client.get(f"{base}/api/health").raise_for_status().json()
    if health.get("status") != "ok":
        raise RuntimeError(f"/api/health via nginx: {health}")
    return "deep link /members/NWH-M000123 -> SPA shell; /api/health ok"


def run(probes: Sequence[Probe]) -> int:
    """Run every probe, print PASS/FAIL lines, and return the exit code (0 only if all passed).

    Example:
        run([Probe("noop", lambda: "fine")])  # prints "PASS  noop  fine", returns 0
    """
    failed = 0
    for probe in probes:
        try:
            detail = probe.run()
        except (OSError, RuntimeError, ValueError, KeyError, httpx.HTTPError) as error:
            failed += 1
            print(f"FAIL  {probe.name:<10} {type(error).__name__}: {error}")
        else:
            print(f"PASS  {probe.name:<10} {detail}")
    print(f"\n{len(probes) - failed}/{len(probes)} sandbox probes passed.")
    return 1 if failed else 0


def main() -> int:
    """Probe the sandbox using the resolved ports.

    Example:
        main()  # -> 0 when every container is healthy and every app answers
    """
    ports = resolve_ports(os.environ, ENV_FILE, ENV_TEMPLATE)
    print(
        "Sandbox ports: web {NWH_SANDBOX_WEB_PORT}, api {NWH_SANDBOX_API_PORT}, "
        "postgres {NWH_SANDBOX_DB_PORT} (127.0.0.1)".format(**ports)
    )
    with httpx.Client(timeout=10) as client:
        return run(
            [
                Probe("health", container_health),
                Probe("postgres", lambda: probe_postgres(ports["NWH_SANDBOX_DB_PORT"])),
                Probe("api", lambda: probe_api(client, ports["NWH_SANDBOX_API_PORT"])),
                Probe("web", lambda: probe_web(client, ports["NWH_SANDBOX_WEB_PORT"])),
            ]
        )


if __name__ == "__main__":
    sys.exit(main())
