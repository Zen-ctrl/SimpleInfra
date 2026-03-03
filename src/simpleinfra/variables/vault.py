"""Vault integration for secure secret storage.

Supports multiple vault backends:
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Encrypted local files (using Fernet)
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class VaultBackend:
    """Base class for vault backends."""

    async def get_secret(self, key: str) -> str:
        raise NotImplementedError


class LocalEncryptedVault(VaultBackend):
    """Local encrypted vault using Fernet symmetric encryption."""

    def __init__(self, vault_file: Path, password: str | None = None):
        self.vault_file = vault_file
        self.password = password or os.environ.get("SIMPLEINFRA_VAULT_PASSWORD", "")
        self._secrets: dict[str, str] = {}

    async def get_secret(self, key: str) -> str:
        """Get a secret from the encrypted vault."""
        if not self._secrets:
            await self._load_vault()
        return self._secrets.get(key, "")

    async def set_secret(self, key: str, value: str) -> None:
        """Store a secret in the vault."""
        if not self._secrets:
            await self._load_vault()
        self._secrets[key] = value
        await self._save_vault()

    async def _load_vault(self) -> None:
        """Load and decrypt the vault file."""
        if not self.vault_file.exists():
            self._secrets = {}
            return

        try:
            from cryptography.fernet import Fernet
            import hashlib

            # Derive key from password
            key = base64.urlsafe_b64encode(hashlib.sha256(self.password.encode()).digest())
            cipher = Fernet(key)

            encrypted = self.vault_file.read_bytes()
            decrypted = cipher.decrypt(encrypted)
            self._secrets = json.loads(decrypted.decode())
        except ImportError:
            raise ImportError(
                "cryptography is required for vault encryption. "
                "Install with: pip install cryptography"
            )

    async def _save_vault(self) -> None:
        """Encrypt and save the vault file."""
        from cryptography.fernet import Fernet
        import hashlib

        key = base64.urlsafe_b64encode(hashlib.sha256(self.password.encode()).digest())
        cipher = Fernet(key)

        plaintext = json.dumps(self._secrets).encode()
        encrypted = cipher.encrypt(plaintext)

        self.vault_file.parent.mkdir(parents=True, exist_ok=True)
        self.vault_file.write_bytes(encrypted)


class HashiCorpVault(VaultBackend):
    """HashiCorp Vault backend."""

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token

    async def get_secret(self, key: str) -> str:
        """Get secret from HashiCorp Vault."""
        try:
            import hvac
            client = hvac.Client(url=self.url, token=self.token)
            response = client.secrets.kv.v2.read_secret_version(path=key)
            return response["data"]["data"]["value"]
        except ImportError:
            raise ImportError("hvac is required for HashiCorp Vault. Install with: pip install hvac")


class AWSSecretsManager(VaultBackend):
    """AWS Secrets Manager backend."""

    def __init__(self, region: str = "us-east-1"):
        self.region = region

    async def get_secret(self, key: str) -> str:
        """Get secret from AWS Secrets Manager."""
        try:
            import boto3
            client = boto3.client("secretsmanager", region_name=self.region)
            response = client.get_secret_value(SecretId=key)
            return response["SecretString"]
        except ImportError:
            raise ImportError("boto3 is required for AWS Secrets Manager. Install with: pip install boto3")


# Updated DSL syntax for vault secrets:
# secret db_password from vault "database/password"
# secret api_key from aws_secrets "prod/api_key"
# secret cert from hashicorp_vault "pki/cert"
