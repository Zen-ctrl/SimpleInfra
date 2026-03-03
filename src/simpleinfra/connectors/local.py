"""Local machine connector for SimpleInfra.

Executes commands and file operations on the local machine
using asyncio subprocess and standard file I/O.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
from pathlib import Path

from .base import CommandResult, Connector


class LocalConnector(Connector):
    """Connector for executing actions on the local machine."""

    async def connect(self) -> None:
        # No connection needed for local
        pass

    async def disconnect(self) -> None:
        # No cleanup needed for local
        pass

    async def run_command(self, command: str, sudo: bool = False) -> CommandResult:
        """Execute a shell command locally."""
        if sudo:
            command = f"sudo {command}"

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
            return CommandResult(
                exit_code=proc.returncode or 0,
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
            )
        except Exception as e:
            return CommandResult(exit_code=1, stdout="", stderr=str(e))

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Copy a file locally (local_path -> remote_path)."""
        src = Path(local_path)
        dst = Path(remote_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))

    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Copy a file locally (remote_path -> local_path)."""
        src = Path(remote_path)
        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))

    async def read_file(self, remote_path: str) -> str:
        """Read a local file."""
        return Path(remote_path).read_text(encoding="utf-8")

    async def write_file(self, remote_path: str, content: str) -> None:
        """Write content to a local file."""
        path = Path(remote_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    async def file_exists(self, remote_path: str) -> bool:
        """Check if a local file exists."""
        return Path(remote_path).exists()

    async def get_file_hash(self, remote_path: str) -> str | None:
        """Get SHA256 hash of a local file."""
        path = Path(remote_path)
        if not path.exists():
            return None
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()
