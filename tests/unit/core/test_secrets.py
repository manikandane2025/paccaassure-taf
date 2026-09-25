from pathlib import Path
from typing import override

import pytest
from pydantic import BaseModel, SecretStr, ValidationError

from paccaassure_taf.core.errors import SecretError
from paccaassure_taf.core.masking import Masker
from paccaassure_taf.core.plugins import PluginKind, PluginRegistry
from paccaassure_taf.core.secrets import (
    EnvSecretProvider,
    FileSecretProvider,
    SecretProvider,
    SecretRef,
    SecretResolver,
    SecretScheme,
    build_secret_resolver,
)
from paccaassure_taf.core.secrets_azure import KeyVaultSecretProvider


@pytest.mark.parametrize(
    ("text", "scheme", "path", "key"),
    [
        ("env://DB_PASSWORD", SecretScheme.ENV, "DB_PASSWORD", None),
        ("kv://northwind-qa/claims-db", SecretScheme.KEY_VAULT, "northwind-qa/claims-db", None),
        ("kv://northwind-qa/claims-db#v2", SecretScheme.KEY_VAULT, "northwind-qa/claims-db", "v2"),
        ("hcv://secret/data/claims#password", SecretScheme.HASHICORP_VAULT, "secret/data/claims", "password"),
        ("file://secrets/local.txt", SecretScheme.FILE, "secrets/local.txt", None),
    ],
)
def test_parse_and_round_trip(text: str, scheme: SecretScheme, path: str, key: str | None) -> None:
    ref = SecretRef.parse(text)
    assert (ref.scheme, ref.path, ref.key) == (scheme, path, key)
    assert str(ref) == text


@pytest.mark.parametrize(
    "text",
    [
        "DB_PASSWORD",
        "vault://x",
        "env://1BAD",
        "kv://no-slash",
        "kv://a/b/c",
        "hcv://path-without-key",
        "env://",
    ],
)
def test_invalid_refs_raise_actionable_errors(text: str) -> None:
    with pytest.raises(SecretError) as info:
        SecretRef.parse(text)
    assert info.value.fix is not None
    assert "env://VAR" in info.value.fix


def test_secret_ref_as_a_config_field_validates_and_serializes_as_string() -> None:
    class User(BaseModel):
        username: str
        password: SecretRef

    user = User.model_validate({"username": "eligibility_worker", "password": "env://EW_PASSWORD"})
    assert user.password.scheme is SecretScheme.ENV
    assert user.model_dump() == {"username": "eligibility_worker", "password": "env://EW_PASSWORD"}
    with pytest.raises(ValidationError):
        User.model_validate({"username": "x", "password": "plaintext-password"})


def test_env_provider_and_missing_variable() -> None:
    provider = EnvSecretProvider({"A": "pw-Northwind-a"})
    assert provider.fetch(SecretRef.parse("env://A")).get_secret_value() == "pw-Northwind-a"
    with pytest.raises(SecretError, match="is not set") as info:
        provider.fetch(SecretRef.parse("env://MISSING"))
    assert info.value.fix is not None
    assert "Set MISSING" in info.value.fix


def test_file_provider_allowed_blocked_and_missing(tmp_path: Path) -> None:
    (tmp_path / "db.txt").write_text("pw-Northwind-file\n", encoding="utf-8")
    ref = SecretRef.parse("file://db.txt")
    assert (
        FileSecretProvider(allowed=True, base_dir=tmp_path).fetch(ref).get_secret_value()
        == "pw-Northwind-file"
    )
    absolute = SecretRef.parse(f"file://{(tmp_path / 'db.txt').as_posix()}")
    assert FileSecretProvider(allowed=True).fetch(absolute).get_secret_value() == "pw-Northwind-file"
    with pytest.raises(SecretError, match="blocked in CI"):
        FileSecretProvider(allowed=False, base_dir=tmp_path).fetch(ref)
    with pytest.raises(SecretError, match="could not be read"):
        FileSecretProvider(allowed=True, base_dir=tmp_path).fetch(SecretRef.parse("file://nope.txt"))


def test_resolver_caches_and_registers_value_for_masking() -> None:
    calls = {"n": 0}

    class Counting(EnvSecretProvider):
        @override
        def fetch(self, ref: SecretRef) -> SecretStr:
            calls["n"] += 1
            return super().fetch(ref)

    masker = Masker()
    resolver = SecretResolver([Counting({"TOKEN": "tok-Northwind-777"})], masker=masker)
    first = resolver.resolve("env://TOKEN")
    second = resolver.resolve(SecretRef.parse("env://TOKEN"))
    assert first is second
    assert calls["n"] == 1
    assert masker.scrub("Authorization failed for tok-Northwind-777") == "Authorization failed for ***"


def test_resolver_unknown_scheme_points_to_the_extra() -> None:
    with pytest.raises(SecretError) as info:
        SecretResolver([EnvSecretProvider({})], masker=Masker()).resolve("kv://northwind-qa/db")
    assert info.value.cause == "available: env"
    assert info.value.fix == "Install the extra: paccaassure-taf-core[secrets-azure]."


def test_resolver_wraps_unexpected_provider_errors_and_masks_them() -> None:
    masker = Masker()
    masker.register("pw-Northwind-leak")

    class Broken(SecretProvider):
        scheme = SecretScheme.HASHICORP_VAULT

        @override
        def fetch(self, ref: SecretRef) -> SecretStr:
            raise RuntimeError("vault said pw-Northwind-leak is wrong")

    with pytest.raises(SecretError) as info:
        SecretResolver([Broken()], masker=masker).resolve("hcv://secret/claims#pw")
    assert "pw-Northwind-leak" not in str(info.value)
    assert "RuntimeError" in str(info.value.cause)


class FakeSecret:
    def __init__(self, value: str | None) -> None:
        self.value = value


class FakeClient:
    def __init__(self, values: dict[str, str | None]) -> None:
        self.values = values
        self.calls: list[tuple[str, str | None]] = []

    def get_secret(self, name: str, version: str | None = None) -> FakeSecret:
        self.calls.append((name, version))
        return FakeSecret(self.values[name])


def test_key_vault_provider_uses_one_client_per_vault_and_versions() -> None:
    clients: dict[str, FakeClient] = {}

    def factory(vault: str) -> FakeClient:
        clients[vault] = FakeClient({"db": "pw-Northwind-kv", "empty": None})
        return clients[vault]

    provider = KeyVaultSecretProvider(client_factory=factory)
    assert provider.fetch(SecretRef.parse("kv://northwind-qa/db")).get_secret_value() == "pw-Northwind-kv"
    provider.fetch(SecretRef.parse("kv://northwind-qa/db#v2"))
    assert list(clients) == ["northwind-qa"]
    assert clients["northwind-qa"].calls == [("db", None), ("db", "v2")]
    with pytest.raises(SecretError, match="has no value"):
        provider.fetch(SecretRef.parse("kv://northwind-qa/empty"))


def test_default_azure_client_builds_with_the_extra_installed() -> None:
    from paccaassure_taf.core.secrets_azure import _azure_client  # noqa: PLC0415

    client = _azure_client("northwind-qa")  # no network call until get_secret()
    assert type(client).__name__ == "SecretClient"


def test_build_secret_resolver_includes_builtins_and_plugins() -> None:
    registry = PluginRegistry[SecretProvider](PluginKind.SECRET_PROVIDER, SecretProvider, entry_points=list)
    registry.register("kv", KeyVaultSecretProvider)
    resolver = build_secret_resolver(environ={"A": "x"}, allow_file_refs=False, registry=registry)
    assert resolver.schemes == {SecretScheme.ENV, SecretScheme.FILE, SecretScheme.KEY_VAULT}


def test_installed_entry_point_registers_key_vault() -> None:
    resolver = build_secret_resolver(environ={}, allow_file_refs=False)
    assert SecretScheme.KEY_VAULT in resolver.schemes
