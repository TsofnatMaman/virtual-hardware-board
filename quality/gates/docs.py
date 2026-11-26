"""Documentation points at things that exist: Markdown links and `repo/paths` resolve."""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import PurePosixPath

from quality.core import Finding, Tree
from quality.limits import DOC_IGNORED_PREFIXES, DOC_SUFFIXES, FORBIDDEN_TRACKED

LINK = re.compile(r"\]\(([^)\s#]+)(?:#[^)]*)?\)")
CODE_PATH = re.compile(r"`([\w.-]+(?:/[\w.-]+)+/?)`")
PLACEHOLDER = re.compile(r"[<>*{}$]|://|^mailto:")
REPO_ROOT = PurePosixPath(".")


def _is_skipped(target: str) -> bool:
    """URLs, placeholders and files the build creates (never tracked) are not checked."""
    return bool(
        PLACEHOLDER.search(target)
        or target.startswith(DOC_IGNORED_PREFIXES)
        or any(fnmatch(target, pattern) for pattern in FORBIDDEN_TRACKED)
    )


def _normalise(anchor: PurePosixPath, target: str) -> str:
    """`anchor/target` without `.` and `..` parts."""
    parts: list[str] = []
    for part in (anchor / target).as_posix().split("/"):
        if part == "..":
            parts = parts[:-1]
        elif part not in ("", "."):
            parts.append(part)
    return "/".join(parts)


def _targets(
    line: str, base: PurePosixPath, roots: set[str]
) -> list[tuple[str, PurePosixPath]]:
    """(target, directory it is relative to) for every link and repo path on a line."""
    links = [(target, base) for target in LINK.findall(line)]
    paths = [
        (t, REPO_ROOT) for t in CODE_PATH.findall(line) if t.split("/")[0] in roots
    ]
    return links + paths


def _known_paths(tree: Tree) -> set[str]:
    dirs = {
        "/".join(f.split("/")[:i])
        for f in tree.files
        for i in range(1, f.count("/") + 1)
    }
    return set(tree.files) | dirs | {""}


def check(tree: Tree) -> list[Finding]:
    known = _known_paths(tree)
    roots = {f.split("/")[0] for f in tree.files if "/" in f}
    findings = []
    for doc in (f for f in tree.files if f.endswith(DOC_SUFFIXES)):
        base = PurePosixPath(doc).parent
        for number, line in enumerate(tree.read(doc).splitlines(), 1):
            for target, anchor in _targets(line, base, roots):
                if (
                    not _is_skipped(target)
                    and _normalise(anchor, target.rstrip("/")) not in known
                ):
                    findings.append(Finding(doc, number, f"'{target}' does not exist"))
    return findings
