"""Container and orchestration module.

Provides:
- Docker container management
- Docker Compose deployment
- Kubernetes manifest deployment
- Container health checks
- Image management and registry operations
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class ContainerModule(Module):
    """Container and orchestration management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "run")

        if action == "install_docker":
            return await self._install_docker(connector, kwargs)
        elif action == "run":
            return await self._run_container(connector, kwargs)
        elif action == "stop":
            return await self._stop_container(connector, kwargs)
        elif action == "remove":
            return await self._remove_container(connector, kwargs)
        elif action == "build":
            return await self._build_image(connector, kwargs)
        elif action == "compose_up":
            return await self._compose_up(connector, kwargs)
        elif action == "compose_down":
            return await self._compose_down(connector, kwargs)
        elif action == "health_check":
            return await self._health_check(connector, kwargs)
        elif action == "prune":
            return await self._prune_system(connector, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown container action: {action}",
            )

    async def _install_docker(self,connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Install Docker."""
        commands = [
            "apt-get update",
            "apt-get install -y ca-certificates curl gnupg",
            "install -m 0755 -d /etc/apt/keyrings",
            "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg",
            "chmod a+r /etc/apt/keyrings/docker.gpg",
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list',
            "apt-get update",
            "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
        ]

        for cmd in commands:
            result = await connector.run_command(cmd, sudo=True)
            if not result.success:
                return ModuleResult(changed=False, success=False,
                    message=f"Failed to install Docker", details={"error": result.stderr})

        await connector.run_command("systemctl start docker", sudo=True)
        await connector.run_command("systemctl enable docker", sudo=True)

        return ModuleResult(changed=True, success=True, message="Docker installed successfully")

    async def _run_container(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Run a Docker container."""
        image = params.get("image", "")
        name = params.get("name", "")
        ports = params.get("ports", "")
        volumes = params.get("volumes", "")
        env_file = params.get("env_file", "")
        restart_policy = params.get("restart_policy", "no")
        detach = params.get("detach", "true") == "true"
        command = params.get("command", "")

        if not image:
            return ModuleResult(changed=False, success=False, message="Image is required")

        cmd_parts = ["docker run"]
        if detach:
            cmd_parts.append("-d")
        if name:
            cmd_parts.append(f"--name {name}")
        if ports:
            for port in ports.split(","):
                cmd_parts.append(f"-p {port.strip()}")
        if volumes:
            for vol in volumes.split(","):
                cmd_parts.append(f"-v {vol.strip()}")
        if env_file:
            cmd_parts.append(f"--env-file {env_file}")
        if restart_policy:
            cmd_parts.append(f"--restart {restart_policy}")

        cmd_parts.append(image)
        if command:
            cmd_parts.append(command)

        result = await connector.run_command(" ".join(cmd_parts), sudo=True)

        if result.success:
            return ModuleResult(changed=True, success=True,
                message=f"Container {name or image} started",
                details={"container_id": result.stdout.strip()})
        else:
            return ModuleResult(changed=False, success=False,
                message="Failed to start container", details={"error": result.stderr})

    async def _stop_container(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Stop a container."""
        name = params.get("name", "")
        result = await connector.run_command(f"docker stop {name}", sudo=True)
        return ModuleResult(changed=True, success=result.success, message=f"Container {name} stopped")

    async def _remove_container(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Remove a container."""
        name = params.get("name", "")
        force = params.get("force", "false") == "true"
        force_flag = "-f" if force else ""
        result = await connector.run_command(f"docker rm {force_flag} {name}", sudo=True)
        return ModuleResult(changed=True, success=result.success, message=f"Container {name} removed")

    async def _build_image(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Build Docker image."""
        dockerfile = params.get("dockerfile", "Dockerfile")
        tag = params.get("tag", "latest")
        context = params.get("context", ".")
        build_args = params.get("build_args", "")

        cmd = f"docker build -f {dockerfile} -t {tag}"
        if build_args:
            for arg in build_args.split(","):
                cmd += f" --build-arg {arg.strip()}"
        cmd += f" {context}"

        result = await connector.run_command(cmd, sudo=True)
        return ModuleResult(changed=True, success=result.success,
            message=f"Image {tag} built", details={"tag": tag})

    async def _compose_up(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Start services with Docker Compose."""
        file = params.get("file", "docker-compose.yml")
        project = params.get("project", "")
        detach = params.get("detach", "true") == "true"

        cmd = f"docker compose -f {file}"
        if project:
            cmd += f" -p {project}"
        cmd += " up"
        if detach:
            cmd += " -d"

        result = await connector.run_command(cmd, sudo=True)
        return ModuleResult(changed=True, success=result.success,
            message="Docker Compose services started")

    async def _compose_down(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Stop Docker Compose services."""
        file = params.get("file", "docker-compose.yml")
        project = params.get("project", "")
        volumes = params.get("volumes", "false") == "true"

        cmd = f"docker compose -f {file}"
        if project:
            cmd += f" -p {project}"
        cmd += " down"
        if volumes:
            cmd += " -v"

        result = await connector.run_command(cmd, sudo=True)
        return ModuleResult(changed=True, success=result.success, message="Services stopped")

    async def _health_check(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Check container health."""
        name = params.get("name", "")
        result = await connector.run_command(f"docker inspect --format='{{{{.State.Health.Status}}}}' {name}", sudo=True)
        status = result.stdout.strip() if result.success else "unknown"
        return ModuleResult(changed=False, success=result.success,
            message=f"Container health: {status}", details={"status": status})

    async def _prune_system(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Prune Docker system."""
        all_flag = "-a" if params.get("all", "false") == "true" else ""
        result = await connector.run_command(f"docker system prune {all_flag} -f", sudo=True)
        return ModuleResult(changed=True, success=result.success, message="Docker system pruned")
