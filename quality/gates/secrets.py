"""No credentials in the repository."""

from __future__ import annotations

import re

from quality.core import Finding, Tree

PATTERNS = {
    "private key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"
    ),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "hard-coded secret": re.compile(
        r"(?i)(?:api[_-]?key|secret|token|passw(?:or)?d)\s*[:=]\s*['\"][A-Za-z0-9/+_-]{16,}['\"]"
    ),
}
TEXT_SUFFIXES = (
    ".py",
    ".md",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".txt",
    ".sh",
    ".ini",
    ".cfg",
    ".c",
    ".h",
    ".ld",
)


def check(tree: Tree) -> list[Finding]:
    findings = []
    for path in tree.match(*(f"*{s}" for s in TEXT_SUFFIXES)):
        for number, line in enumerate(tree.read(path).splitlines(), 1):
            if kind := next(
                (name for name, rx in PATTERNS.items() if rx.search(line)), None
            ):
                findings.append(Finding(path, number, f"possible {kind}"))
    return findings
