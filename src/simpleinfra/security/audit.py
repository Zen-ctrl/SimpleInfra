"""Audit logging for SimpleInfra.

Logs all actions for security compliance and debugging.
Supports multiple backends: file, syslog, cloud logging.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


class AuditLogger:
    """Audit logger for tracking all infrastructure changes."""

    def __init__(self, log_file: Path | None = None):
        self.log_file = log_file or Path.home() / ".simpleinfra" / "audit.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Setup Python logger
        self.logger = logging.getLogger("simpleinfra.audit")
        self.logger.setLevel(logging.INFO)

        # File handler
        fh = logging.FileHandler(self.log_file)
        fh.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(fh)

    def log_action(
        self,
        action: str,
        target: str,
        user: str,
        success: bool,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an infrastructure action."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "target": target,
            "user": user,
            "success": success,
            "details": details or {},
        }
        self.logger.info(json.dumps(entry))

    def log_connection(self, target: str, user: str, success: bool, method: str) -> None:
        """Log a connection attempt."""
        self.log_action(
            action="connect",
            target=target,
            user=user,
            success=success,
            details={"method": method},
        )

    def log_command(self, target: str, command: str, exit_code: int, user: str) -> None:
        """Log command execution."""
        self.log_action(
            action="run_command",
            target=target,
            user=user,
            success=exit_code == 0,
            details={"command": command, "exit_code": exit_code},
        )

    def log_file_transfer(self, source: str, dest: str, target: str, user: str, success: bool) -> None:
        """Log file transfer."""
        self.log_action(
            action="file_transfer",
            target=target,
            user=user,
            success=success,
            details={"source": source, "destination": dest},
        )

    def get_audit_trail(self, target: str | None = None, limit: int = 100) -> list[dict]:
        """Retrieve audit trail."""
        entries = []
        if not self.log_file.exists():
            return entries

        with open(self.log_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if target is None or entry["target"] == target:
                        entries.append(entry)
                        if len(entries) >= limit:
                            break
                except json.JSONDecodeError:
                    continue

        return entries
