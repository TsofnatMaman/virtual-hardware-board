"""Building blocks shared by all gates: findings, the file tree, and ratchets."""

from __future__ import annotations

import ast
import fnmatch
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINES = Path(__file__).resolve().parent / "baselines"
ENCODING = "utf-8"
SKIPPED_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache"}


@dataclass(frozen=True)
class Finding:
    """One rule violation. `key` groups findings for ratchets; `value` weights them."""

    path: str
    line: int
    message: str
    key: str = ""
    value: int = 1

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


class Tree:
    """The files a gate looks at: what git tracks or would track (new files that are
    not ignored), or any directory (for tests)."""

    def __init__(self, root: Path, files: list[str]):
        self.root, self.files = root, sorted(files)

    @classmethod
    def from_git(cls, root: Path = ROOT) -> Tree:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return cls(root, [f for f in out.split("\0") if f and (root / f).exists()])

    @classmethod
    def from_dir(cls, root: Path) -> Tree:
        found = (
            p
            for p in root.rglob("*")
            if p.is_file() and not SKIPPED_DIRS & set(p.parts)
        )
        return cls(root, [p.relative_to(root).as_posix() for p in found])

    def read(self, path: str) -> str:
        return (self.root / path).read_text(encoding=ENCODING, errors="replace")

    def match(self, *globs: str) -> list[str]:
        return [f for f in self.files if any(fnmatch.fnmatch(f, g) for g in globs)]

    def python(self, dirs: tuple[str, ...]) -> list[str]:
        return [f for f in self.files if f.endswith(".py") and f.split("/")[0] in dirs]

    def parse(self, path: str) -> ast.Module:
        return ast.parse(self.read(path), filename=path)


def totals(findings: list[Finding]) -> dict[str, int]:
    """Sum finding values per key (what a ratchet compares)."""
    result: dict[str, int] = {}
    for finding in findings:
        result[finding.key] = result.get(finding.key, 0) + finding.value
    return result


class Ratchet:
    """Known debt per key that may only go down. Not-yet-fixed old code is listed in a
    baseline file; new code starts at zero."""

    def __init__(self, gate_id: str, directory: Path = BASELINES):
        self.path = directory / f"{gate_id}.json"

    def load(self) -> dict[str, int]:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def violations(self, current: dict[str, int], strict: bool = False) -> list[str]:
        """Keys above their baseline; with `strict`, also keys the baseline could drop."""
        base = self.load()
        grown = [
            f"{k}: {v} (allowed {base.get(k, 0)})"
            for k, v in sorted(current.items())
            if v > base.get(k, 0)
        ]
        stale = [
            f"{k}: baseline {v} can be lowered to {current.get(k, 0)}"
            for k, v in sorted(base.items())
            if current.get(k, 0) < v
        ]
        return grown + (stale if strict else [])

    def write(self, current: dict[str, int], allow_growth: bool = False) -> None:
        if not allow_growth and (grown := self.violations(current)):
            raise SystemExit(
                f"refusing to grow {self.path.name}:\n  " + "\n  ".join(grown)
            )
        self.path.write_text(json.dumps(dict(sorted(current.items())), indent=2) + "\n")
