"""Main parser for the SimpleInfra DSL.

Reads a .si file, parses it using Lark, transforms the parse tree
into a typed AST, and validates it.
"""

from pathlib import Path

from lark import Lark
from lark.exceptions import UnexpectedInput

from ..ast.nodes import Document
from ..errors.parse_errors import ParseError
from .lexer import SimpleInfraIndenter
from .transformer import SimpleInfraTransformer
from .validator import validate

_GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"


class SimpleInfraParser:
    """Parses .si source code into a validated AST Document."""

    def __init__(self) -> None:
        grammar_text = _GRAMMAR_PATH.read_text(encoding="utf-8")
        self._parser = Lark(
            grammar_text,
            parser="lalr",
            postlex=SimpleInfraIndenter(),
            propagate_positions=True,
            maybe_placeholders=False,
        )

    def parse(self, source: str, filename: str = "<stdin>") -> Document:
        """Parse source code and return a validated AST Document.

        Args:
            source: The .si source code string.
            filename: The filename for error reporting.

        Returns:
            A validated Document AST.

        Raises:
            ParseError: If the source has syntax errors.
            ValidationError: If the AST has semantic errors.
        """
        source_lines = source.splitlines()

        try:
            tree = self._parser.parse(source + "\n")
        except UnexpectedInput as e:
            raise self._friendly_error(e, source_lines, filename) from e

        transformer = SimpleInfraTransformer(filename)
        document = transformer.transform(tree)

        validate(document, filename)

        return document

    def parse_file(self, filepath: str | Path) -> Document:
        """Parse a .si file from disk.

        Args:
            filepath: Path to the .si file.

        Returns:
            A validated Document AST.
        """
        path = Path(filepath)
        source = path.read_text(encoding="utf-8")
        return self.parse(source, filename=str(path))

    def _friendly_error(
        self,
        error: UnexpectedInput,
        source_lines: list[str],
        filename: str,
    ) -> ParseError:
        """Convert a Lark UnexpectedInput into a friendly ParseError."""
        line = getattr(error, "line", 0)
        column = getattr(error, "column", 0)

        # Build a helpful message
        expected = getattr(error, "expected", set())
        if expected:
            expected_str = ", ".join(sorted(str(e) for e in expected))
            message = f"Unexpected input. Expected one of: {expected_str}"
        else:
            message = str(error).split("\n")[0]

        return ParseError(
            message=message,
            filename=filename,
            line=line,
            column=column,
            source_lines=source_lines,
        )
