"""Planner for SimpleInfra dry-run mode.

The planner shows what would be executed without actually running it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ast.nodes import Document, TaskDecl


class ExecutionPlanner:
    """Generates an execution plan without running anything."""

    def __init__(self, document: "Document") -> None:
        self.document = document

    def plan_task(self, task_name: str) -> dict:
        """Generate a plan for executing a task."""
        task = self._find_task(task_name)
        if not task:
            return {"error": f"Task '{task_name}' not found"}

        return {
            "task": task.name,
            "target": task.target,
            "actions": [
                {
                    "type": type(action).__name__,
                    "description": self._describe_action(action),
                }
                for action in task.actions
            ],
        }

    def _find_task(self, name: str) -> "TaskDecl | None":
        for task in self.document.tasks:
            if task.name == name:
                return task
        return None

    def _describe_action(self, action: object) -> str:
        """Generate a human-readable description of an action."""
        from ..ast.nodes import (
            InstallAction, RemoveAction, CopyAction,
            RunAction, ServiceActionNode,
        )

        if isinstance(action, InstallAction):
            return f"Install packages: {', '.join(action.packages)}"
        elif isinstance(action, RemoveAction):
            return f"Remove packages: {', '.join(action.packages)}"
        elif isinstance(action, CopyAction):
            return f"Copy {action.source} to {action.destination}"
        elif isinstance(action, RunAction):
            return f"Run command: {action.command}"
        elif isinstance(action, ServiceActionNode):
            return f"{action.action.name} service {action.service_name}"
        else:
            return str(action)
