"""IPFS module for SimpleInfra.

Deploy and manage IPFS nodes for decentralized storage.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class IPFSModule(Module):
    """Manages IPFS nodes and pinning services."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        operation = kwargs.get("operation", "install")

        if operation == "install":
            return await self._install_ipfs(connector)
        elif operation == "init":
            return await self._init_ipfs(connector, kwargs)
        elif operation == "run":
            return await self._run_ipfs(connector)
        elif operation == "pin":
            return await self._pin_content(connector, kwargs)
        elif operation == "publish":
            return await self._publish_ipns(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown operation: {operation}",
            )

    async def _install_ipfs(self, connector: "Connector") -> ModuleResult:
        """Install IPFS (Kubo)."""
        commands = [
            "wget https://dist.ipfs.tech/kubo/v0.24.0/kubo_v0.24.0_linux-amd64.tar.gz",
            "tar -xvzf kubo_v0.24.0_linux-amd64.tar.gz",
            "cd kubo && bash install.sh",
            "rm -rf kubo kubo_v0.24.0_linux-amd64.tar.gz",
        ]

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message=f"Failed to install IPFS: {result.stderr}",
                )

        return ModuleResult(changed=True, success=True, message="Installed IPFS")

    async def _init_ipfs(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Initialize IPFS repository."""
        profile = params.get("profile", "server")  # server, lowpower, badgerds

        # Create ipfs user
        await connector.run_command("useradd -m -s /bin/bash ipfs", sudo=True)

        # Initialize IPFS repo
        result = await connector.run_command(
            f"su - ipfs -c 'ipfs init --profile={profile}'",
            sudo=True
        )

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Initialized IPFS with profile: {profile}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to init IPFS: {result.stderr}",
            )

    async def _run_ipfs(self, connector: "Connector") -> ModuleResult:
        """Run IPFS daemon as a systemd service."""
        service_content = """[Unit]
Description=IPFS Daemon
After=network.target

[Service]
Type=simple
User=ipfs
Environment=IPFS_PATH=/home/ipfs/.ipfs
ExecStart=/usr/local/bin/ipfs daemon --enable-gc
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

        await connector.write_file("/etc/systemd/system/ipfs.service", service_content)
        await connector.run_command("systemctl daemon-reload", sudo=True)
        await connector.run_command("systemctl enable ipfs", sudo=True)
        result = await connector.run_command("systemctl start ipfs", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message="Started IPFS daemon",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to start IPFS: {result.stderr}",
            )

    async def _pin_content(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Pin content to IPFS."""
        cid = params.get("cid", "")

        result = await connector.run_command(f"su - ipfs -c 'ipfs pin add {cid}'", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Pinned content: {cid}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to pin: {result.stderr}",
            )

    async def _publish_ipns(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Publish to IPNS."""
        cid = params.get("cid", "")

        result = await connector.run_command(
            f"su - ipfs -c 'ipfs name publish {cid}'",
            sudo=True
        )

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Published to IPNS: {cid}",
                details={"stdout": result.stdout},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to publish: {result.stderr}",
            )


# DSL Syntax:
# task "Setup IPFS Node" on ipfs_server:
#     ipfs install
#     ipfs init profile="server"
#     ipfs run
#
#     # Pin important content
#     ipfs pin cid="QmXyz..."
#     ipfs publish cid="QmAbc..."
