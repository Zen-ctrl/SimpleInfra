"""Smart contract deployment module for SimpleInfra.

Deploy and verify smart contracts using Foundry or Hardhat.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class SmartContractModule(Module):
    """Deploy and manage smart contracts."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        operation = kwargs.get("operation", "deploy")
        framework = kwargs.get("framework", "foundry")  # foundry or hardhat

        if operation == "install":
            return await self._install_framework(connector, framework)
        elif operation == "compile":
            return await self._compile_contracts(connector, context, kwargs)
        elif operation == "deploy":
            return await self._deploy_contract(connector, context, kwargs)
        elif operation == "verify":
            return await self._verify_contract(connector, context, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown operation: {operation}",
            )

    async def _install_framework(
        self,
        connector: "Connector",
        framework: str,
    ) -> ModuleResult:
        """Install Foundry or Hardhat."""
        if framework == "foundry":
            # Install Foundry
            result = await connector.run_command(
                "curl -L https://foundry.paradigm.xyz | bash && "
                "~/.foundry/bin/foundryup"
            )
            if result.success:
                return ModuleResult(
                    changed=True,
                    success=True,
                    message="Installed Foundry (forge, cast, anvil)",
                )
        elif framework == "hardhat":
            # Install Node.js and Hardhat
            commands = [
                "curl -fsSL https://deb.nodesource.com/setup_18.x | bash -",
                "apt-get install -y nodejs",
                "npm install -g hardhat",
            ]
            for cmd in commands:
                result = await connector.run_command(cmd, sudo=True)
                if not result.success:
                    return ModuleResult(
                        changed=False,
                        success=False,
                        message=f"Failed to install Hardhat: {result.stderr}",
                    )
            return ModuleResult(changed=True, success=True, message="Installed Hardhat")

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Unknown framework: {framework}",
        )

    async def _compile_contracts(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Compile smart contracts."""
        project_path = context.resolver.resolve(params.get("path", "."))
        framework = params.get("framework", "foundry")

        if framework == "foundry":
            cmd = f"cd {project_path} && forge build"
        else:  # hardhat
            cmd = f"cd {project_path} && npx hardhat compile"

        result = await connector.run_command(cmd)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message="Contracts compiled successfully",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Compilation failed: {result.stderr}",
            )

    async def _deploy_contract(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Deploy a smart contract."""
        contract = params.get("contract", "")
        rpc_url = context.resolver.resolve(params.get("rpc_url", "http://localhost:8545"))
        private_key = context.resolver.resolve(params.get("private_key", ""))
        constructor_args = params.get("args", "")
        framework = params.get("framework", "foundry")

        if framework == "foundry":
            cmd = (
                f"forge create {contract} "
                f"--rpc-url {rpc_url} "
                f"--private-key {private_key}"
            )
            if constructor_args:
                cmd += f" --constructor-args {constructor_args}"

        else:  # hardhat
            # Create deployment script
            deploy_script = f"""
const {{ ethers }} = require("hardhat");

async function main() {{
    const Contract = await ethers.getContractFactory("{contract}");
    const contract = await Contract.deploy({constructor_args});
    await contract.deployed();
    console.log("Contract deployed to:", contract.address);
}}

main().catch((error) => {{
    console.error(error);
    process.exitCode = 1;
}});
"""
            await connector.write_file("/tmp/deploy.js", deploy_script)
            cmd = f"npx hardhat run /tmp/deploy.js --network mainnet"

        result = await connector.run_command(cmd)

        if result.success:
            # Extract contract address from output
            import re
            address_match = re.search(r"0x[a-fA-F0-9]{40}", result.stdout)
            address = address_match.group(0) if address_match else "unknown"

            return ModuleResult(
                changed=True,
                success=True,
                message=f"Deployed {contract} to {address}",
                details={"address": address, "stdout": result.stdout},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Deployment failed: {result.stderr}",
            )

    async def _verify_contract(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Verify contract on Etherscan."""
        address = params.get("address", "")
        contract = params.get("contract", "")
        etherscan_key = context.resolver.resolve(params.get("etherscan_key", ""))

        cmd = (
            f"forge verify-contract {address} {contract} "
            f"--etherscan-api-key {etherscan_key}"
        )

        result = await connector.run_command(cmd)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Verified {contract} at {address}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Verification failed: {result.stderr}",
            )


# DSL Syntax:
# secret private_key from vault "eth/deployer/key"
# secret etherscan_key from env "ETHERSCAN_API_KEY"
#
# task "Deploy Smart Contract" on local:
#     contract install framework="foundry"
#     contract compile path="./contracts" framework="foundry"
#
#     contract deploy:
#         contract: "src/MyToken.sol:MyToken"
#         rpc_url: "https://mainnet.infura.io/v3/..."
#         private_key: secret private_key
#         args: "1000000 'My Token' 'MTK'"
#
#     contract verify:
#         address: "0x..."
#         contract: "MyToken"
#         etherscan_key: secret etherscan_key
