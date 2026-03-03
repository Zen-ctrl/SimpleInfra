"""Execution context for SimpleInfra.

The context holds all runtime state: variables, secrets, facts,
and the variable resolver. It's passed to every module during execution.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..variables.builtins import get_builtins
from ..variables.facts import gather_facts, get_local_facts
from ..variables.resolver import VariableResolver

if TYPE_CHECKING:
    from ..ast.nodes import Document, SetVariable
    from ..connectors.base import Connector


class ExecutionContext:
    """Runtime context for task execution."""

    def __init__(
        self,
        variables: dict[str, str | int | bool],
        secrets: dict[str, str],
        facts: dict[str, str] | None = None,
        builtins: dict[str, str] | None = None,
    ) -> None:
        self.variables = variables
        self.secrets = secrets
        self.facts = facts or {}
        self.builtins = builtins or get_builtins()
        self.resolver = VariableResolver(
            variables=self.variables,
            secrets=self.secrets,
            facts=self.facts,
            builtins=self.builtins,
        )

    async def gather_facts(self, connector: "Connector") -> None:
        """Gather system facts from the connected target."""
        self.facts = await gather_facts(connector)
        # Update resolver with fresh facts
        self.resolver.facts = self.facts

    def gather_facts_local(self) -> None:
        """Gather facts for the local machine (non-async)."""
        self.facts = get_local_facts()
        self.resolver.facts = self.facts

    @classmethod
    def from_document(
        cls,
        document: "Document",
        secrets: dict[str, str],
    ) -> "ExecutionContext":
        """Create a context from a parsed document."""
        # Convert SetVariable nodes to a simple dict
        variables: dict[str, str | int | bool] = {}
        for var in document.variables:
            variables[var.name] = _value_to_python(var.value)

        return cls(
            variables=variables,
            secrets=secrets,
        )


def _value_to_python(value: object) -> str | int | bool:
    """Convert an AST value node to a Python primitive."""
    from ..ast.nodes import StringValue, NumberValue, BooleanValue, VariableRef

    if isinstance(value, StringValue):
        return value.value
    elif isinstance(value, NumberValue):
        return value.value
    elif isinstance(value, BooleanValue):
        return value.value
    elif isinstance(value, VariableRef):
        return f"{{{value.name}}}"  # Leave unresolved for now
    else:
        return str(value)
