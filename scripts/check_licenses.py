"""Third-party license allow-list check (ADR-0010, amendment 1).

Inspects every distribution installed in the active environment (run after
``uv sync --all-extras`` so extras and dev tools are included) and evaluates its
license against ``scripts/license_policy.toml``. SPDX expressions are honoured:
``A OR B`` passes if any option is allowed, ``A AND B`` only if all are.
With ``--npm-lock`` it checks the packages of an npm ``package-lock.json`` instead
(the sandbox web app, ADR-0010: sandbox dependencies are checked separately).

Example:
    uv run python scripts/check_licenses.py
    uv run python scripts/check_licenses.py --policy scripts/license_policy.toml --verbose
    uv run python scripts/check_licenses.py --npm-lock sandbox/web/package-lock.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

DEFAULT_POLICY = Path(__file__).resolve().parent / "license_policy.toml"

# Free-text License fields and trove classifiers → SPDX ids.
ALIASES: dict[str, str] = {
    "mit": "MIT",
    "mit license": "MIT",
    "the mit license": "MIT",
    "mit no attribution": "MIT-0",
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "new bsd": "BSD-3-Clause",
    "new bsd license": "BSD-3-Clause",
    "bsd-3": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "bsd 3-clause license": "BSD-3-Clause",
    "3-clause bsd license": "BSD-3-Clause",
    "modified bsd license": "BSD-3-Clause",
    "bsd-2": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "bsd 2-clause license": "BSD-2-Clause",
    "simplified bsd": "BSD-2-Clause",
    "apache": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache license, version 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "apache software license 2.0": "Apache-2.0",
    "psf": "PSF-2.0",
    "psf license": "PSF-2.0",
    "psfl": "PSF-2.0",
    "python software foundation license": "PSF-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
    "mpl-2.0": "MPL-2.0",
    "isc license (iscl)": "ISC",
    "isc": "ISC",
    "the unlicense (unlicense)": "Unlicense",
    "gnu lesser general public license v3 (lgplv3)": "LGPL-3.0-only",
    "gnu lesser general public license v2 or later (lgplv2+)": "LGPL-2.0-or-later",
    "gnu general public license v3 (gplv3)": "GPL-3.0-only",
    "gnu general public license v2 (gplv2)": "GPL-2.0-only",
    "gnu affero general public license v3": "AGPL-3.0-only",
    "historical permission notice and disclaimer (hpnd)": "HPND",
    "universal permissive license (upl)": "UPL-1.0",
}

_TOKEN = re.compile(r"\(|\)|[^\s()]+")


@dataclass(frozen=True)
class Policy:
    """Allow-list policy loaded from TOML."""

    allowed: frozenset[str]
    skip: frozenset[str]
    exceptions: dict[str, dict[str, str | bool]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> Policy:
        """Load the policy file.

        Example:
            Policy.load(Path("scripts/license_policy.toml"))
        """
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls(
            allowed=frozenset(data["policy"]["allowed"]),
            skip=frozenset(_canonical(n) for n in data["policy"].get("skip", [])),
            exceptions={_canonical(k): v for k, v in data.get("exceptions", {}).items()},
        )


@dataclass(frozen=True)
class Verdict:
    """The outcome for one distribution."""

    name: str
    version: str
    license: str
    source: str
    allowed: bool
    note: str = ""


def _canonical(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def normalize(text: str) -> str:
    """Map a free-text license name to an SPDX id when we know it.

    Example:
        normalize("MIT License")  # -> "MIT"
    """
    cleaned = text.strip()
    return ALIASES.get(cleaned.lower(), cleaned)


def evaluate(expression: str, allowed: frozenset[str]) -> bool:
    """Evaluate an SPDX license expression against the allow-list.

    Precedence follows SPDX: WITH binds tightest, then AND, then OR.

    Example:
        evaluate("Apache-2.0 OR UPL-1.0", frozenset({"Apache-2.0"}))  # -> True
    """
    tokens: list[str] = _TOKEN.findall(expression)
    if not tokens:
        return False
    position = 0

    def peek() -> str | None:
        return tokens[position] if position < len(tokens) else None

    def take() -> str:
        nonlocal position
        token = tokens[position]
        position += 1
        return token

    def parse_or() -> bool:
        result = parse_and()
        while (token := peek()) is not None and token.upper() == "OR":
            take()
            right = parse_and()
            result = result or right
        return result

    def parse_and() -> bool:
        result = parse_atom()
        while (token := peek()) is not None and token.upper() == "AND":
            take()
            right = parse_atom()
            result = result and right
        return result

    def parse_atom() -> bool:
        part = take()
        if part == "(":
            result = parse_or()
            take()  # ")"
            return result
        ok = normalize(part.removesuffix("+")) in allowed
        next_token = peek()
        if next_token is not None and next_token.upper() == "WITH":
            take()
            take()  # exception id (e.g. LLVM-exception) never widens or narrows the base license here
        return ok

    try:
        result = parse_or()
    except IndexError:
        return False
    return result and position == len(tokens)


def license_of(dist: Distribution) -> tuple[str, str]:
    """Return (license, source) for a distribution: SPDX expression, License field, or classifiers.

    Example:
        license_of(importlib.metadata.distribution("httpx"))  # -> ("BSD-3-Clause", "License-Expression")
    """
    meta = dist.metadata
    expression = meta.get("License-Expression")
    if expression:
        return expression.strip(), "License-Expression"
    classifiers = [
        c.rsplit("::", 1)[-1].strip()
        for c in meta.get_all("Classifier") or []
        if c.startswith("License ::") and c.count("::") >= 2  # noqa: PLR2004 - "License :: OSI Approved :: X"
    ]
    classifiers = [normalize(c) for c in classifiers if c != "OSI Approved"]
    raw = (meta.get("License") or "").strip()
    short = raw if raw and "\n" not in raw and len(raw) < 80 else ""  # noqa: PLR2004 - full license texts are not ids
    if short and short.upper() not in {"UNKNOWN", "NONE"}:
        normalized = normalize(short)
        if _TOKEN.fullmatch(normalized) or " OR " in normalized or " AND " in normalized:
            return normalized, "License"
        if classifiers:
            return " OR ".join(sorted(set(classifiers))), "Classifier"
        return normalized, "License"
    if classifiers:
        # Several license classifiers on one package mean the user may choose (dual licensing).
        return " OR ".join(sorted(set(classifiers))), "Classifier"
    return "UNKNOWN", "none"


def _verdict(name: str, version: str, license_text: str, source: str, policy: Policy) -> Verdict:
    exception = policy.exceptions.get(_canonical(name))
    if exception is not None:
        license_text = str(exception.get("license", license_text))
        reason = str(exception.get("reason", ""))
        ok = bool(exception.get("approved", False)) or evaluate(license_text, policy.allowed)
        return Verdict(name, version, license_text, "exception", ok and bool(reason), reason)
    return Verdict(name, version, license_text, source, evaluate(license_text, policy.allowed))


def check(dists: Iterable[Distribution], policy: Policy) -> list[Verdict]:
    """Evaluate every distribution against the policy.

    Example:
        check(importlib.metadata.distributions(), Policy.load(DEFAULT_POLICY))
    """
    verdicts: dict[str, Verdict] = {}
    for dist in dists:
        name = dist.metadata["Name"]
        key = _canonical(name)
        if key in policy.skip or key in verdicts:
            continue
        license_text, source = license_of(dist)
        verdicts[key] = _verdict(name, dist.version, license_text, source, policy)
    return sorted(verdicts.values(), key=lambda v: _canonical(v.name))


@dataclass(frozen=True)
class NpmPackage:
    """One package from an npm lockfile (``package-lock.json`` v2/v3 ``packages`` map)."""

    name: str
    version: str
    license: str


def npm_packages(lock_text: str) -> list[NpmPackage]:
    """Parse every installed package (including optional platform binaries) from a lockfile.

    The root project entry (key ``""``) is our own code and is skipped. A missing or
    non-string ``license`` becomes ``UNKNOWN`` (which fails).

    Example:
        npm_packages(Path("sandbox/web/package-lock.json").read_text(encoding="utf-8"))
    """
    data = json.loads(lock_text)
    packages: dict[str, NpmPackage] = {}
    for path, entry in data.get("packages", {}).items():
        if not path or entry.get("link"):
            continue
        name = str(entry.get("name") or path.rsplit("node_modules/", 1)[-1])
        license_value = entry.get("license")
        license_text = license_value.strip() if isinstance(license_value, str) else "UNKNOWN"
        version = str(entry.get("version", "?"))
        packages.setdefault(f"{name}@{version}", NpmPackage(name, version, license_text or "UNKNOWN"))
    return sorted(packages.values(), key=lambda p: (p.name, p.version))


def check_npm(packages: Iterable[NpmPackage], policy: Policy) -> list[Verdict]:
    """Evaluate npm packages against the same policy as Python distributions.

    Example:
        check_npm([NpmPackage("preact", "10.29.8", "MIT")], Policy.load(DEFAULT_POLICY))
    """
    return [
        _verdict(package.name, package.version, normalize(package.license), "package-lock", policy)
        for package in packages
        if _canonical(package.name) not in policy.skip
    ]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the check and print a report; exit 1 on any violation.

    Example:
        main(["--verbose"])
    """
    parser = argparse.ArgumentParser(description="Third-party license allow-list check (ADR-0010).")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--verbose", action="store_true", help="list every distribution, not only failures")
    parser.add_argument("--npm-lock", type=Path, help="check this npm package-lock.json instead of Python")
    args = parser.parse_args(argv)
    policy = Policy.load(args.policy)
    if args.npm_lock is not None:
        verdicts = check_npm(npm_packages(args.npm_lock.read_text(encoding="utf-8")), policy)
    else:
        verdicts = check(distributions(), policy)
    failures = [v for v in verdicts if not v.allowed]
    for verdict in verdicts if args.verbose else failures:
        mark = "ok  " if verdict.allowed else "FAIL"
        note = f"  ({verdict.note})" if verdict.note else ""
        print(f"{mark} {verdict.name}=={verdict.version}  [{verdict.license}]  via {verdict.source}{note}")
    kind = "npm packages" if args.npm_lock is not None else "distributions"
    print(f"\n{len(verdicts)} {kind} checked, {len(failures)} violation(s).")
    if failures:
        print(
            "Fix: replace the dependency, or (only after review) add it under [exceptions] "
            "in scripts/license_policy.toml with a reason."
        )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
