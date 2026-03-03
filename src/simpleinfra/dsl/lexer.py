"""Indentation-aware postlexer for the SimpleInfra DSL.

Uses Lark's built-in Indenter to emit _INDENT/_DEDENT tokens
based on indentation level changes, similar to Python.
"""

from lark.indenter import Indenter


class SimpleInfraIndenter(Indenter):
    NL_type = "_NL"
    OPEN_PAREN_types = ["LSQB"]       # [
    CLOSE_PAREN_types = ["RSQB"]      # ]
    INDENT_type = "_INDENT"
    DEDENT_type = "_DEDENT"
    tab_len = 4
