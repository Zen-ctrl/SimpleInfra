"""Ethereum node module for SimpleInfra.

Makes it trivial to spin up Ethereum full nodes, archive nodes,
and validators.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class EthereumModule(Module):
    """Manages Ethereum nodes (Geth, Erigon, Nethermind, Besu)."""

    # Default configurations for different node types
    NODE_CONFIGS = {
        "geth": {
            "full": "--syncmode=snap --http --http.api=eth,net,web3",
            "archive": "--syncmode=full --gcmode=archive --http --http.api=eth,net,web3,debug,txpool",
            "light": "--syncmode=light --http --http.api=eth,net,web3",
        },
        "erigon": {
            "full": "--prune=hrtc --http --http.api=eth,net,web3",
            "archive": "--http --http.api=eth,net,web3,debug,trace",
        },
    }

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        operation = kwargs.get("operation", "run")

        if operation == "install":
            return await self._install_node(connector, context, kwargs)
        elif operation == "run":
            return await self._run_node(connector, context, kwargs)
        elif operation == "sync_status":
            return await self._check_sync(connector, kwargs)
        elif operation == "stop":
            return await self._stop_node(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown operation: {operation}",
            )

    async def _install_node(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Install an Ethereum client."""
        client = params.get("client", "geth")  # geth, erigon, nethermind
        network = params.get("network", "mainnet")

        if client == "geth":
            # Install Geth
            commands = [
                "add-apt-repository -y ppa:ethereum/ethereum",
                "apt-get update",
                "apt-get install -y ethereum",
            ]
        elif client == "erigon":
            # Install Erigon (from binary)
            commands = [
                "wget https://github.com/ledgerwatch/erigon/releases/download/v2.55.0/erigon_2.55.0_linux_amd64.tar.gz",
                "tar -xzf erigon_2.55.0_linux_amd64.tar.gz -C /usr/local/bin/",
                "chmod +x /usr/local/bin/erigon",
            ]
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported client: {client}",
            )

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success:
                return ModuleResult(
                    changed=False,
                    success=False,
                    message=f"Failed to install {client}: {result.stderr}",
                )

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Installed {client} for {network}",
        )

    async def _run_node(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Run an Ethereum node."""
        client = params.get("client", "geth")
        node_type = params.get("type", "full")  # full, archive, light
        network = params.get("network", "mainnet")
        data_dir = params.get("data_dir", f"/var/lib/{client}")

        # Get config flags
        config = self.NODE_CONFIGS.get(client, {}).get(node_type, "")

        # Build systemd service
        service_content = f"""[Unit]
Description={client.capitalize()} {network} {node_type} node
After=network.target

[Service]
Type=simple
User=ethereum
ExecStart=/usr/local/bin/{client} {config} --datadir={data_dir} --{network}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

        # Write systemd service
        await connector.write_file(f"/etc/systemd/system/{client}.service", service_content)

        # Create ethereum user and data directory
        await connector.run_command("useradd -m -s /bin/bash ethereum", sudo=True)
        await connector.run_command(f"mkdir -p {data_dir}", sudo=True)
        await connector.run_command(f"chown -R ethereum:ethereum {data_dir}", sudo=True)

        # Start service
        await connector.run_command("systemctl daemon-reload", sudo=True)
        await connector.run_command(f"systemctl enable {client}", sudo=True)
        result = await connector.run_command(f"systemctl start {client}", sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Started {client} {node_type} node on {network}",
                details={"data_dir": data_dir, "network": network},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to start {client}: {result.stderr}",
            )

    async def _check_sync(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Check Ethereum node sync status."""
        client = params.get("client", "geth")

        # Query sync status via RPC
        result = await connector.run_command(
            'curl -X POST -H "Content-Type: application/json" '
            '--data \'{"jsonrpc":"2.0","method":"eth_syncing","params":[],"id":1}\' '
            'http://localhost:8545'
        )

        if result.success:
            import json
            response = json.loads(result.stdout)
            is_syncing = response.get("result", False)

            if is_syncing and isinstance(is_syncing, dict):
                current = int(is_syncing.get("currentBlock", "0"), 16)
                highest = int(is_syncing.get("highestBlock", "0"), 16)
                percent = (current / highest * 100) if highest > 0 else 0

                return ModuleResult(
                    changed=False,
                    success=True,
                    message=f"Syncing: {current}/{highest} ({percent:.2f}%)",
                    details={"current": current, "highest": highest, "percent": percent},
                )
            else:
                return ModuleResult(
                    changed=False,
                    success=True,
                    message="Node is fully synced!",
                    details={"synced": True},
                )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message="Cannot check sync status - node may be offline",
            )

    async def _stop_node(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Stop Ethereum node."""
        client = params.get("client", "geth")

        result = await connector.run_command(f"systemctl stop {client}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Stopped {client} node")
        else:
            return ModuleResult(changed=False, success=False, message=f"Failed to stop {client}")


# DSL Syntax for Ethereum:
# ethereum "mainnet_full":
#     client: "geth"
#     type: "full"
#     network: "mainnet"
#     data_dir: "/mnt/nvme/ethereum"
#
# task "Setup Ethereum Node" on eth_server:
#     ethereum install client="geth"
#     ethereum run "mainnet_full"
#     ethereum sync_status "mainnet_full"
