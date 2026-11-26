"""Small and simple: bounded function length, parameter count, complexity and file size."""

from __future__ import annotations

import ast

from radon.complexity import cc_visit

from quality.core import Finding, Tree
from quality.limits import (
    MAX_COMPLEXITY,
    MAX_FILE_LINES,
    MAX_FUNCTION_LINES,
    MAX_PARAMS,
    SOURCE_DIRS,
)


def _functions(module: ast.Module):
    for node in ast.walk(module):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def check(tree: Tree) -> list[Finding]:
    findings = []
    for path in tree.python(SOURCE_DIRS):
        text, module = tree.read(path), tree.parse(path)
        if (lines := len(text.splitlines())) > MAX_FILE_LINES:
            findings.append(
                Finding(
                    path,
                    1,
                    f"file has {lines} lines (max {MAX_FILE_LINES})",
                    f"{path}:file-lines",
                    lines,
                )
            )
        for fn in _functions(module):
            length, params = fn.end_lineno - fn.lineno + 1, len(fn.args.args) + len(
                fn.args.kwonlyargs
            )
            for what, value, limit in (
                ("lines", length, MAX_FUNCTION_LINES),
                ("params", params, MAX_PARAMS),
            ):
                if value > limit:
                    findings.append(
                        Finding(
                            path,
                            fn.lineno,
                            f"{fn.name} has {value} {what} (max {limit})",
                            f"{path}::{fn.name}:{what}",
                            value,
                        )
                    )
        for block in cc_visit(text):
            if block.complexity > MAX_COMPLEXITY:
                findings.append(
                    Finding(
                        path,
                        block.lineno,
                        f"{block.name} complexity {block.complexity} (max {MAX_COMPLEXITY})",
                        f"{path}::{block.name}:complexity",
                        block.complexity,
                    )
                )
    return findings
