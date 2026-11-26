"""The registry is consistent, the guidelines name every rule, and the runner behaves."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest

from quality import registry, run
from quality.core import BASELINES, ROOT, Finding, Tree
from quality.registry import CI, FAST, PRE_COMMIT, SCHEDULED, STAGES, Gate
from tests.quality.conftest import git

GATE_MODULES = sorted(
    p.stem for p in (ROOT / "quality" / "gates").glob("*.py") if p.stem != "__init__"
)


class TestRegistry:
    def test_ids_are_unique_and_stages_known(self):
        ids = [g.id for g in registry.GATES]
        assert len(ids) == len(set(ids))
        assert all(set(g.stages) <= set(STAGES) for g in registry.GATES)

    def test_each_gate_has_exactly_one_way_to_run(self):
        for gate in registry.GATES:
            assert bool(gate.check) != bool(gate.cmd), gate.id
            assert not gate.fix or gate.cmd, f"{gate.id}: fix without cmd"

    def test_pre_commit_gates_are_in_process_or_formatters(self):
        """Only quick gates may run on every commit."""
        slow = {
            "lint",
            "types",
            "tests",
            "bandit",
            "dead-code",
            "duplication",
            "dependency-audit",
        }
        assert not {g.id for g in registry.GATES if PRE_COMMIT in g.stages} & slow

    def test_ratchet_gates_and_baseline_files_match_one_to_one(self):
        ratcheted = {g.id for g in registry.GATES if g.ratchet}
        on_disk = {p.stem for p in BASELINES.glob("*.json")}
        assert ratcheted == on_disk

    def test_every_gate_module_is_registered_exactly_by_its_check(self):
        used = {
            g.check.__module__.rsplit(".", 1)[-1] for g in registry.GATES if g.check
        }
        assert used == set(GATE_MODULES)

    def test_every_rule_is_defined_in_the_coding_guidelines(self):
        guidelines = (ROOT / "CODING_GUIDELINES.md").read_text(encoding="utf-8")
        headings = set(re.findall(r"^#{2,3} (.+)$", guidelines, re.M))
        assert {g.rule for g in registry.GATES} <= headings

    def test_every_gate_is_documented_in_the_quality_gates_page(self):
        page = (ROOT / "docs" / "quality-gates.md").read_text(encoding="utf-8")
        assert [g.id for g in registry.GATES if f"`{g.id}`" not in page] == []

    def test_stage_constants(self):
        assert set(FAST) == {PRE_COMMIT, CI} and SCHEDULED not in FAST


def args(**kw):
    base = dict(
        fix=False,
        strict=False,
        write_baselines=False,
        allow_growth=False,
        verbose=False,
    )
    return argparse.Namespace(**{**base, **kw})


class TestRunGate:
    def test_absolute_gate_reports_every_finding(self):
        gate = Gate("g", "r", (CI,), check=lambda t: [Finding("a.py", 3, "bad")])
        assert run.run_gate(gate, Tree(ROOT, []), args()) == ["a.py:3: bad"]
        assert (
            run.run_gate(
                Gate("g", "r", (CI,), check=lambda t: []), Tree(ROOT, []), args()
            )
            == []
        )

    def test_external_command_exit_code_decides(self):
        ok = Gate("g", "r", (CI,), cmd=("true",))
        bad = Gate("g", "r", (CI,), cmd=("python3", "-c", "raise SystemExit(3)"))
        assert run.run_gate(ok, Tree(ROOT, []), args()) == []
        assert "exited with 3" in run.run_gate(bad, Tree(ROOT, []), args())[0]

    def test_fix_runs_the_repair_command_instead_of_the_check(self, tmp_path):
        marker = tmp_path / "fixed"
        gate = Gate("g", "r", (CI,), cmd=("false",), fix=("touch", str(marker)))
        assert run.run_gate(gate, Tree(ROOT, []), args(fix=True)) == []
        assert marker.exists()

    def test_ratchet_gate_allows_known_debt_and_rejects_growth(self, tmp_path):
        (tmp_path / "g.json").write_text(json.dumps({"a.py": 2}))
        gate = Gate(
            "g",
            "r",
            (CI,),
            check=lambda t: [Finding("a.py", 1, "x", "a.py", 2)],
            ratchet=True,
        )
        assert run.run_gate(gate, Tree(ROOT, []), args(), tmp_path) == []
        worse = Gate(
            "g",
            "r",
            (CI,),
            check=lambda t: [Finding("a.py", 1, "x", "a.py", 3)],
            ratchet=True,
        )
        assert run.run_gate(worse, Tree(ROOT, []), args(), tmp_path) == [
            "a.py: 3 (allowed 2)"
        ]

    def test_write_baselines_lowers_but_refuses_growth(self, tmp_path):
        gate = Gate(
            "g",
            "r",
            (CI,),
            check=lambda t: [Finding("a.py", 1, "x", "a.py")],
            ratchet=True,
        )
        with pytest.raises(SystemExit):
            run.run_gate(gate, Tree(ROOT, []), args(write_baselines=True), tmp_path)
        assert (
            run.run_gate(
                gate,
                Tree(ROOT, []),
                args(write_baselines=True, allow_growth=True),
                tmp_path,
            )
            == []
        )
        assert json.loads((tmp_path / "g.json").read_text()) == {"a.py": 1}

    def test_strict_mode_demands_a_lowered_baseline(self, tmp_path):
        (tmp_path / "g.json").write_text(json.dumps({"a.py": 5}))
        gate = Gate(
            "g",
            "r",
            (CI,),
            check=lambda t: [Finding("a.py", 1, "x", "a.py")],
            ratchet=True,
        )
        assert run.run_gate(gate, Tree(ROOT, []), args(), tmp_path) == []
        assert (
            "can be lowered"
            in run.run_gate(gate, Tree(ROOT, []), args(strict=True), tmp_path)[0]
        )


class TestMain:
    @pytest.fixture(autouse=True)
    def fake_registry(self, monkeypatch):
        gates = (
            Gate("pass", "r", FAST, check=lambda t: []),
            Gate("fail", "r", (CI,), check=lambda t: [Finding("x.py", 1, "broken")]),
            Gate(
                "late",
                "r",
                (SCHEDULED,),
                check=lambda t: [Finding("y.py", 1, "later")],
                advisory=True,
            ),
        )
        monkeypatch.setattr(run, "GATES", gates)
        monkeypatch.setattr(run, "BY_ID", {g.id: g for g in gates})
        monkeypatch.setattr(
            run.Tree, "from_git", classmethod(lambda cls: Tree(ROOT, []))
        )

    def test_ci_stage_fails_when_a_gate_fails(self, capsys):
        assert run.main(["--stage", "ci"]) == 1
        out = capsys.readouterr().out
        assert (
            "[OK] pass" in out
            and "[FAIL] fail" in out
            and "x.py:1: broken" in out
            and "1/2 gates passed" in out
        )

    def test_pre_commit_stage_runs_only_its_gates(self, capsys):
        assert run.main(["--stage", "pre-commit"]) == 0
        assert "fail" not in capsys.readouterr().out.replace("0 failed", "")

    def test_advisory_gates_never_fail_the_run(self, capsys):
        assert run.main(["--stage", "scheduled"]) == 0
        assert "[ADVISORY] late" in capsys.readouterr().out

    def test_only_selects_gates_and_rejects_unknown_ids(self, capsys):
        assert run.main(["--only", "pass"]) == 0
        with pytest.raises(SystemExit, match="unknown gate"):
            run.main(["--only", "nope"])

    def test_list_prints_every_gate(self, capsys):
        assert run.main(["--list"]) == 0
        assert capsys.readouterr().out.count("\n") == 3

    def test_long_reports_are_cut_unless_verbose(self, monkeypatch, capsys):
        many = Gate(
            "many",
            "r",
            (CI,),
            check=lambda t: [Finding("f.py", i, "bad") for i in range(40)],
        )
        monkeypatch.setattr(run, "GATES", (many,))
        monkeypatch.setattr(run, "BY_ID", {"many": many})
        run.main(["--only", "many"])
        assert capsys.readouterr().out.count("bad") == run.SHOWN
        run.main(["--only", "many", "--verbose"])
        assert capsys.readouterr().out.count("bad") == 40


class TestGrowthCheck:
    def make_repo(self, repo: Path, content: dict) -> Path:
        baselines = repo / "quality" / "baselines"
        baselines.mkdir(parents=True)
        (baselines / "g.json").write_text(json.dumps(content))
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "base")
        git(repo, "branch", "-M", "main")
        return baselines

    def test_growing_or_new_debt_is_reported(self, git_repo):
        baselines = self.make_repo(git_repo, {"a.py": 2, "b.py": 1})
        (baselines / "g.json").write_text(json.dumps({"a.py": 3, "b.py": 1, "c.py": 1}))
        assert run.growth("main", baselines, git_repo) == [
            "g.json: 'a.py' grew 2 -> 3",
            "g.json: 'c.py' grew 0 -> 1",
        ]

    def test_shrinking_and_brand_new_baselines_are_fine(self, git_repo):
        baselines = self.make_repo(git_repo, {"a.py": 2})
        (baselines / "g.json").write_text(json.dumps({"a.py": 1}))
        (baselines / "new.json").write_text(json.dumps({"x": 9}))
        assert run.growth("main", baselines, git_repo) == []

    def test_cli_flag_reports_the_result(self, monkeypatch, capsys):
        monkeypatch.setattr(run, "growth", lambda base: [])
        assert run.main(["--growth-check", "--base", "main"]) == 0
        monkeypatch.setattr(run, "growth", lambda base: ["g.json: 'a' grew 1 -> 2"])
        assert run.main(["--growth-check"]) == 1
