"""Docker module for SimpleInfra.

Manages Docker containers, images, networks, and volumes.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class DockerModule(Module):
    """Manages Docker containers and images."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action")
        operation = kwargs.get("operation", "run")

        if operation == "run":
            return await self._run_container(connector, context, kwargs)
        elif operation == "build":
            return await self._build_image(connector, context, kwargs)
        elif operation == "pull":
            return await self._pull_image(connector, context, kwargs)
        elif operation == "stop":
            return await self._stop_container(connector, kwargs)
        elif operation == "remove":
            return await self._remove_container(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown Docker operation: {operation}",
            )

    async def _run_container(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Run a Docker container."""
        name = params.get("name", "")
        image = params.get("image", "")
        ports = params.get("ports", {})
        volumes = params.get("volumes", {})
        env = params.get("env", {})

        # Check if container already running
        check = await connector.run_command(f"docker ps -q -f name={name}")
        if check.success and check.stdout.strip():
            return ModuleResult(
                changed=False,
                success=True,
                message=f"Container {name} already running",
            )

        # Build docker run command
        cmd_parts = ["docker run -d"]
        cmd_parts.append(f"--name {name}")

        for host_port, container_port in ports.items():
            cmd_parts.append(f"-p {host_port}:{container_port}")

        for host_path, container_path in volumes.items():
            cmd_parts.append(f"-v {host_path}:{container_path}")

        for key, value in env.items():
            cmd_parts.append(f"-e {key}={value}")

        cmd_parts.append(image)
        cmd = " ".join(cmd_parts)

        result = await connector.run_command(cmd)
        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Started container {name} from {image}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to start container: {result.stderr}",
            )

    async def _build_image(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Build a Docker image."""
        tag = params.get("tag", "")
        dockerfile = params.get("dockerfile", "Dockerfile")
        context_path = params.get("context", ".")

        cmd = f"docker build -t {tag} -f {dockerfile} {context_path}"
        result = await connector.run_command(cmd)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Built image {tag}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to build image: {result.stderr}",
            )

    async def _pull_image(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Pull a Docker image."""
        image = params.get("image", "")

        result = await connector.run_command(f"docker pull {image}")
        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Pulled image {image}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to pull image: {result.stderr}",
            )

    async def _stop_container(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Stop a Docker container."""
        name = params.get("name", "")

        result = await connector.run_command(f"docker stop {name}")
        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Stopped container {name}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to stop container: {result.stderr}",
            )

    async def _remove_container(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Remove a Docker container."""
        name = params.get("name", "")
        force = params.get("force", False)

        cmd = f"docker rm {'--force' if force else ''} {name}"
        result = await connector.run_command(cmd)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Removed container {name}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to remove container: {result.stderr}",
            )


# Updated DSL syntax for Docker:
# docker "myapp":
#     image "nginx:latest"
#     ports:
#         80: 8080
#         443: 8443
#     volumes:
#         "./app": "/usr/share/nginx/html"
#     env:
#         APP_ENV: "production"
#
# task "Deploy Container" on local:
#     docker run "myapp"
#     docker build tag="myapp:v1.0" dockerfile="Dockerfile"
#     docker pull "postgres:14"
