"""Git module for SimpleInfra.

Manages Git repositories: clone, pull, checkout, etc.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


class GitModule(Module):
    """Manages Git repositories."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        operation = kwargs.get("operation", "clone")

        if operation == "clone":
            return await self._clone(connector, context, kwargs)
        elif operation == "pull":
            return await self._pull(connector, context, kwargs)
        elif operation == "checkout":
            return await self._checkout(connector, context, kwargs)
        elif operation == "commit":
            return await self._commit(connector, context, kwargs)
        elif operation == "push":
            return await self._push(connector, context, kwargs)
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unknown Git operation: {operation}",
            )

    async def _clone(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Clone a Git repository."""
        repo = context.resolver.resolve(params.get("repo", ""))
        dest = context.resolver.resolve(params.get("dest", ""))
        branch = params.get("branch")

        # Check if already cloned
        check = await connector.run_command(f"test -d {dest}/.git")
        if check.success:
            return ModuleResult(
                changed=False,
                success=True,
                message=f"Repository already cloned at {dest}",
            )

        # Clone
        cmd = f"git clone {repo} {dest}"
        if branch:
            cmd += f" -b {branch}"

        result = await connector.run_command(cmd)
        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Cloned {repo} to {dest}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to clone: {result.stderr}",
            )

    async def _pull(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Pull latest changes."""
        repo_path = context.resolver.resolve(params.get("path", ""))

        result = await connector.run_command(f"cd {repo_path} && git pull")
        if result.success:
            # Check if anything changed
            changed = "Already up to date" not in result.stdout
            return ModuleResult(
                changed=changed,
                success=True,
                message=f"Pulled latest changes" if changed else "Already up to date",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to pull: {result.stderr}",
            )

    async def _checkout(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Checkout a branch or commit."""
        repo_path = context.resolver.resolve(params.get("path", ""))
        ref = params.get("ref", "main")

        result = await connector.run_command(f"cd {repo_path} && git checkout {ref}")
        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Checked out {ref}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to checkout: {result.stderr}",
            )

    async def _commit(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Commit changes."""
        repo_path = context.resolver.resolve(params.get("path", ""))
        message = context.resolver.resolve(params.get("message", "Update"))

        # Add all changes
        await connector.run_command(f"cd {repo_path} && git add .")

        # Commit
        result = await connector.run_command(
            f'cd {repo_path} && git commit -m "{message}"'
        )

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Committed: {message}",
            )
        elif "nothing to commit" in result.stdout:
            return ModuleResult(
                changed=False,
                success=True,
                message="Nothing to commit",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to commit: {result.stderr}",
            )

    async def _push(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        params: dict[str, Any],
    ) -> ModuleResult:
        """Push commits to remote."""
        repo_path = context.resolver.resolve(params.get("path", ""))
        remote = params.get("remote", "origin")
        branch = params.get("branch", "main")

        result = await connector.run_command(
            f"cd {repo_path} && git push {remote} {branch}"
        )

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Pushed to {remote}/{branch}",
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to push: {result.stderr}",
            )


# Updated DSL syntax for Git:
# task "Deploy from Git" on web:
#     git clone "https://github.com/user/repo.git" to "/opt/app"
#     git pull at "/opt/app"
#     git checkout "v1.0.0" at "/opt/app"
#
#     run "cd /opt/app && npm install"
#     run "systemctl restart myapp"
