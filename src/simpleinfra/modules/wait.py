"""Wait module for SimpleInfra.

Handles waiting for ports to become available, URLs to respond,
or just sleeping for a number of seconds.
"""

from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class WaitModule(Module):
    """Handles wait operations."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action")
        if action is None:
            return ModuleResult(changed=False, success=False, message="No action provided")

        from ..ast.nodes import WaitAction

        if not isinstance(action, WaitAction):
            return ModuleResult(changed=False, success=False, message=f"Expected WaitAction")

        if action.target_type == "port":
            return await self._wait_port(connector, context, action.target_value)
        elif action.target_type == "url":
            return await self._wait_url(connector, context, str(action.target_value))
        elif action.target_type == "seconds":
            return await self._wait_seconds(int(action.target_value))
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown wait target: {action.target_type}")

    async def _wait_port(self, connector: "Connector", context: "ExecutionContext", port: Any) -> ModuleResult:
        from ..ast.nodes import NumberValue
        port_num = port.value if isinstance(port, NumberValue) else port

        max_attempts = 30
        for attempt in range(max_attempts):
            result = await connector.run_command(f"ss -tlnp | grep :{port_num}")
            if result.success and str(port_num) in result.stdout:
                return ModuleResult(
                    changed=False,
                    success=True,
                    message=f"Port {port_num} is ready (waited {attempt}s)",
                )
            await asyncio.sleep(1)

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Timeout waiting for port {port_num} (waited {max_attempts}s)",
        )

    async def _wait_url(self, connector: "Connector", context: "ExecutionContext", url: str) -> ModuleResult:
        url = context.resolver.resolve(url)
        max_attempts = 30

        for attempt in range(max_attempts):
            result = await connector.run_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url}")
            if result.success:
                status = int(result.stdout.strip())
                if 200 <= status < 400:
                    return ModuleResult(
                        changed=False,
                        success=True,
                        message=f"URL {url} is ready (status {status}, waited {attempt}s)",
                    )
            await asyncio.sleep(1)

        return ModuleResult(
            changed=False,
            success=False,
            message=f"Timeout waiting for URL {url} (waited {max_attempts}s)",
        )

    async def _wait_seconds(self, seconds: int) -> ModuleResult:
        await asyncio.sleep(seconds)
        return ModuleResult(
            changed=False,
            success=True,
            message=f"Waited {seconds} seconds",
        )
