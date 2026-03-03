"""Check module for SimpleInfra.

Handles verification checks: service running, port open,
URL returns status code, file exists/contains, disk space.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class CheckModule(Module):
    """Handles check assertions."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action")
        if action is None:
            return ModuleResult(changed=False, success=False, message="No action provided")

        from ..ast.nodes import (
            CheckAction, PortCondition, ServiceCondition,
            UrlCondition, FileExistsCondition, FileContainsCondition,
            DiskCondition, CommandCondition,
        )

        if not isinstance(action, CheckAction):
            return ModuleResult(changed=False, success=False, message=f"Expected CheckAction")

        cond = action.condition

        if isinstance(cond, ServiceCondition):
            return await self._check_service(connector, cond)
        elif isinstance(cond, PortCondition):
            return await self._check_port(connector, context, cond)
        elif isinstance(cond, UrlCondition):
            return await self._check_url(connector, context, cond)
        elif isinstance(cond, FileExistsCondition):
            return await self._check_file_exists(connector, context, cond)
        elif isinstance(cond, FileContainsCondition):
            return await self._check_file_contains(connector, context, cond)
        elif isinstance(cond, DiskCondition):
            return await self._check_disk(connector, cond)
        elif isinstance(cond, CommandCondition):
            return await self._check_command(connector, context, cond)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown condition type")

    async def _check_service(self, connector: "Connector", cond: Any) -> ModuleResult:
        result = await connector.run_command(f"systemctl is-active {cond.service_name}")
        is_running = result.success and result.stdout.strip() == "active"

        if cond.state == "running" and is_running:
            return ModuleResult(changed=False, success=True, message=f"Service {cond.service_name} is running")
        elif cond.state == "stopped" and not is_running:
            return ModuleResult(changed=False, success=True, message=f"Service {cond.service_name} is stopped")
        else:
            actual = "running" if is_running else "stopped"
            return ModuleResult(
                changed=False, success=False,
                message=f"Service {cond.service_name} is {actual}, expected {cond.state}",
            )

    async def _check_port(self, connector: "Connector", context: "ExecutionContext", cond: Any) -> ModuleResult:
        from ..ast.nodes import NumberValue
        port = cond.port.value if isinstance(cond.port, NumberValue) else cond.port
        result = await connector.run_command(f"ss -tlnp | grep :{port}")
        is_open = result.success and str(port) in result.stdout

        if cond.state == "open" and is_open:
            return ModuleResult(changed=False, success=True, message=f"Port {port} is open")
        elif cond.state == "closed" and not is_open:
            return ModuleResult(changed=False, success=True, message=f"Port {port} is closed")
        else:
            actual = "open" if is_open else "closed"
            return ModuleResult(changed=False, success=False, message=f"Port {port} is {actual}, expected {cond.state}")

    async def _check_url(self, connector: "Connector", context: "ExecutionContext", cond: Any) -> ModuleResult:
        url = context.resolver.resolve(cond.url)
        result = await connector.run_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url}")
        if result.success:
            status_code = int(result.stdout.strip())
            if status_code == cond.expected_status:
                return ModuleResult(changed=False, success=True, message=f"URL {url} returns {status_code}")
            else:
                return ModuleResult(
                    changed=False, success=False,
                    message=f"URL {url} returns {status_code}, expected {cond.expected_status}",
                )
        return ModuleResult(changed=False, success=False, message=f"Cannot reach URL {url}")

    async def _check_file_exists(self, connector: "Connector", context: "ExecutionContext", cond: Any) -> ModuleResult:
        path = context.resolver.resolve(cond.path)
        exists = await connector.file_exists(path)
        if exists:
            return ModuleResult(changed=False, success=True, message=f"File exists: {path}")
        return ModuleResult(changed=False, success=False, message=f"File does not exist: {path}")

    async def _check_file_contains(self, connector: "Connector", context: "ExecutionContext", cond: Any) -> ModuleResult:
        path = context.resolver.resolve(cond.path)
        content = context.resolver.resolve(cond.content)
        try:
            file_content = await connector.read_file(path)
            if content in file_content:
                return ModuleResult(changed=False, success=True, message=f"File {path} contains expected content")
            return ModuleResult(changed=False, success=False, message=f"File {path} does not contain expected content")
        except Exception:
            return ModuleResult(changed=False, success=False, message=f"Cannot read file: {path}")

    async def _check_disk(self, connector: "Connector", cond: Any) -> ModuleResult:
        result = await connector.run_command(f"df -BG {cond.path} | tail -1")
        if result.success:
            parts = result.stdout.split()
            if len(parts) >= 4:
                available = parts[3].rstrip("G")
                threshold = cond.threshold.rstrip("GBMK")
                try:
                    if int(available) >= int(threshold):
                        return ModuleResult(
                            changed=False, success=True,
                            message=f"Disk {cond.path} has {available}GB free (>= {cond.threshold})",
                        )
                    else:
                        return ModuleResult(
                            changed=False, success=False,
                            message=f"Disk {cond.path} has only {available}GB free (need {cond.threshold})",
                        )
                except ValueError:
                    pass
        return ModuleResult(changed=False, success=False, message=f"Cannot check disk space for {cond.path}")

    async def _check_command(self, connector: "Connector", context: "ExecutionContext", cond: Any) -> ModuleResult:
        command = context.resolver.resolve(cond.command)
        result = await connector.run_command(command)
        if result.exit_code == cond.expected_code:
            return ModuleResult(
                changed=False, success=True,
                message=f"Command returned expected exit code {cond.expected_code}",
            )
        return ModuleResult(
            changed=False, success=False,
            message=f"Command returned {result.exit_code}, expected {cond.expected_code}",
        )
