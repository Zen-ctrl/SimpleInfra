"""Main task executor for SimpleInfra.

The executor walks the AST and dispatches actions to their modules.
It handles control flow (if/unless/for), tracks state, and manages
connectors.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..ast.nodes import (
    Document,
    TaskDecl,
    IfBlock,
    UnlessBlock,
    ForBlock,
    SimpleCondition,
    FileExistsCheck,
    CommandSucceedsCheck,
)
from ..connectors.local import LocalConnector
from ..connectors.ssh import SSHConnector
from ..modules.registry import ModuleRegistry
from ..variables.secrets import load_secrets
from .context import ExecutionContext

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..ast.nodes import TaskAction, ConditionExpr


class TaskExecutor:
    """Main execution engine that runs tasks from a parsed document."""

    def __init__(
        self,
        document: Document,
        registry: ModuleRegistry,
        project_dir: Path | None = None,
        dry_run: bool = False,
    ) -> None:
        self.document = document
        self.registry = registry
        self.project_dir = project_dir or Path.cwd()
        self.dry_run = dry_run
        self.results: list[dict[str, Any]] = []

    async def run_task(self, task_name: str) -> dict[str, Any]:
        """Execute a single named task."""
        task = self._find_task(task_name)
        if not task:
            return {"success": False, "message": f"Task '{task_name}' not found"}

        # Load secrets
        secrets = load_secrets(self.document.secrets, self.project_dir)

        # Create execution context
        context = ExecutionContext.from_document(self.document, secrets)

        # Resolve target(s)
        connectors = await self._get_connectors(task.target)

        task_results = []
        for target_name, connector in connectors:
            result = await self._execute_task_on_target(task, target_name, connector, context)
            task_results.append(result)

        return {
            "task_name": task.name,
            "results": task_results,
            "success": all(r["success"] for r in task_results),
        }

    async def _execute_task_on_target(
        self,
        task: TaskDecl,
        target_name: str,
        connector: "Connector",
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a task on a single target."""
        action_results = []

        async with connector:
            # Gather facts
            if target_name == "local":
                context.gather_facts_local()
            else:
                await context.gather_facts(connector)

            # Execute each action in the task
            for action in task.actions:
                result = await self._execute_action(action, connector, context)
                action_results.append(result)

                # Stop on failure (unless it's a check)
                if not result["success"] and not self.dry_run:
                    from ..ast.nodes import CheckAction
                    if not isinstance(action, CheckAction):
                        break

        return {
            "target": target_name,
            "success": all(r["success"] for r in action_results),
            "actions": action_results,
        }

    async def _execute_action(
        self,
        action: "TaskAction",
        connector: "Connector",
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a single action."""
        # Handle control flow
        if isinstance(action, IfBlock):
            return await self._execute_if(action, connector, context)
        elif isinstance(action, UnlessBlock):
            return await self._execute_unless(action, connector, context)
        elif isinstance(action, ForBlock):
            return await self._execute_for(action, connector, context)

        # Normal module execution
        if self.dry_run:
            return {
                "action": type(action).__name__,
                "dry_run": True,
                "success": True,
                "changed": False,
                "message": f"[DRY RUN] Would execute {type(action).__name__}",
            }

        module = self.registry.get(type(action))
        result = await module.execute(connector, context, action=action)

        return {
            "action": type(action).__name__,
            "success": result.success,
            "changed": result.changed,
            "message": result.message,
            "details": result.details,
        }

    async def _execute_if(
        self,
        block: IfBlock,
        connector: "Connector",
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute an if block."""
        condition_met = await self._evaluate_condition(block.condition, connector, context)

        if condition_met:
            results = []
            for action in block.body:
                result = await self._execute_action(action, connector, context)
                results.append(result)
            return {
                "action": "IfBlock",
                "success": all(r["success"] for r in results),
                "changed": any(r.get("changed", False) for r in results),
                "message": f"If block executed ({len(results)} actions)",
                "details": {"results": results},
            }
        else:
            return {
                "action": "IfBlock",
                "success": True,
                "changed": False,
                "message": "If condition not met, skipped",
            }

    async def _execute_unless(
        self,
        block: UnlessBlock,
        connector: "Connector",
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute an unless block."""
        condition_met = await self._evaluate_condition(block.condition, connector, context)

        if not condition_met:
            results = []
            for action in block.body:
                result = await self._execute_action(action, connector, context)
                results.append(result)
            return {
                "action": "UnlessBlock",
                "success": all(r["success"] for r in results),
                "changed": any(r.get("changed", False) for r in results),
                "message": f"Unless block executed ({len(results)} actions)",
                "details": {"results": results},
            }
        else:
            return {
                "action": "UnlessBlock",
                "success": True,
                "changed": False,
                "message": "Unless condition met, skipped",
            }

    async def _execute_for(
        self,
        block: ForBlock,
        connector: "Connector",
        context: ExecutionContext,
    ) -> dict[str, Any]:
        """Execute a for loop."""
        # Get the iterable
        iterable = context.variables.get(block.iterable, [])
        if not isinstance(iterable, (list, tuple)):
            return {
                "action": "ForBlock",
                "success": False,
                "changed": False,
                "message": f"Cannot iterate over {block.iterable} (not a list)",
            }

        all_results = []
        for item in iterable:
            context.resolver.set_loop_variable(block.variable, item)
            for action in block.body:
                result = await self._execute_action(action, connector, context)
                all_results.append(result)
            context.resolver.clear_loop_variable(block.variable)

        return {
            "action": "ForBlock",
            "success": all(r["success"] for r in all_results),
            "changed": any(r.get("changed", False) for r in all_results),
            "message": f"For loop executed ({len(all_results)} total actions)",
            "details": {"results": all_results},
        }

    async def _evaluate_condition(
        self,
        condition: "ConditionExpr",
        connector: "Connector",
        context: ExecutionContext,
    ) -> bool:
        """Evaluate a condition expression."""
        if isinstance(condition, SimpleCondition):
            left_val = context.facts.get(condition.left, context.variables.get(condition.left))
            right_val = self._get_value(condition.right, context)

            if condition.operator == "is":
                return str(left_val) == str(right_val)
            elif condition.operator == "is_not":
                return str(left_val) != str(right_val)
            elif condition.operator == "contains":
                return str(right_val) in str(left_val)
            elif condition.operator == ">":
                try:
                    return float(left_val) > float(right_val)
                except (ValueError, TypeError):
                    return False
            elif condition.operator == "<":
                try:
                    return float(left_val) < float(right_val)
                except (ValueError, TypeError):
                    return False

        elif isinstance(condition, FileExistsCheck):
            path = context.resolver.resolve(condition.path)
            return await connector.file_exists(path)

        elif isinstance(condition, CommandSucceedsCheck):
            command = context.resolver.resolve(condition.command)
            result = await connector.run_command(command)
            return result.success

        return False

    def _get_value(self, value: Any, context: ExecutionContext) -> str | int | bool:
        """Extract the primitive value from an AST value node."""
        from ..ast.nodes import StringValue, NumberValue, BooleanValue, VariableRef

        if isinstance(value, StringValue):
            return value.value
        elif isinstance(value, NumberValue):
            return value.value
        elif isinstance(value, BooleanValue):
            return value.value
        elif isinstance(value, VariableRef):
            return context.variables.get(value.name, "")
        return str(value)

    def _find_task(self, name: str) -> TaskDecl | None:
        """Find a task by name."""
        for task in self.document.tasks:
            if task.name == name:
                return task
        return None

    async def _get_connectors(self, target: str) -> list[tuple[str, "Connector"]]:
        """Get connector(s) for a target."""
        if target == "local":
            return [("local", LocalConnector())]

        # Find server
        for server in self.document.servers:
            if server.name == target:
                connector = SSHConnector(
                    host=server.host,
                    user=server.user,
                    port=server.port,
                    key_path=server.key,
                    password=self._get_secret(server.password_secret) if server.password_secret else None,
                )
                return [(server.name, connector)]

        # Find group
        for group in self.document.groups:
            if group.name == target:
                connectors = []
                for member in group.members:
                    if member.kind == "server":
                        for server in self.document.servers:
                            if server.name == member.name:
                                connector = SSHConnector(
                                    host=server.host,
                                    user=server.user,
                                    port=server.port,
                                    key_path=server.key,
                                    password=self._get_secret(server.password_secret) if server.password_secret else None,
                                )
                                connectors.append((server.name, connector))
                return connectors

        return []

    def _get_secret(self, secret_name: str) -> str | None:
        """Get a secret value by name."""
        secrets = load_secrets(self.document.secrets, self.project_dir)
        return secrets.get(secret_name)
