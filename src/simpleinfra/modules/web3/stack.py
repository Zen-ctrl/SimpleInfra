"""Web3 Stack module for SimpleInfra.

One-command deployment of complete Web3 infrastructure stacks.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class Web3StackModule(Module):
    """Deploy complete Web3 infrastructure stacks with one command."""

    # Predefined stacks
    STACKS = {
        "ethereum_full": {
            "description": "Full Ethereum node + IPFS + monitoring",
            "components": ["geth", "ipfs", "prometheus", "grafana"],
        },
        "polygon_validator": {
            "description": "Polygon validator node setup",
            "components": ["heimdall", "bor", "prometheus"],
        },
        "dapp_backend": {
            "description": "Complete dApp backend infrastructure",
            "components": ["geth", "ipfs", "graph_node", "postgres", "nginx"],
        },
        "nft_platform": {
            "description": "NFT platform infrastructure",
            "components": ["geth", "ipfs", "postgres", "redis", "api"],
        },
    }

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        stack_name = kwargs.get("stack", "ethereum_full")
        operation = kwargs.get("operation", "deploy")

        if operation == "deploy":
            return await self._deploy_stack(connector, context, stack_name)
        elif operation == "status":
            return await self._check_stack_status(connector, stack_name)
        elif operation == "stop":
            return await self._stop_stack(connector, stack_name)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown operation: {operation}",
            )

    async def _deploy_stack(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        stack_name: str,
    ) -> ModuleResult:
        """Deploy a complete Web3 stack."""
        if stack_name not in self.STACKS:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown stack: {stack_name}. Available: {list(self.STACKS.keys())}",
            )

        stack = self.STACKS[stack_name]
        results = []

        # Deploy each component
        for component in stack["components"]:
            result = await self._deploy_component(connector, context, component)
            results.append((component, result))

        # Check if all succeeded
        all_success = all(r[1].success for r in results)
        failed = [r[0] for r in results if not r[1].success]

        if all_success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Deployed {stack['description']}",
                details={"components": stack["components"]},
            )
        else:
            return ModuleResult(
                changed=True,
                success=False,
                message=f"Partial deployment. Failed: {', '.join(failed)}",
                details={"failed": failed},
            )

    async def _deploy_component(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        component: str,
    ) -> ModuleResult:
        """Deploy a single infrastructure component."""
        if component == "geth":
            return await self._deploy_geth(connector)
        elif component == "ipfs":
            return await self._deploy_ipfs(connector)
        elif component == "prometheus":
            return await self._deploy_prometheus(connector)
        elif component == "grafana":
            return await self._deploy_grafana(connector)
        elif component == "graph_node":
            return await self._deploy_graph_node(connector)
        elif component == "postgres":
            return await self._deploy_postgres(connector)
        elif component == "nginx":
            return await self._deploy_nginx(connector)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown component: {component}",
            )

    async def _deploy_geth(self, connector: "Connector") -> ModuleResult:
        """Deploy Geth node."""
        commands = [
            "add-apt-repository -y ppa:ethereum/ethereum",
            "apt-get update",
            "apt-get install -y ethereum",
            "systemctl enable geth",
            "systemctl start geth",
        ]

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success:
                return ModuleResult(changed=False, success=False, message="Geth deployment failed")

        return ModuleResult(changed=True, success=True, message="Deployed Geth")

    async def _deploy_ipfs(self, connector: "Connector") -> ModuleResult:
        """Deploy IPFS node."""
        # Download and install IPFS
        commands = [
            "wget https://dist.ipfs.tech/kubo/v0.24.0/kubo_v0.24.0_linux-amd64.tar.gz -O /tmp/ipfs.tar.gz",
            "tar -xvzf /tmp/ipfs.tar.gz -C /tmp",
            "cd /tmp/kubo && bash install.sh",
            "useradd -m ipfs || true",
            "su - ipfs -c 'ipfs init --profile=server'",
        ]

        for cmd in commands:
            await connector.run_command(cmd, sudo=True)

        return ModuleResult(changed=True, success=True, message="Deployed IPFS")

    async def _deploy_prometheus(self, connector: "Connector") -> ModuleResult:
        """Deploy Prometheus monitoring."""
        result = await connector.run_command("apt-get install -y prometheus", sudo=True)
        await connector.run_command("systemctl enable prometheus", sudo=True)
        await connector.run_command("systemctl start prometheus", sudo=True)

        return ModuleResult(
            changed=True,
            success=result.success,
            message="Deployed Prometheus" if result.success else "Prometheus deployment failed",
        )

    async def _deploy_grafana(self, connector: "Connector") -> ModuleResult:
        """Deploy Grafana dashboards."""
        commands = [
            "apt-get install -y apt-transport-https software-properties-common",
            "wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -",
            'echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list',
            "apt-get update",
            "apt-get install -y grafana",
            "systemctl enable grafana-server",
            "systemctl start grafana-server",
        ]

        for cmd in commands:
            await connector.run_command(cmd, sudo=True)

        return ModuleResult(changed=True, success=True, message="Deployed Grafana")

    async def _deploy_graph_node(self, connector: "Connector") -> ModuleResult:
        """Deploy The Graph indexing node."""
        # Install Graph Node via Docker
        docker_compose = """version: '3'
services:
  graph-node:
    image: graphprotocol/graph-node:latest
    ports:
      - '8000:8000'
      - '8001:8001'
      - '8020:8020'
      - '8030:8030'
      - '8040:8040'
    environment:
      postgres_host: postgres
      postgres_user: graph-node
      postgres_pass: let-me-in
      postgres_db: graph-node
      ipfs: 'ipfs:5001'
      ethereum: 'mainnet:http://geth:8545'
    depends_on:
      - postgres
      - ipfs
"""

        await connector.write_file("/opt/graph-node/docker-compose.yml", docker_compose)
        result = await connector.run_command(
            "cd /opt/graph-node && docker-compose up -d",
            sudo=True,
        )

        return ModuleResult(
            changed=True,
            success=result.success,
            message="Deployed Graph Node",
        )

    async def _deploy_postgres(self, connector: "Connector") -> ModuleResult:
        """Deploy PostgreSQL."""
        result = await connector.run_command("apt-get install -y postgresql", sudo=True)
        return ModuleResult(changed=True, success=result.success, message="Deployed PostgreSQL")

    async def _deploy_nginx(self, connector: "Connector") -> ModuleResult:
        """Deploy Nginx reverse proxy."""
        result = await connector.run_command("apt-get install -y nginx", sudo=True)
        return ModuleResult(changed=True, success=result.success, message="Deployed Nginx")

    async def _check_stack_status(
        self,
        connector: "Connector",
        stack_name: str,
    ) -> ModuleResult:
        """Check status of deployed stack."""
        if stack_name not in self.STACKS:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown stack: {stack_name}",
            )

        stack = self.STACKS[stack_name]
        status_info = {}

        # Check each component's systemd service
        for component in stack["components"]:
            result = await connector.run_command(f"systemctl is-active {component}")
            status_info[component] = "running" if result.success else "stopped"

        all_running = all(s == "running" for s in status_info.values())

        return ModuleResult(
            changed=False,
            success=all_running,
            message=f"Stack status: {'healthy' if all_running else 'degraded'}",
            details=status_info,
        )

    async def _stop_stack(self, connector: "Connector", stack_name: str) -> ModuleResult:
        """Stop all components of a stack."""
        if stack_name not in self.STACKS:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown stack: {stack_name}",
            )

        stack = self.STACKS[stack_name]

        for component in stack["components"]:
            await connector.run_command(f"systemctl stop {component}", sudo=True)

        return ModuleResult(
            changed=True,
            success=True,
            message=f"Stopped {stack_name} stack",
        )


# DSL Syntax - Super simple Web3 deployment:
#
# task "Deploy Ethereum Infrastructure" on eth_server:
#     web3_stack deploy "ethereum_full"
#
# task "Deploy dApp Backend" on app_server:
#     web3_stack deploy "dapp_backend"
#
# task "Check Stack Health" on eth_server:
#     web3_stack status "ethereum_full"
