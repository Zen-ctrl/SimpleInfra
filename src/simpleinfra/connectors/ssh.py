"""SSH connector for SimpleInfra.

Connects to remote Linux servers via SSH using asyncssh.
Supports key-based and password authentication.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .base import CommandResult, Connector


class SSHConnector(Connector):
    """Connector for executing actions on remote servers via SSH."""

    def __init__(
        self,
        host: str,
        user: str = "root",
        port: int = 22,
        key_path: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.user = user
        self.port = port
        self.key_path = key_path
        self.password = password
        self._conn: Any = None

    async def connect(self) -> None:
        """Establish SSH connection."""
        try:
            import asyncssh
        except ImportError:
            raise ImportError(
                "asyncssh is required for SSH connections. "
                "Install it with: pip install simpleinfra[ssh] or pip install asyncssh"
            )

        connect_kwargs: dict[str, Any] = {
            "host": self.host,
            "port": self.port,
            "username": self.user,
            "known_hosts": None,  # Accept any host key (for simplicity)
        }

        if self.key_path:
            connect_kwargs["client_keys"] = [self.key_path]
        if self.password:
            connect_kwargs["password"] = self.password

        self._conn = await asyncssh.connect(**connect_kwargs)

    async def disconnect(self) -> None:
        """Close SSH connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    async def run_command(self, command: str, sudo: bool = False) -> CommandResult:
        """Execute a command over SSH."""
        if not self._conn:
            raise RuntimeError("Not connected. Call connect() first.")

        if sudo and self.user != "root":
            command = f"sudo -n {command}"

        result = await self._conn.run(command, check=False)
        return CommandResult(
            exit_code=result.exit_status or 0,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Upload a file via SFTP."""
        if not self._conn:
            raise RuntimeError("Not connected.")

        import asyncssh
        await asyncssh.scp(local_path, (self._conn, remote_path))

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Download a file via SFTP."""
        if not self._conn:
            raise RuntimeError("Not connected.")

        import asyncssh
        await asyncssh.scp((self._conn, remote_path), local_path)

    async def read_file(self, remote_path: str) -> str:
        """Read a remote file's contents."""
        result = await self.run_command(f"cat {remote_path}")
        if not result.success:
            raise FileNotFoundError(f"Remote file not found: {remote_path}")
        return result.stdout

    async def write_file(self, remote_path: str, content: str) -> None:
        """Write content to a remote file."""
        # Use heredoc to avoid quoting issues
        escaped = content.replace("'", "'\"'\"'")
        await self.run_command(f"cat > {remote_path} << 'SIMPLEINFRA_EOF'\n{content}\nSIMPLEINFRA_EOF")

    async def file_exists(self, remote_path: str) -> bool:
        """Check if a remote file exists."""
        result = await self.run_command(f"test -e {remote_path}")
        return result.success

    async def get_file_hash(self, remote_path: str) -> str | None:
        """Get SHA256 hash of a remote file."""
        result = await self.run_command(f"sha256sum {remote_path} 2>/dev/null")
        if result.success:
            return result.stdout.split()[0]
        return None
