"""The one list of gates. CI, pre-commit and the local runner all read it.

Add a gate: write `quality/gates/<name>.py` with `check(tree) -> list[Finding]` (or point
`cmd` at an external tool), add one `Gate(...)` below, add its tests in tests/quality/.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

from quality.core import Finding, Tree
from quality.gates import (
    docs,
    duplication,
    hygiene,
    layers,
    magic,
    scope,
    secrets,
    size,
    suppressions,
)
from quality.limits import COVERAGE_FLOOR, COVERED_PACKAGES, PYTHON_DIRS, SOURCE_DIRS

PRE_COMMIT, CI, SCHEDULED = "pre-commit", "ci", "scheduled"
STAGES = (PRE_COMMIT, CI, SCHEDULED)
FAST = (PRE_COMMIT, CI)  # fast gates run on every commit and again in CI
PYTHON = sys.executable


@dataclass(frozen=True)
class Gate:
    id: str
    rule: str  # section of CODING_GUIDELINES.md this gate enforces
    stages: tuple[str, ...]
    check: Callable[[Tree], list[Finding]] | None = None  # in-process gate ...
    cmd: tuple[str, ...] = ()  # ... or an external tool
    fix: tuple[str, ...] = ()  # command that repairs what `cmd` reports
    ratchet: bool = False  # known debt in quality/baselines/<id>.json, may only shrink
    advisory: bool = False  # reported, never fails the run


def tool(module: str, *args: str) -> tuple[str, ...]:
    return (PYTHON, "-m", module, *args)


GATES = (
    # ---- format: one style, no discussion
    Gate(
        "format",
        "Style",
        FAST,
        cmd=tool("black", "--check", *PYTHON_DIRS),
        fix=tool("black", *PYTHON_DIRS),
    ),
    Gate(
        "import-order",
        "Style",
        FAST,
        cmd=tool("isort", "--check-only", *PYTHON_DIRS),
        fix=tool("isort", *PYTHON_DIRS),
    ),
    # ---- architecture: modular, predictable structure
    Gate("layers", "Structure", FAST, check=layers.check),
    Gate("gate-scope", "Structure", FAST, check=scope.check),
    Gate("docs-links", "Structure", FAST, check=docs.check),
    Gate("repo-hygiene", "Structure", FAST, check=hygiene.check),
    # ---- clean code: named values, small functions, honest suppressions
    Gate("magic-values", "Named values", FAST, check=magic.check, ratchet=True),
    Gate("size", "Small and simple", FAST, check=size.check, ratchet=True),
    Gate("duplication", "No duplication", (CI,), check=duplication.check, ratchet=True),
    Gate("suppressions-named", "Honest suppressions", FAST, check=suppressions.blanket),
    Gate(
        "suppressions-budget",
        "Honest suppressions",
        FAST,
        check=suppressions.budget,
        ratchet=True,
    ),
    # ---- security
    Gate("secrets", "Security", FAST, check=secrets.check),
    Gate(
        "bandit", "Security", (CI,), cmd=tool("bandit", "-q", "-ll", "-r", *SOURCE_DIRS)
    ),
    # ---- analysis that needs a few seconds
    Gate(
        "lint",
        "Clean code",
        (CI,),
        cmd=tool("pylint", "--disable=duplicate-code", *SOURCE_DIRS),
    ),
    Gate(
        "types",
        "Typed",
        (CI,),
        cmd=tool("mypy", *(d for d in SOURCE_DIRS if d not in ("tools", "examples"))),
    ),
    Gate(
        "dead-code",
        "Minimal",
        (CI,),
        cmd=tool("vulture", *SOURCE_DIRS, "--min-confidence", "90"),
    ),
    # ---- behaviour
    Gate(
        "tests",
        "Tested",
        (CI,),
        cmd=tool(
            "pytest",
            "-q",
            *(f"--cov={p}" for p in COVERED_PACKAGES),
            "--cov-report=term-missing:skip-covered",
            "--cov-report=xml",
            f"--cov-fail-under={COVERAGE_FLOOR}",
        ),
    ),  # fmt: skip
    # ---- scheduled: depends on the outside world, so it must not block a commit
    Gate(
        "dependency-audit",
        "Security",
        (SCHEDULED,),
        cmd=tool("pip_audit", "-r", "requirements.txt", "-r", "requirements-gui.txt"),
        advisory=True,
    ),
)

BY_ID = {gate.id: gate for gate in GATES}
