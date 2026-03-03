"""Python API for programmatic use of SimpleInfra.

Allows using SimpleInfra directly from Python code without .si files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ast.nodes import (
    Document,
    InstallAction,
    RunAction,
    ServerDecl,
    SetVariable,
    StringValue,
    TaskDecl,
)
from ..dsl.parser import SimpleInfraParser
from ..engine.executor import TaskExecutor
from ..modules.registry import create_default_registry


class SimpleInfraClient:
    """Programmatic client for SimpleInfra.

    Example usage:
        client = SimpleInfraClient()

        # Define infrastructure
        client.add_server("web", host="192.168.1.10", user="root")
        client.set_variable("app_name", "myapp")

        # Create task programmatically
        task = client.create_task("deploy", target="web")
        task.install("nginx", "python3")
        task.run("systemctl start nginx")

        # Execute
        result = await client.execute_task("deploy")
    """

    def __init__(self):
        self.servers: list[ServerDecl] = []
        self.variables: list[SetVariable] = []
        self.tasks: list[TaskDecl] = []
        self.registry = create_default_registry()

    def add_server(
        self,
        name: str,
        host: str,
        user: str = "root",
        key: str | None = None,
        port: int = 22,
    ) -> ServerDecl:
        """Add a server definition."""
        server = ServerDecl(name=name, host=host, user=user, key=key, port=port)
        self.servers.append(server)
        return server

    def set_variable(self, name: str, value: str | int | bool) -> None:
        """Set a variable."""
        if isinstance(value, str):
            ast_value = StringValue(value)
        else:
            from ..ast.nodes import NumberValue, BooleanValue
            ast_value = NumberValue(value) if isinstance(value, int) else BooleanValue(value)

        self.variables.append(SetVariable(name=name, value=ast_value))

    def create_task(self, name: str, target: str = "local") -> TaskBuilder:
        """Create a new task with a fluent builder."""
        return TaskBuilder(self, name, target)

    def load_from_file(self, filepath: str | Path) -> Document:
        """Load a .si file."""
        parser = SimpleInfraParser()
        return parser.parse_file(filepath)

    def load_from_string(self, source: str) -> Document:
        """Parse a .si string."""
        parser = SimpleInfraParser()
        return parser.parse(source)

    async def execute_task(self, task_name: str) -> dict[str, Any]:
        """Execute a task by name."""
        document = self._build_document()
        executor = TaskExecutor(
            document=document,
            registry=self.registry,
            dry_run=False,
        )
        return await executor.run_task(task_name)

    async def execute_from_file(self, filepath: str | Path, task_name: str | None = None) -> dict[str, Any]:
        """Load and execute a .si file."""
        document = self.load_from_file(filepath)
        executor = TaskExecutor(
            document=document,
            registry=self.registry,
            project_dir=Path(filepath).parent,
        )

        if task_name:
            return await executor.run_task(task_name)
        elif document.tasks:
            return await executor.run_task(document.tasks[0].name)
        else:
            raise ValueError("No tasks found")

    def _build_document(self) -> Document:
        """Build a Document from programmatically created components."""
        return Document(
            servers=tuple(self.servers),
            variables=tuple(self.variables),
            tasks=tuple(self.tasks),
        )


class TaskBuilder:
    """Fluent builder for creating tasks programmatically."""

    def __init__(self, client: SimpleInfraClient, name: str, target: str):
        self.client = client
        self.name = name
        self.target = target
        self.actions: list[Any] = []

    def install(self, *packages: str) -> TaskBuilder:
        """Add an install action."""
        self.actions.append(InstallAction(packages=packages))
        return self

    def run(self, command: str) -> TaskBuilder:
        """Add a run command action."""
        self.actions.append(RunAction(command=command))
        return self

    def copy(self, source: str, dest: str) -> TaskBuilder:
        """Add a copy file action."""
        from ..ast.nodes import CopyAction
        self.actions.append(CopyAction(source=source, destination=dest))
        return self

    def start_service(self, name: str) -> TaskBuilder:
        """Add a start service action."""
        from ..ast.nodes import ServiceActionNode, ServiceAction
        self.actions.append(ServiceActionNode(action=ServiceAction.START, service_name=name))
        return self

    def build(self) -> TaskDecl:
        """Build and register the task."""
        task = TaskDecl(name=self.name, target=self.target, actions=tuple(self.actions))
        self.client.tasks.append(task)
        return task


# Example usage in Python:
"""
import asyncio
from simpleinfra.api.client import SimpleInfraClient

async def main():
    client = SimpleInfraClient()

    # Define server
    client.add_server("web", host="192.168.1.10", user="root")

    # Create task
    (client.create_task("setup", target="web")
        .install("nginx", "python3")
        .copy("nginx.conf", "/etc/nginx/nginx.conf")
        .start_service("nginx")
        .build())

    # Execute
    result = await client.execute_task("setup")
    print(result)

asyncio.run(main())
"""
