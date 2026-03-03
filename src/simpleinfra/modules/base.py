"""Base module interface for SimpleInfra.

Every module (package, file, service, etc.) implements this interface.
Modules are the "verbs" of the DSL -- they know how to execute actions
on any connector.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..connectors.base import Connector
    from ..engine.context import ExecutionContext


@dataclass
class ModuleResult:
    """Result of a module execution."""
    changed: bool
    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class Module(ABC):
    """Base class for all SimpleInfra modules."""

    @abstractmethod
    async def execute(
        self,
        connector: "Connector",
        context: "ExecutionContext",
        **kwargs: Any,
    ) -> ModuleResult:
        """Execute the module action.

        Args:
            connector: The target connector to execute on.
            context: The execution context with variables and facts.
            **kwargs: Action-specific arguments.

        Returns:
            ModuleResult with changed/success/message.
        """
