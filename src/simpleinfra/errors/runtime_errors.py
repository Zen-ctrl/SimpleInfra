"""Runtime error classes for task execution failures."""

from .base import SimpleInfraError


class TaskExecutionError(SimpleInfraError):
    """Raised when a task action fails during execution."""

    def __init__(self, task_name: str, target: str, action: str, original_error: Exception):
        self.task_name = task_name
        self.target = target
        self.action = action
        self.original_error = original_error
        super().__init__(f"Task '{task_name}' failed on '{target}' at [{action}]: {original_error}")


class VariableNotFoundError(SimpleInfraError):
    """Raised when a {variable} reference cannot be resolved."""

    def __init__(self, variable_name: str):
        self.variable_name = variable_name
        super().__init__(f"Variable '{{{variable_name}}}' is not defined")


class ConnectionError(SimpleInfraError):
    """Raised when a connector cannot reach its target."""

    def __init__(self, target: str, message: str):
        self.target = target
        super().__init__(f"Cannot connect to '{target}': {message}")


class AuthenticationError(ConnectionError):
    """Raised when authentication fails."""

    def __init__(self, target: str, message: str = "Authentication failed"):
        super().__init__(target, message)


class ModuleError(SimpleInfraError):
    """Raised when a module encounters an error during execution."""

    def __init__(self, module_name: str, message: str):
        self.module_name = module_name
        super().__init__(f"Module '{module_name}': {message}")
