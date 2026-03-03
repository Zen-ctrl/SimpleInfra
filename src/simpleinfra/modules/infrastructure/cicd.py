"""CI/CD integration module.

Provides:
- Git repository operations
- Build pipeline automation
- Deployment workflows
- Artifact management
- Blue-green deployments
- Rollback procedures
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class CICDModule(Module):
    """CI/CD integration and automation."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "clone")

        if action == "clone":
            return await self._clone_repo(connector, kwargs)
        elif action == "pull":
            return await self._pull_updates(connector, kwargs)
        elif action == "checkout":
            return await self._checkout_branch(connector, kwargs)
        elif action == "build":
            return await self._build_project(connector, kwargs)
        elif action == "deploy":
            return await self._deploy_app(connector, kwargs)
        elif action == "blue_green_deploy":
            return await self._blue_green_deploy(connector, kwargs)
        elif action == "rollback":
            return await self._rollback(connector, kwargs)
        elif action == "setup_hooks":
            return await self._setup_hooks(connector, kwargs)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown CI/CD action: {action}")

    async def _clone_repo(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Clone Git repository."""
        repo = params.get("repo", "")
        destination = params.get("destination", "")
        branch = params.get("branch", "main")
        depth = params.get("depth", "")

        if not repo or not destination:
            return ModuleResult(changed=False, success=False, message="Repo and destination required")

        cmd = f"git clone -b {branch}"
        if depth:
            cmd += f" --depth {depth}"
        cmd += f" {repo} {destination}"

        result = await connector.run_command(cmd, sudo=True)
        return ModuleResult(changed=True, success=result.success,
            message=f"Repository cloned to {destination}", details={"repo": repo, "branch": branch})

    async def _pull_updates(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Pull Git updates."""
        path = params.get("path", "")
        restart_service = params.get("restart_service", "")

        result = await connector.run_command(f"git -C {path} pull", sudo=True)

        if result.success and restart_service:
            await connector.run_command(f"systemctl restart {restart_service}", sudo=True)

        return ModuleResult(changed=True, success=result.success, message="Updates pulled")

    async def _checkout_branch(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Checkout Git branch."""
        path = params.get("path", "")
        branch = params.get("branch", "main")

        result = await connector.run_command(f"git -C {path} checkout {branch}", sudo=True)
        return ModuleResult(changed=True, success=result.success, message=f"Checked out {branch}")

    async def _build_project(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Build project (auto-detect build tool)."""
        path = params.get("path", "")
        build_tool = params.get("build_tool", "auto")
        build_cmd = params.get("build_cmd", "")

        if build_cmd:
            result = await connector.run_command(f"cd {path} && {build_cmd}", sudo=True)
        elif build_tool == "auto":
            # Auto-detect build tool
            checks = [
                ("package.json", "npm install && npm run build"),
                ("requirements.txt", "pip install -r requirements.txt"),
                ("Makefile", "make"),
                ("pom.xml", "mvn package"),
                ("go.mod", "go build"),
            ]

            for file, cmd in checks:
                check_result = await connector.run_command(f"test -f {path}/{file}", sudo=True)
                if check_result.success:
                    result = await connector.run_command(f"cd {path} && {cmd}", sudo=True)
                    break
            else:
                return ModuleResult(changed=False, success=False, message="Could not detect build tool")
        else:
            build_commands = {
                "npm": "npm install && npm run build",
                "python": "pip install -r requirements.txt",
                "go": "go build",
                "maven": "mvn package",
            }
            cmd = build_commands.get(build_tool, "")
            result = await connector.run_command(f"cd {path} && {cmd}", sudo=True)

        return ModuleResult(changed=True, success=result.success, message="Build completed")

    async def _deploy_app(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Deploy application."""
        source = params.get("source", "")
        destination = params.get("destination", "/var/www/app")
        restart_service = params.get("restart_service", "")
        run_migrations = params.get("run_migrations", "false") == "true"

        # Copy files
        result = await connector.run_command(f"rsync -av --delete {source}/ {destination}/", sudo=True)

        if not result.success:
            return ModuleResult(changed=False, success=False, message="Deployment failed")

        # Run migrations if requested
        if run_migrations:
            await connector.run_command(f"cd {destination} && python manage.py migrate", sudo=True)

        # Restart service
        if restart_service:
            await connector.run_command(f"systemctl restart {restart_service}", sudo=True)

        return ModuleResult(changed=True, success=True, message="Application deployed")

    async def _blue_green_deploy(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Blue-green deployment."""
        source = params.get("source", "")
        app_dir = params.get("app_dir", "/var/www")
        service = params.get("service", "myapp")

        # Determine current and next slots
        blue_path = f"{app_dir}/blue"
        green_path = f"{app_dir}/green"
        current_link = f"{app_dir}/current"

        # Check which slot is current
        check_result = await connector.run_command(f"readlink {current_link}", sudo=True)
        current_slot = check_result.stdout.strip()

        if "blue" in current_slot:
            next_slot = green_path
            next_name = "green"
        else:
            next_slot = blue_path
            next_name = "blue"

        # Deploy to inactive slot
        await connector.run_command(f"rsync -av --delete {source}/ {next_slot}/", sudo=True)

        # Health check on next slot (simplified)
        await connector.run_command(f"sleep 2")  # Give app time to start

        # Switch symlink
        await connector.run_command(f"ln -snf {next_slot} {current_link}", sudo=True)

        # Restart service
        await connector.run_command(f"systemctl restart {service}", sudo=True)

        return ModuleResult(changed=True, success=True,
            message=f"Blue-green deployment: switched to {next_name}",
            details={"previous_slot": current_slot, "new_slot": next_name})

    async def _rollback(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Rollback to previous deployment."""
        app_dir = params.get("app_dir", "/var/www")
        service = params.get("service", "myapp")

        blue_path = f"{app_dir}/blue"
        green_path = f"{app_dir}/green"
        current_link = f"{app_dir}/current"

        # Get current slot
        check_result = await connector.run_command(f"readlink {current_link}", sudo=True)
        current_slot = check_result.stdout.strip()

        # Switch to other slot
        if "blue" in current_slot:
            previous_slot = green_path
            previous_name = "green"
        else:
            previous_slot = blue_path
            previous_name = "blue"

        # Switch symlink
        await connector.run_command(f"ln -snf {previous_slot} {current_link}", sudo=True)

        # Restart service
        await connector.run_command(f"systemctl restart {service}", sudo=True)

        return ModuleResult(changed=True, success=True,
            message=f"Rolled back to {previous_name}",
            details={"rolled_back_to": previous_name})

    async def _setup_hooks(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Setup Git hooks."""
        repo_path = params.get("repo_path", "")
        hook_type = params.get("hook_type", "post-receive")
        hook_script = params.get("hook_script", "")

        if not repo_path or not hook_script:
            return ModuleResult(changed=False, success=False, message="Repo path and hook script required")

        hook_path = f"{repo_path}/.git/hooks/{hook_type}"

        # Write hook script
        await connector.run_command(f"cat > {hook_path} << 'EOL'\n{hook_script}\nEOL", sudo=True)
        await connector.run_command(f"chmod +x {hook_path}", sudo=True)

        return ModuleResult(changed=True, success=True, message=f"Git hook {hook_type} configured")
