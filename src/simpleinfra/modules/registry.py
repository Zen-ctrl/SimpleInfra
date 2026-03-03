"""Module registry for SimpleInfra.

Maps AST action node types to their module handlers.
This is the central dispatch table for the execution engine.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..ast.nodes import (
    AgentAction,
    AppDependencyAction,
    CheckAction,
    CopyAction,
    CreateDirectoryAction,
    CreateFileAction,
    CreateUserAction,
    DeleteUserAction,
    DownloadAction,
    EnsureAction,
    FlowAnalysisAction,
    InstallAction,
    NetworkAction,
    PolicyAction,
    RemoveAction,
    RunAction,
    SecurityScanAction,
    ServiceActionNode,
    SetOwnerAction,
    SetPermissionsAction,
    TemplateAction,
    UploadAction,
    WaitAction,
)
from ..errors.base import SimpleInfraError
from .base import Module

if TYPE_CHECKING:
    pass


class ModuleRegistry:
    """Central registry mapping AST node types to module handlers."""

    def __init__(self) -> None:
        self._modules: dict[type, Module] = {}

    def register(self, node_type: type, module: Module) -> None:
        """Register a module handler for a given AST node type."""
        self._modules[node_type] = module

    def get(self, node_type: type) -> Module:
        """Look up the module handler for an AST node type."""
        if node_type not in self._modules:
            raise SimpleInfraError(f"No module registered for action type: {node_type.__name__}")
        return self._modules[node_type]

    def has(self, node_type: type) -> bool:
        """Check if a handler is registered for a node type."""
        return node_type in self._modules


def create_default_registry() -> ModuleRegistry:
    """Create a registry with all built-in modules registered."""
    from .package import PackageModule
    from .file import FileModule
    from .service import ServiceModule
    from .command import CommandModule
    from .check import CheckModule
    from .wait import WaitModule
    from .user import UserModule
    from .firewall import FirewallModule
    from .security.scanner import SecurityScannerModule
    from .network.segmentation import NetworkSegmentationModule
    from .network.agent import NetworkAgentModule
    from .network.policy_engine import PolicyEngineModule
    from .network.app_dependency import ApplicationDependencyModule
    from .network.flow_analysis import FlowAnalysisModule

    registry = ModuleRegistry()

    pkg = PackageModule()
    registry.register(InstallAction, pkg)
    registry.register(RemoveAction, pkg)

    file_mod = FileModule()
    registry.register(CopyAction, file_mod)
    registry.register(UploadAction, file_mod)
    registry.register(DownloadAction, file_mod)
    registry.register(TemplateAction, file_mod)
    registry.register(CreateFileAction, file_mod)
    registry.register(CreateDirectoryAction, file_mod)
    registry.register(SetPermissionsAction, file_mod)
    registry.register(SetOwnerAction, file_mod)

    registry.register(ServiceActionNode, ServiceModule())
    registry.register(RunAction, CommandModule())
    registry.register(EnsureAction, FirewallModule())

    check_mod = CheckModule()
    registry.register(CheckAction, check_mod)

    registry.register(WaitAction, WaitModule())

    user_mod = UserModule()
    registry.register(CreateUserAction, user_mod)
    registry.register(DeleteUserAction, user_mod)

    registry.register(SecurityScanAction, SecurityScannerModule())
    registry.register(NetworkAction, NetworkSegmentationModule())
    registry.register(AgentAction, NetworkAgentModule())
    registry.register(PolicyAction, PolicyEngineModule())
    registry.register(AppDependencyAction, ApplicationDependencyModule())
    registry.register(FlowAnalysisAction, FlowAnalysisModule())

    return registry
