"""Package module for SimpleInfra.

Handles installing and removing system packages.
Auto-detects the package manager based on OS family.
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .base import Module, ModuleResult

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


# Package manager commands by OS family
PACKAGE_MANAGERS = {
    "debian": {
        "update": "apt-get update -qq",
        "install": "apt-get install -y -qq",
        "remove": "apt-get remove -y -qq",
        "check": "dpkg -l",
    },
    "redhat": {
        "update": "yum makecache -q",
        "install": "yum install -y -q",
        "remove": "yum remove -y -q",
        "check": "rpm -q",
    },
    "arch": {
        "update": "pacman -Sy --noconfirm",
        "install": "pacman -S --noconfirm",
        "remove": "pacman -R --noconfirm",
        "check": "pacman -Q",
    },
    "alpine": {
        "update": "apk update -q",
        "install": "apk add -q",
        "remove": "apk del -q",
        "check": "apk info -e",
    },
}


class PackageModule(Module):
    """Handles install/remove of system packages."""

    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        action_node = kwargs.get("action")
        if action_node is None:
            return ModuleResult(changed=False, success=False, message="No action provided")

        from ..ast.nodes import InstallAction, RemoveAction

        if isinstance(action_node, InstallAction):
            return await self._install(connector, context, action_node.packages)
        elif isinstance(action_node, RemoveAction):
            return await self._remove(connector, context, action_node.packages)
        else:
            return ModuleResult(changed=False, success=False, message=f"Unknown action: {type(action_node)}")

    async def _install(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        packages: tuple[str, ...],
    ) -> ModuleResult:
        os_family = context.facts.get("os_family", "debian")
        manager = PACKAGE_MANAGERS.get(os_family)

        if not manager:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported OS family: {os_family}. Cannot determine package manager.",
            )

        # Check which packages need to be installed
        to_install = []
        for pkg in packages:
            result = await connector.run_command(f"{manager['check']} {pkg} 2>/dev/null")
            if not result.success:
                to_install.append(pkg)

        if not to_install:
            return ModuleResult(
                changed=False,
                success=True,
                message=f"Already installed: {', '.join(packages)}",
            )

        # Update package cache first
        await connector.run_command(manager["update"], sudo=True)

        # Install packages
        cmd = f"{manager['install']} {' '.join(to_install)}"
        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Installed: {', '.join(to_install)}",
                details={"stdout": result.stdout, "stderr": result.stderr},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to install: {', '.join(to_install)}",
                details={"stdout": result.stdout, "stderr": result.stderr},
            )

    async def _remove(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        packages: tuple[str, ...],
    ) -> ModuleResult:
        os_family = context.facts.get("os_family", "debian")
        manager = PACKAGE_MANAGERS.get(os_family)

        if not manager:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Unsupported OS family: {os_family}",
            )

        # Check which packages are actually installed
        to_remove = []
        for pkg in packages:
            result = await connector.run_command(f"{manager['check']} {pkg} 2>/dev/null")
            if result.success:
                to_remove.append(pkg)

        if not to_remove:
            return ModuleResult(
                changed=False,
                success=True,
                message=f"Already absent: {', '.join(packages)}",
            )

        cmd = f"{manager['remove']} {' '.join(to_remove)}"
        result = await connector.run_command(cmd, sudo=True)

        if result.success:
            return ModuleResult(
                changed=True,
                success=True,
                message=f"Removed: {', '.join(to_remove)}",
                details={"stdout": result.stdout, "stderr": result.stderr},
            )
        else:
            return ModuleResult(
                changed=False,
                success=False,
                message=f"Failed to remove: {', '.join(to_remove)}",
                details={"stdout": result.stdout, "stderr": result.stderr},
            )
