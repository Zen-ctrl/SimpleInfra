"""Variable interpolation engine for SimpleInfra.

Resolves {variable_name} references in strings by searching
through multiple scopes: loop vars -> secrets -> variables -> facts -> builtins.
"""

from __future__ import annotations

import re

from ..errors.runtime_errors import VariableNotFoundError

VARIABLE_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class VariableResolver:
    """Resolves {variable} references in strings."""

    def __init__(
        self,
        variables: dict[str, str | int | bool] | None = None,
        secrets: dict[str, str] | None = None,
        facts: dict[str, str] | None = None,
        builtins: dict[str, str] | None = None,
    ) -> None:
        self.variables = variables or {}
        self.secrets = secrets or {}
        self.facts = facts or {}
        self.builtins = builtins or {}
        self._loop_vars: dict[str, str | int] = {}

    def resolve(self, text: str) -> str:
        """Replace all {var} references with their values.

        Search order (first match wins):
            1. Loop variables (innermost scope)
            2. User-defined variables (set)
            3. Secrets
            4. Host facts
            5. Built-in variables

        Raises:
            VariableNotFoundError: If a referenced variable doesn't exist.
        """
        def replacer(match: re.Match) -> str:
            name = match.group(1)

            # Check scopes in order
            for scope in (self._loop_vars, self.variables, self.secrets, self.facts, self.builtins):
                if name in scope:
                    return str(scope[name])

            raise VariableNotFoundError(name)

        return VARIABLE_PATTERN.sub(replacer, text)

    def resolve_if_string(self, value: object) -> object:
        """Resolve variable references only if the value is a string."""
        if isinstance(value, str):
            return self.resolve(value)
        return value

    def set_loop_variable(self, name: str, value: str | int) -> None:
        """Set a loop iteration variable."""
        self._loop_vars[name] = value

    def clear_loop_variable(self, name: str) -> None:
        """Remove a loop variable after the loop ends."""
        self._loop_vars.pop(name, None)

    def get(self, name: str) -> str | int | bool | None:
        """Look up a variable by name across all scopes."""
        for scope in (self._loop_vars, self.variables, self.secrets, self.facts, self.builtins):
            if name in scope:
                return scope[name]
        return None

    def has(self, name: str) -> bool:
        """Check if a variable exists in any scope."""
        return self.get(name) is not None
