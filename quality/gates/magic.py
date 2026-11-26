"""No magic numbers or repeated string literals: give the value a name once.

A number is fine when it is 0/1/2, sits in a named definition (module/class level
assignment) or is a default argument. A string is flagged when the same text is
written inline several times.
"""

from __future__ import annotations

import ast
from collections import defaultdict

from quality.core import Finding, Tree
from quality.limits import (
    ALLOWED_NUMBERS,
    MIN_REPEATED_STRING_LEN,
    MIN_STRING_REPEATS,
    SOURCE_DIRS,
)


def _named(module: ast.Module) -> set[int]:
    """Ids of nodes that are part of a named definition or a default argument."""
    ids: set[int] = set()
    for node in ast.walk(module):
        if isinstance(node, (ast.Module, ast.ClassDef)):
            values = [
                s.value
                for s in node.body
                if isinstance(s, (ast.Assign, ast.AnnAssign)) and s.value
            ]
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            values = [*node.args.defaults, *filter(None, node.args.kw_defaults)]
        else:
            continue
        ids.update(id(n) for v in values for n in ast.walk(v))
    return ids


def _docstrings(module: ast.Module) -> set[int]:
    nodes = [
        n
        for n in ast.walk(module)
        if isinstance(
            n, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        )
    ]
    return {
        id(n.body[0].value)
        for n in nodes
        if n.body
        and isinstance(n.body[0], ast.Expr)
        and isinstance(n.body[0].value, ast.Constant)
    }


def _fstring_parts(module: ast.Module) -> set[int]:
    return {
        id(v)
        for n in ast.walk(module)
        if isinstance(n, ast.JoinedStr)
        for v in n.values
    }


def _repeatable(text: str) -> bool:
    """Long enough to deserve a name; dunders like `"__main__"` are idioms."""
    return len(text) >= MIN_REPEATED_STRING_LEN and not (
        text.startswith("__") and text.endswith("__")
    )


def _is_magic_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and value not in ALLOWED_NUMBERS
    )


def literals(module: ast.Module) -> tuple[list[ast.Constant], list[ast.Constant]]:
    """(inline numbers, inline strings) that are not part of a named definition."""
    skip = _named(module) | _docstrings(module) | _fstring_parts(module)
    consts = [
        n for n in ast.walk(module) if isinstance(n, ast.Constant) and id(n) not in skip
    ]
    numbers = [n for n in consts if _is_magic_number(n.value)]
    strings = [n for n in consts if isinstance(n.value, str) and _repeatable(n.value)]
    return numbers, strings


def check(tree: Tree) -> list[Finding]:
    findings: list[Finding] = []
    seen: dict[str, list[Finding]] = defaultdict(list)
    for path in tree.python(SOURCE_DIRS):
        numbers, strings = literals(tree.parse(path))
        findings += [
            Finding(path, n.lineno, f"magic number {n.value!r}: name it", key=path)
            for n in numbers
        ]
        for node in strings:
            text = str(node.value)
            message = f"string {text!r} repeated: name it"
            seen[text].append(Finding(path, node.lineno, message, key=f"string:{text}"))
    return findings + [
        f for group in seen.values() if len(group) >= MIN_STRING_REPEATS for f in group
    ]
