"""Findings, the file tree and ratchets."""

import json

import pytest

from quality.core import Finding, Ratchet, Tree, totals
from tests.quality.conftest import git


def test_totals_sum_values_per_key():
    found = [
        Finding("a.py", 1, "x", "a", 2),
        Finding("a.py", 5, "y", "a", 3),
        Finding("b.py", 1, "z", "b"),
    ]
    assert totals(found) == {"a": 5, "b": 1}


def test_tree_from_dir_lists_files_but_skips_caches(make_tree, tmp_path):
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"")
    tree = make_tree({"pkg/a.py": "x = 1", "pkg/b.md": "# t", "tests/t.py": "y = 2"})
    assert tree.files == ["pkg/a.py", "pkg/b.md", "tests/t.py"]
    assert tree.python(("pkg",)) == ["pkg/a.py"]
    assert tree.match("*.md") == ["pkg/b.md"]
    assert tree.read("pkg/a.py") == "x = 1"


def test_tree_from_git_lists_tracked_and_new_files_but_not_ignored_ones(git_repo):
    (git_repo / ".gitignore").write_text("*.log\n")
    for name in ("tracked.py", "new.py", "debug.log"):
        (git_repo / name).write_text("x = 1")
    git(git_repo, "add", "tracked.py")
    assert Tree.from_git(git_repo).files == [".gitignore", "new.py", "tracked.py"]


class TestRatchet:
    def test_new_debt_fails_and_known_debt_passes(self, tmp_path):
        ratchet = Ratchet("g", tmp_path)
        (tmp_path / "g.json").write_text(json.dumps({"old.py": 3}))
        assert ratchet.violations({"old.py": 3}) == []
        assert ratchet.violations({"old.py": 2}) == []
        assert ratchet.violations({"old.py": 4}) == ["old.py: 4 (allowed 3)"]
        assert ratchet.violations({"new.py": 1}) == ["new.py: 1 (allowed 0)"]

    def test_strict_mode_asks_for_the_baseline_to_be_lowered(self, tmp_path):
        ratchet = Ratchet("g", tmp_path)
        (tmp_path / "g.json").write_text(json.dumps({"a": 3, "gone": 1}))
        assert ratchet.violations({"a": 1}, strict=True) == [
            "a: baseline 3 can be lowered to 1",
            "gone: baseline 1 can be lowered to 0",
        ]

    def test_write_refuses_growth_unless_allowed(self, tmp_path):
        ratchet = Ratchet("g", tmp_path)
        with pytest.raises(SystemExit, match="refusing to grow"):
            ratchet.write({"a": 1})
        ratchet.write({"b": 2, "a": 1}, allow_growth=True)
        assert json.loads((tmp_path / "g.json").read_text()) == {"a": 1, "b": 2}
        ratchet.write({"a": 1})  # shrinking is always allowed
        assert ratchet.load() == {"a": 1}

    def test_missing_baseline_means_zero_debt(self, tmp_path):
        assert Ratchet("none", tmp_path).load() == {}
