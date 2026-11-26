"""Lint suppressions: always name the rule they silence, and keep their number from growing."""

from __future__ import annotations

import re

from quality.core import Finding, Tree
from quality.limits import SOURCE_DIRS

SUPPRESSION = re.compile(
    r"#\s*(noqa|type:\s*ignore|pylint:\s*disable|nosec|pragma:\s*no cover)([^\n]*)"
)
NEEDS_CODE = {"noqa": ":", "type: ignore": "["}  # what must follow the marker


def scan(tree: Tree) -> list[tuple[str, int, str, str]]:
    """(path, line, kind, rest-of-comment) for every suppression in source code."""
    found = []
    for path in tree.python(SOURCE_DIRS):
        for number, line in enumerate(tree.read(path).splitlines(), 1):
            if match := SUPPRESSION.search(line):
                found.append(
                    (path, number, re.sub(r"\s+", " ", match.group(1)), match.group(2))
                )
    return found


def blanket(tree: Tree) -> list[Finding]:
    """A suppression that silences every rule on the line hides future problems."""
    return [
        Finding(path, line, f"'# {kind}' must name the rule it silences")
        for path, line, kind, rest in scan(tree)
        if kind in NEEDS_CODE and not rest.lstrip().startswith(NEEDS_CODE[kind])
    ]


def budget(tree: Tree) -> list[Finding]:
    """Every suppression is debt: counted per file by a ratchet."""
    return [
        Finding(path, line, f"suppression '# {kind}'", key=path)
        for path, line, kind, _ in scan(tree)
    ]
