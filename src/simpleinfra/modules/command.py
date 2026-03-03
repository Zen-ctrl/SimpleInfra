"""Command module for SimpleInfra.

Handles executing arbitrary shell commands via the `run` action.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class CommandModule(Module):
    """Handles running arbitrary shell commands."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action")
        if action is None:
            return ModuleResult(changed=False, success=False, message="No action provided")

        from ..ast.nodes import RunAction

        if not isinstance(action, RunAction):
            return ModuleResult(changed=False, success=False, message=f"Expected RunAction, got {type(action)}")

        command = context.resolver.resolve(action.command)

        if not command:
            return ModuleResult(changed=False, success=True, message="Empty command, skipped")

        result = await connector.run_command(command)

        if result.success:
            return ModuleResult(
                changed=True,  # Commands always count as changed
                success=True,
                message=f"Executed: {command}",
                details={
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                    "exit_code": result.exit_code,
                },
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Command failed (exit {result.exit_code}): {command}",
                details={
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                    "exit_code": result.exit_code,
                },
            )
