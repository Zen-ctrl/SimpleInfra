"""Abstract connector interface for SimpleInfra.

All connectors (SSH, Local, Docker, Cloud) implement this interface.
This is the boundary between "what to do" (modules) and "where to do it"
(connectors).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CommandResult:
    """Result of executing a command on a target."""
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.exit_code == 0


class Connector(ABC):
    """Abstract interface that every target connector must implement."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the target."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Clean up the connection."""

    @abstractmethod
    async def run_command(self, command: str, sudo: bool = False) -> CommandResult:
        """Execute a shell command on the target."""

    @abstractmethod
    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Transfer a file from local to target."""

    @abstractmethod
    async def download_file(self, remote_path: str, local_path: str) -> None:
        """Transfer a file from target to local."""

    @abstractmethod
    async def read_file(self, remote_path: str) -> str:
        """Read file contents from target."""

    @abstractmethod
    async def write_file(self, remote_path: str, content: str) -> None:
        """Write content to a file on the target."""

    @abstractmethod
    async def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the target."""

    @abstractmethod
    async def get_file_hash(self, remote_path: str) -> str | None:
        """Get SHA256 hash of a file on target. Returns None if file doesn't exist."""

    async def __aenter__(self) -> Connector:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.disconnect()
