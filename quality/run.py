"""Run the quality gates.

    python -m quality.run                  # everything CI runs
    python -m quality.run --stage pre-commit
    python -m quality.run --only layers,size --verbose
    python -m quality.run --fix            # let formatters repair what they report
    python -m quality.run --write-baselines          # lower ratchets after fixing debt
    python -m quality.run --growth-check --base origin/main   # CI: baselines never grow
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from quality.core import BASELINES, ROOT, Finding, Ratchet, Tree, totals
from quality.registry import BY_ID, CI, GATES, STAGES, Gate

SHOWN = 15  # findings printed per gate unless --verbose
OK, FAIL, ADVISORY = "OK", "FAIL", "ADVISORY"
SWITCH: dict[str, Any] = {"action": "store_true"}  # an option without a value
FLAGS = (  # (flag, help): every on/off switch of the command line
    ("--list", "list the gates and exit"),
    ("--fix", "run the formatters instead of only checking"),
    ("--strict", "ratchets must also be lowered when debt was paid"),
    ("--write-baselines", "lower the ratchet baselines to the current debt"),
    ("--allow-growth", "with --write-baselines: accept more debt (new baselines only)"),
    ("--growth-check", "fail if a baseline is higher than on --base"),
    ("--verbose", "print every finding"),
)


def run_command(gate: Gate, args: argparse.Namespace) -> list[str]:
    cmd = gate.fix if args.fix and gate.fix else gate.cmd
    done = subprocess.run(cmd, cwd=ROOT, check=False)
    return (
        []
        if done.returncode == 0
        else [f"`{' '.join(cmd[2:])}` exited with {done.returncode}"]
    )


def run_check(
    gate: Gate,
    check: Callable[[Tree], list[Finding]],
    tree: Tree,
    args: argparse.Namespace,
    baselines: Path,
) -> list[str]:
    findings = check(tree)
    if not gate.ratchet:
        return [str(f) for f in findings]
    ratchet, current = Ratchet(gate.id, baselines), totals(findings)
    if args.write_baselines:
        ratchet.write(current, args.allow_growth)
        return []
    problems = ratchet.violations(current, strict=args.strict)
    example = next(
        (f for f in findings if current[f.key] > ratchet.load().get(f.key, 0)), None
    )
    return problems + ([f"  e.g. {example}"] if example and args.verbose else [])


def run_gate(
    gate: Gate, tree: Tree, args: argparse.Namespace, baselines: Path = BASELINES
) -> list[str]:
    """Problems found by one gate (empty = pass)."""
    if gate.cmd:
        return run_command(gate, args)
    if gate.check is None:
        raise ValueError(f"gate {gate.id} has neither a command nor a check")
    return run_check(gate, gate.check, tree, args, baselines)


def growth(base: str, baselines: Path = BASELINES, root: Path = ROOT) -> list[str]:
    """Baselines in this checkout must not be higher than they are on `base`."""
    problems = []
    for path in sorted(baselines.glob("*.json")):
        rel = path.relative_to(root).as_posix()
        shown = subprocess.run(
            ["git", "show", f"{base}:{rel}"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        if shown.returncode:
            continue  # new baseline: nothing to compare with
        old, new = json.loads(shown.stdout), json.loads(path.read_text())
        problems += [
            f"{path.name}: '{k}' grew {old.get(k, 0)} -> {v}"
            for k, v in new.items()
            if v > old.get(k, 0)
        ]
    return problems


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--stage", choices=STAGES, default=CI)
    p.add_argument("--only", help="comma separated gate ids")
    p.add_argument("--base", default="origin/main")
    for flag, text in FLAGS:
        p.add_argument(flag, help=text, **SWITCH)
    return p


def select(args: argparse.Namespace) -> list[Gate]:
    """The gates to run: the ones named by --only, else those of the stage."""
    if not args.only:
        return [g for g in GATES if args.stage in g.stages]
    wanted = set(args.only.split(","))
    if unknown := wanted - BY_ID.keys():
        raise SystemExit(f"unknown gate(s): {', '.join(sorted(unknown))}")
    return [g for g in GATES if g.id in wanted]


def report(gate: Gate, problems: list[str], verbose: bool) -> bool:
    """Print one gate's result; True when it counts as a failure."""
    status = OK if not problems else ADVISORY if gate.advisory else FAIL
    print(f"[{status}] {gate.id}")
    for problem in problems[: None if verbose else SHOWN]:
        print(f"    {problem}")
    return status == FAIL


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.list:
        print(
            *(f"{g.id:22s} {','.join(g.stages):22s} {g.rule}" for g in GATES), sep="\n"
        )
        return 0
    if args.growth_check:
        problems = growth(args.base)
        print(*problems or ["[OK] baselines did not grow"], sep="\n")
        return 1 if problems else 0
    selected, tree = select(args), Tree.from_git()
    failed = [
        g.id for g in selected if report(g, run_gate(g, tree, args), args.verbose)
    ]
    summary = f"{len(selected) - len(failed)}/{len(selected)} gates passed"
    print(f"\n{summary}" + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
