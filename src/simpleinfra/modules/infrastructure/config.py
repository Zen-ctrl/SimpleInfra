"""Configuration management module.

Provides:
- Environment-specific configurations
- Secret rotation
- Configuration validation
- Advanced templating
- Config file management
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from ..base import Module, ModuleResult

if TYPE_CHECKING:
    from ...connectors.base import Connector
    from ...engine.context import ExecutionContext


class ConfigModule(Module):
    """Configuration management."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action", "from_template")

        if action == "from_template":
            return await self._from_template(connector, kwargs)
        elif action == "validate":
            return await self._validate_config(connector, kwargs)
        elif action == "rotate_secret":
            return await self._rotate_secret(connector, kwargs)
        elif action == "env_config":
            return await self._env_config(connector, kwargs)
        elif action == "diff":
            return await self._diff_configs(connector, kwargs)
        elif action == "rollback":
            return await self._rollback_config(connector, kwargs)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown config action: {action}")

    async def _from_template(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Generate config from template."""
        template = params.get("template", "")
        destination = params.get("destination", "")
        variables = params.get("variables", {})
        validate_command = params.get("validate_command", "")

        if not template or not destination:
            return ModuleResult(changed=False, success=False, message="Template and destination required")

        # Read template
        template_result = await connector.run_command(f"cat {template}", sudo=True)
        if not template_result.success:
            return ModuleResult(changed=False, success=False, message=f"Template not found: {template}")

        template_content = template_result.stdout

        # Simple variable substitution (can be enhanced with Jinja2)
        for key, value in variables.items():
            template_content = template_content.replace(f"{{{{{key}}}}}", str(value))

        # Backup existing config
        await connector.run_command(f"cp {destination} {destination}.bak 2>/dev/null || true", sudo=True)

        # Write new config
        await connector.run_command(f"cat > {destination} << 'EOL'\n{template_content}\nEOL", sudo=True)

        # Validate if command provided
        if validate_command:
            validate_result = await connector.run_command(validate_command, sudo=True)
            if not validate_result.success:
                # Rollback on validation failure
                await connector.run_command(f"mv {destination}.bak {destination}", sudo=True)
                return ModuleResult(changed=False, success=False,
                    message="Validation failed, config rolled back",
                    details={"error": validate_result.stderr})

        return ModuleResult(changed=True, success=True,
            message=f"Config deployed to {destination}",
            details={"template": template, "destination": destination})

    async def _validate_config(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Validate configuration file."""
        config_file = params.get("config_file", "")
        validator = params.get("validator", "")

        if validator == "nginx":
            result = await connector.run_command("nginx -t", sudo=True)
        elif validator == "apache":
            result = await connector.run_command("apache2ctl configtest", sudo=True)
        elif validator == "yaml":
            result = await connector.run_command(f"python3 -c 'import yaml; yaml.safe_load(open(\"{config_file}\"))'", sudo=True)
        elif validator == "json":
            result = await connector.run_command(f"python3 -c 'import json; json.load(open(\"{config_file}\"))'", sudo=True)
        else:
            result = await connector.run_command(validator, sudo=True)

        return ModuleResult(changed=False, success=result.success,
            message="Validation passed" if result.success else "Validation failed",
            details={"output": result.stderr + result.stdout})

    async def _rotate_secret(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Rotate secret/credential."""
        secret_type = params.get("secret_type", "password")
        service = params.get("service", "")
        length = params.get("length", "32")

        # Generate new secret
        gen_cmd = f"openssl rand -base64 {length}"
        gen_result = await connector.run_command(gen_cmd, sudo=True)

        if not gen_result.success:
            return ModuleResult(changed=False, success=False, message="Secret generation failed")

        new_secret = gen_result.stdout.strip()

        # Store in file (would integrate with vault/secrets manager in production)
        secret_file = f"/etc/simpleinfra/secrets/{service}_{secret_type}"
        await connector.run_command(f"mkdir -p /etc/simpleinfra/secrets", sudo=True)
        await connector.run_command(f"echo '{new_secret}' > {secret_file}", sudo=True)
        await connector.run_command(f"chmod 600 {secret_file}", sudo=True)

        return ModuleResult(changed=True, success=True,
            message=f"Secret rotated for {service}",
            details={"secret_file": secret_file, "length": len(new_secret)})

    async def _env_config(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Deploy environment-specific configuration."""
        environment = params.get("environment", "production")
        app = params.get("app", "myapp")
        config_source = params.get("config_source", "")
        config_dest = params.get("config_dest", "")

        # Copy environment-specific config
        env_config_file = f"{config_source}/{environment}.conf"

        result = await connector.run_command(f"cp {env_config_file} {config_dest}", sudo=True)

        if result.success:
            return ModuleResult(changed=True, success=True,
                message=f"{environment} config deployed",
                details={"environment": environment, "destination": config_dest})
        else:
            return ModuleResult(changed=False, success=False,
                message="Config deployment failed", details={"error": result.stderr})

    async def _diff_configs(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Show difference between configs."""
        file1 = params.get("file1", "")
        file2 = params.get("file2", "")

        result = await connector.run_command(f"diff -u {file1} {file2}", sudo=True)

        return ModuleResult(changed=False, success=True,
            message="Config diff",
            details={"diff": result.stdout if result.stdout else "Files are identical"})

    async def _rollback_config(self, connector: "Connector", params: dict[str, Any]) -> ModuleResult:
        """Rollback configuration to backup."""
        config_file = params.get("config_file", "")

        backup_file = f"{config_file}.bak"

        # Check if backup exists
        check_result = await connector.run_command(f"test -f {backup_file}", sudo=True)
        if not check_result.success:
            return ModuleResult(changed=False, success=False, message="No backup found")

        # Restore backup
        result = await connector.run_command(f"cp {backup_file} {config_file}", sudo=True)

        return ModuleResult(changed=True, success=result.success,
            message="Config rolled back to backup")
