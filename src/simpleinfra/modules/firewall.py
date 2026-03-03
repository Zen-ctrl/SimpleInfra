"""Firewall / ensure module for SimpleInfra.

Handles ensure statements for ports, services, files, etc.
When ensuring a port is open, uses ufw/firewall-cmd based on OS.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class FirewallModule(Module):
    """Handles ensure statements (ports, services, files, directories)."""

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
            EnsureAction, PortCondition, ServiceCondition,
            FileExistsCondition,
        )

        if not isinstance(action, EnsureAction):
            return ModuleResult(changed=False, success=False, message=f"Expected EnsureAction")

        cond = action.condition

        if isinstance(cond, PortCondition):
            return await self._ensure_port(connector, context, cond)
        elif isinstance(cond, ServiceCondition):
            return await self._ensure_service(connector, cond)
        elif isinstance(cond, FileExistsCondition):
            return await self._ensure_file(connector, context, cond)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown ensure condition")

    async def _ensure_port(self, connector: "Connector", context: "ExecutionContext", cond: Any) -> ModuleResult:
        from ..ast.nodes import NumberValue
        port = cond.port.value if isinstance(cond.port, NumberValue) else cond.port
        os_family = context.facts.get("os_family", "debian")

        if cond.state == "open":
            if os_family == "debian":
                result = await connector.run_command(f"ufw allow {port}/tcp", sudo=True)
            elif os_family == "redhat":
                result = await connector.run_command(
                    f"firewall-cmd --add-port={port}/tcp --permanent && firewall-cmd --reload",
                    sudo=True,
                )
            else:
                result = await connector.run_command(f"iptables -A INPUT -p tcp --dport {port} -j ACCEPT", sudo=True)

            if result.success:
                return ModuleResult(changed=True, success=True, message=f"Opened port {port}")
            return ModuleResult(changed=False, success=False, message=f"Failed to open port {port}: {result.stderr}")

        elif cond.state == "closed":
            if os_family == "debian":
                result = await connector.run_command(f"ufw deny {port}/tcp", sudo=True)
            elif os_family == "redhat":
                result = await connector.run_command(
                    f"firewall-cmd --remove-port={port}/tcp --permanent && firewall-cmd --reload",
                    sudo=True,
                )
            else:
                result = await connector.run_command(f"iptables -A INPUT -p tcp --dport {port} -j DROP", sudo=True)

            if result.success:
                return ModuleResult(changed=True, success=True, message=f"Closed port {port}")
            return ModuleResult(changed=False, success=False, message=f"Failed to close port {port}: {result.stderr}")

        return ModuleResult(changed=False, success=False, message=f"Unknown port state: {cond.state}")

    async def _ensure_service(self, connector: "Connector", cond: Any) -> ModuleResult:
        result = await connector.run_command(f"systemctl is-active {cond.service_name}")
        is_running = result.success and result.stdout.strip() == "active"

        if cond.state == "running" and not is_running:
            result = await connector.run_command(f"systemctl start {cond.service_name}", sudo=True)
            if result.success:
                return ModuleResult(changed=True, success=True, message=f"Started service {cond.service_name}")
            return ModuleResult(changed=False, success=False, message=f"Failed to start {cond.service_name}")
        elif cond.state == "stopped" and is_running:
            result = await connector.run_command(f"systemctl stop {cond.service_name}", sudo=True)
            if result.success:
                return ModuleResult(changed=True, success=True, message=f"Stopped service {cond.service_name}")
            return ModuleResult(changed=False, success=False, message=f"Failed to stop {cond.service_name}")

        return ModuleResult(changed=False, success=True, message=f"Service {cond.service_name} already {cond.state}")

    async def _ensure_file(self, connector: "Connector", context: "ExecutionContext", cond: Any) -> ModuleResult:
        path = context.resolver.resolve(cond.path)
        exists = await connector.file_exists(path)
        if exists:
            return ModuleResult(changed=False, success=True, message=f"File exists: {path}")
        return ModuleResult(changed=False, success=False, message=f"File does not exist: {path}")
