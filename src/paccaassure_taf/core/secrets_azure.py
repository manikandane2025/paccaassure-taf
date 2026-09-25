"""Azure Key Vault secret provider (extra ``secrets-azure``), registered as ``secret_provider.kv``.

References look like ``kv://<vault-name>/<secret-name>`` (optionally ``#<version>``).
Authentication uses ``DefaultAzureCredential`` (workload identity, managed identity,
Azure CLI login, ...), so no credential ever appears in PaccaAssureTAF config.

Example:
    >>> class FakeClient:
    ...     def get_secret(self, name: str, version: str | None = None) -> "FakeSecret":
    ...         return FakeSecret()
    >>> class FakeSecret:
    ...     value = "pw-Northwind-kv"
    >>> provider = KeyVaultSecretProvider(client_factory=lambda vault: FakeClient())
    >>> provider.fetch(SecretRef.parse("kv://northwind-qa/claims-db")).get_secret_value()
    'pw-Northwind-kv'
"""

from collections.abc import Callable
from typing import Protocol, override

from pydantic import SecretStr

from paccaassure_taf.core.errors import SecretError
from paccaassure_taf.core.secrets import SecretProvider, SecretRef, SecretScheme

__all__ = ["KeyVaultSecretProvider"]


class _KeyVaultSecret(Protocol):
    @property
    def value(self) -> str | None: ...


class _KeyVaultClient(Protocol):
    def get_secret(self, name: str, version: str | None = None) -> _KeyVaultSecret: ...


def _azure_client(vault: str) -> _KeyVaultClient:
    try:
        from azure.identity import DefaultAzureCredential  # noqa: PLC0415 - optional extra, imported on use
        from azure.keyvault.secrets import SecretClient  # noqa: PLC0415 - optional extra, imported on use
    except ImportError as error:
        raise SecretError(
            "Azure Key Vault support is not installed",
            cause=str(error),
            fix="Install the extra: paccaassure-taf-core[secrets-azure].",
        ) from error
    return SecretClient(vault_url=f"https://{vault}.vault.azure.net", credential=DefaultAzureCredential())


class KeyVaultSecretProvider(SecretProvider):
    """Resolves ``kv://<vault>/<name>[#<version>]`` via Azure Key Vault.

    Args:
        client_factory: Builds a client per vault name (injectable for tests).

    Example:
        >>> KeyVaultSecretProvider.scheme.value
        'kv'
    """

    scheme = SecretScheme.KEY_VAULT

    def __init__(self, *, client_factory: Callable[[str], _KeyVaultClient] = _azure_client) -> None:
        self._client_factory = client_factory
        self._clients: dict[str, _KeyVaultClient] = {}

    @override
    def fetch(self, ref: SecretRef) -> SecretStr:
        vault, name = ref.path.split("/", 1)
        client = self._clients.get(vault)
        if client is None:
            client = self._clients[vault] = self._client_factory(vault)
        value = client.get_secret(name, version=ref.key).value
        if value is None:
            raise SecretError(
                f"Secret {ref} has no value",
                cause="the Key Vault secret exists but is empty or disabled",
                fix="Set a value for the secret in Key Vault, or fix the reference.",
            )
        return SecretStr(value)
