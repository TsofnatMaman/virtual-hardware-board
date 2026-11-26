"""Repository hygiene: no submodule pointers, build outputs, stray binaries or huge files."""

from __future__ import annotations

import re
import subprocess
from fnmatch import fnmatch

from quality.core import Finding, Tree
from quality.limits import ALLOWED_BINARIES, FORBIDDEN_TRACKED, MAX_FILE_BYTES

GITLINK_MODE = "160000"
INDEX_ENTRY = re.compile(
    r"^(?P<mode>\d+) \w+ \d\t(?P<path>.+)$"
)  # `git ls-files -s` line
GITLINK_MESSAGE = (
    "submodule pointer (gitlink): vendor the files or declare it in .gitmodules"
)


def gitlinks(tree: Tree) -> list[str]:
    """Tracked directories that are submodule pointers (git index mode 160000)."""
    out = subprocess.run(
        ["git", "ls-files", "-s", "-z"],
        cwd=tree.root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    entries = (INDEX_ENTRY.match(entry) for entry in out.split("\0"))
    return [m.group("path") for m in entries if m and m.group("mode") == GITLINK_MODE]


def check(tree: Tree) -> list[Finding]:
    findings = [
        Finding(
            p,
            1,
            GITLINK_MESSAGE,
        )
        for p in gitlinks(tree)
    ]
    for path in tree.files:
        if any(fnmatch(path, pattern) for pattern in FORBIDDEN_TRACKED):
            findings.append(
                Finding(path, 1, "build output / generated file must not be tracked")
            )
        elif path.endswith(".bin") and path not in ALLOWED_BINARIES:
            findings.append(
                Finding(path, 1, "binary not in ALLOWED_BINARIES (quality/limits.py)")
            )
        size = (tree.root / path).stat().st_size
        if size > MAX_FILE_BYTES:
            findings.append(
                Finding(
                    path, 1, f"{size} bytes exceeds MAX_FILE_BYTES ({MAX_FILE_BYTES})"
                )
            )
    return findings
