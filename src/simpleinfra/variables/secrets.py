"""Secret loading for SimpleInfra.

Supports loading secrets from:
- Environment variables
- Files on disk
- .env files (via python-dotenv)
"""

from __future__ import annotations

import os
from pathlib import Path

from ..ast.nodes import SecretDecl
from ..errors.runtime_errors import SimpleInfraError


class SecretLoadError(SimpleInfraError):
    """Raised when a secret cannot be loaded."""

    def __init__(self, secret_name: str, message: str):
        super().__init__(f"Cannot load secret '{secret_name}': {message}")


def load_secrets(secret_decls: tuple[SecretDecl, ...], project_dir: Path | None = None) -> dict[str, str]:
    """Load all declared secrets and return a name -> value mapping.

    Args:
        secret_decls: Secret declarations from the AST.
        project_dir: Base directory for resolving relative file paths.

    Returns:
        Dictionary mapping secret names to their values.

    Raises:
        SecretLoadError: If a secret cannot be loaded.
    """
    # Try loading .env file if it exists
    if project_dir:
        env_file = project_dir / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                pass  # python-dotenv not installed, skip

    secrets: dict[str, str] = {}

    for decl in secret_decls:
        if decl.source_type == "env":
            value = os.environ.get(decl.source_value)
            if value is None:
                raise SecretLoadError(
                    decl.name,
                    f"Environment variable '{decl.source_value}' is not set",
                )
            secrets[decl.name] = value

        elif decl.source_type == "file":
            file_path = Path(decl.source_value)
            if project_dir and not file_path.is_absolute():
                file_path = project_dir / file_path

            if not file_path.exists():
                raise SecretLoadError(
                    decl.name,
                    f"Secret file '{file_path}' does not exist",
                )
            secrets[decl.name] = file_path.read_text(encoding="utf-8").strip()

    return secrets
