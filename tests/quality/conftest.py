"""Helpers: build a throw-away repository tree to plant violations in."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from quality.core import Tree


@pytest.fixture(name="make_tree")
def fixture_make_tree(tmp_path):
    def make(files: dict[str, str | bytes]) -> Tree:
        for name, content in files.items():
            target = tmp_path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                content if isinstance(content, bytes) else content.encode()
            )
        return Tree.from_dir(tmp_path)

    return make


@pytest.fixture(name="git_repo")
def fixture_git_repo(tmp_path) -> Path:
    for cmd in (
        ["init", "-q"],
        ["config", "user.email", "t@t"],
        ["config", "user.name", "t"],
    ):
        subprocess.run(["git", *cmd], cwd=tmp_path, check=True)
    return tmp_path


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout
