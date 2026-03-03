"""Parse error classes with friendly error messages and source context."""

from .base import SimpleInfraError


class ParseError(SimpleInfraError):
    """Raised when a .si file has syntax errors."""

    def __init__(
        self,
        message: str,
        filename: str = "<stdin>",
        line: int = 0,
        column: int = 0,
        source_lines: list[str] | None = None,
    ):
        self.filename = filename
        self.line = line
        self.column = column
        self.source_lines = source_lines or []
        self.context_lines = self._build_context()
        super().__init__(self._format_message(message))

    def _build_context(self) -> str:
        """Build a 3-line context window around the error."""
        if not self.source_lines:
            return ""
        start = max(0, self.line - 2)
        end = min(len(self.source_lines), self.line + 1)
        lines = []
        for i in range(start, end):
            marker = ">>>" if i == self.line - 1 else "   "
            lines.append(f"{marker} {i + 1:4d} | {self.source_lines[i]}")
        return "\n".join(lines)

    def _format_message(self, message: str) -> str:
        parts = [f"Syntax error in {self.filename} at line {self.line}, column {self.column}"]
        if self.context_lines:
            parts.append(self.context_lines)
            parts.append(" " * (self.column + 10) + f"^--- {message}")
        else:
            parts.append(message)
        return "\n".join(parts)


class ValidationError(SimpleInfraError):
    """Raised when a .si file has semantic errors (e.g. undefined references)."""

    def __init__(self, message: str, filename: str = "<stdin>", line: int = 0):
        self.filename = filename
        self.line = line
        super().__init__(f"{filename}:{line}: {message}" if line else f"{filename}: {message}")
