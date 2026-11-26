"""Gate coverage: every Python file lives in a directory the Python gates actually check."""

from __future__ import annotations

from quality.core import Finding, Tree
from quality.limits import PYTHON_DIRS


def check(tree: Tree) -> list[Finding]:
    return [
        Finding(
            f,
            1,
            f"Python file outside PYTHON_DIRS {PYTHON_DIRS}: no gate would check it",
        )
        for f in tree.files
        if f.endswith(".py") and f.split("/")[0] not in PYTHON_DIRS
    ]
