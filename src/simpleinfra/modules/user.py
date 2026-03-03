"""User module for SimpleInfra.

Handles creating and deleting user accounts on Linux systems.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class UserModule(Module):
    """Handles user management operations."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action = kwargs.get("action")
        if action is None:
            return ModuleResult(changed=False, success=False, message="No action provided")

        from ..ast.nodes import CreateUserAction, DeleteUserAction

        if isinstance(action, CreateUserAction):
            return await self._create_user(connector, action.username, action.home_dir)
        elif isinstance(action, DeleteUserAction):
            return await self._delete_user(connector, action.username)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown user action")

    async def _user_exists(self, connector: "Connector", username: str) -> bool:
        result = await connector.run_command(f"id -u {username} 2>/dev/null")
        return result.success

    async def _create_user(self, connector: "Connector", username: str, home_dir: str | None) -> ModuleResult:
        if await self._user_exists(connector, username):
            return ModuleResult(changed=False, success=True, message=f"User {username} already exists")

        if home_dir:
            cmd = f"useradd -m -d {home_dir} {username}"
        else:
            cmd = f"useradd -m {username}"

        result = await connector.run_command(cmd, sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Created user {username}")
        return ModuleResult(changed=False, success=False, message=f"Failed to create user {username}: {result.stderr}")

    async def _delete_user(self, connector: "Connector", username: str) -> ModuleResult:
        if not await self._user_exists(connector, username):
            return ModuleResult(changed=False, success=True, message=f"User {username} already absent")

        result = await connector.run_command(f"userdel -r {username}", sudo=True)
        if result.success:
            return ModuleResult(changed=True, success=True, message=f"Deleted user {username}")
        return ModuleResult(changed=False, success=False, message=f"Failed to delete user {username}: {result.stderr}")
