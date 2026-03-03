"""Service module for SimpleInfra.

Handles start/stop/restart/enable/disable of system services
via systemctl.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class ServiceModule(Module):
    """Handles service management operations."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action")
        if action is None:
            return ModuleResult(changed=False, success=False, message="No action provided")

        from ..ast.nodes import ServiceActionNode, ServiceAction

        if not isinstance(action, ServiceActionNode):
            return ModuleResult(changed=False, success=False, message=f"Expected ServiceActionNode, got {type(action)}")

        service = action.service_name
        svc_action = action.action

        if svc_action == ServiceAction.START:
            return await self._start(connector, service)
        elif svc_action == ServiceAction.STOP:
            return await self._stop(connector, service)
        elif svc_action == ServiceAction.RESTART:
            return await self._restart(connector, service)
        elif svc_action == ServiceAction.ENABLE:
            return await self._enable(connector, service)
        elif svc_action == ServiceAction.DISABLE:
            return await self._disable(connector, service)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown service action: {svc_action}")

    async def _is_active(self, connector: "Connector", service: str) -> bool:
        result = await connector.run_command(f"systemctl is-active {service}")
        return result.success and result.stdout.strip() == "active"

    async def _is_enabled(self, connector: "Connector", service: str) -> bool:
        result = await connector.run_command(f"systemctl is-enabled {service}")
        return result.success and result.stdout.strip() == "enabled"

    async def _start(self, connector: "Connector", service: str) -> ModuleResult:
        if await self._is_active(connector, service):
            return ModuleResult(changed=False, success=True, message=f"Service {service} already running")

        result = await connector.run_command(f"systemctl start {service}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Started service {service}")
        return ModuleResult(changed=False, success=False, message=f"Failed to start {service}: {result.stderr}")

    async def _stop(self, connector: "Connector", service: str) -> ModuleResult:
        if not await self._is_active(connector, service):
            return ModuleResult(changed=False, success=True, message=f"Service {service} already stopped")

        result = await connector.run_command(f"systemctl stop {service}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Stopped service {service}")
        return ModuleResult(changed=False, success=False, message=f"Failed to stop {service}: {result.stderr}")

    async def _restart(self, connector: "Connector", service: str) -> ModuleResult:
        result = await connector.run_command(f"systemctl restart {service}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Restarted service {service}")
        return ModuleResult(changed=False, success=False, message=f"Failed to restart {service}: {result.stderr}")

    async def _enable(self, connector: "Connector", service: str) -> ModuleResult:
        if await self._is_enabled(connector, service):
            return ModuleResult(changed=False, success=True, message=f"Service {service} already enabled")

        result = await connector.run_command(f"systemctl enable {service}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Enabled service {service}")
        return ModuleResult(changed=False, success=False, message=f"Failed to enable {service}: {result.stderr}")

    async def _disable(self, connector: "Connector", service: str) -> ModuleResult:
        if not await self._is_enabled(connector, service):
            return ModuleResult(changed=False, success=True, message=f"Service {service} already disabled")

        result = await connector.run_command(f"systemctl disable {service}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Disabled service {service}")
        return ModuleResult(changed=False, success=False, message=f"Failed to disable {service}: {result.stderr}")
