"""No copy-pasted code: pylint's duplicate-code finds repeated blocks across modules."""

from __future__ import annotations

import json
import re
import subprocess
import sys

from quality.core import Finding, Tree
from quality.limits import SOURCE_DIRS

BLOCK = re.compile(r"==([\w.]+):\[(\d+):(\d+)\]")  # ==module:[first line:last line]


def run_pylint(root) -> list[dict]:
    args = [
        "--disable=all",
        "--enable=duplicate-code",
        "--output-format=json",
        *SOURCE_DIRS,
    ]
    out = subprocess.run(
        [sys.executable, "-m", "pylint", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return json.loads(out or "[]")


def check(tree: Tree) -> list[Finding]:
    """One finding per duplicated block, keyed by the modules that share it."""
    findings = []
    for item in run_pylint(tree.root):
        blocks = BLOCK.findall(item["message"])
        modules = sorted({module for module, _, _ in blocks})
        lines = max(int(last) - int(first) for _, first, last in blocks)
        path = blocks[0][0].replace(".", "/") + ".py"
        message = f"{lines} lines duplicated in {', '.join(modules)}"
        findings.append(
            Finding(path, int(blocks[0][1]), message, " & ".join(modules), lines)
        )
    return findings
