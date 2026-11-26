"""Every gate fails on a planted violation and stays quiet on clean code."""

from __future__ import annotations

import subprocess

import pytest

from quality.core import Tree, totals
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
from tests.quality.conftest import git


def keys(findings):
    return sorted({f.key for f in findings})


# ------------------------------------------------------------------ layers
class TestLayers:
    def test_core_must_not_import_a_board(self, make_tree):
        tree = make_tree(
            {"simulator/core/engine.py": "from simulator.tm4c import board\n"}
        )
        assert keys(layers.check(tree)) == ["core->board:tm4c"]

    def test_allowed_and_shared_imports_pass(self, make_tree):
        tree = make_tree({
            "simulator/core/engine.py": "from simulator.interfaces import cpu\nfrom simulator.core.exceptions import X\n",
            "simulator/interfaces/cpu.py": "from simulator.core.gpio_enums import PinLevel\n",
            "simulator/stm32c031/board.py": "from simulator.stm32 import gpio\nfrom simulator.core import cpu\n",
            "simulator/__init__.py": "from simulator.tm4c import board\n",
        })  # fmt: skip
        assert layers.check(tree) == []

    def test_boards_must_not_import_each_other_except_a_base_family(self, make_tree):
        tree = make_tree(
            {"simulator/stm32/board.py": "from simulator.tm4c import gpio\n"}
        )
        assert keys(layers.check(tree)) == ["board:stm32->board:tm4c"]

    def test_type_checking_imports_are_not_dependencies(self, make_tree):
        src = "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from simulator.core.memmap import AddressSpace\n"
        assert layers.check(make_tree({"simulator/interfaces/board.py": src})) == []

    def test_a_runtime_upward_import_is_reported_with_its_line(self, make_tree):
        finding = layers.check(
            make_tree(
                {
                    "simulator/interfaces/board.py": "import os\nfrom simulator.core.memmap import AddressSpace\n"
                }
            )
        )[0]
        assert (finding.path, finding.line) == ("simulator/interfaces/board.py", 2)

    def test_nothing_may_import_the_gui_below_the_api(self, make_tree):
        assert keys(
            layers.check(
                make_tree({"simulator/debug/server.py": "import simulator_gui.app\n"})
            )
        ) == ["debug->gui"]

    def test_relative_imports_are_resolved(self, make_tree):
        tree = make_tree(
            {
                "simulator/core/a.py": "from ..tm4c import x\n",
                "simulator/tm4c/__init__.py": "",
            }
        )
        assert keys(layers.check(tree)) == ["core->board:tm4c"]

    def test_import_cycles_are_reported(self, make_tree):
        tree = make_tree(
            {
                "simulator/core/a.py": "from simulator.core import b\n",
                "simulator/core/b.py": "from simulator.core import a\n",
            }
        )
        assert any("import cycle" in f.message for f in layers.check(tree))

    def test_unknown_layer_names_are_not_resolved(self):
        assert layers.layer_of("yaml") is None
        assert layers.layer_of("simulator.stm32c031.board") == "board:stm32c031"
        assert layers.layer_of("simulator.stm32.gpio") == "board:stm32"
        assert layers.layer_of("simulator.core.gpio_enums") == "shared"


# ------------------------------------------------------------------ hygiene
class TestHygiene:
    def test_gitlink_forbidden_artifacts_binaries_and_big_files(
        self, git_repo, monkeypatch
    ):
        (git_repo / "ok.py").write_text("x = 1\n")
        (git_repo / "app.elf").write_bytes(b"\x7fELF")
        (git_repo / "mystery.bin").write_bytes(b"\0")
        (git_repo / "huge.txt").write_bytes(b"x" * 600_000)
        git(git_repo, "add", "-f", ".")
        git(
            git_repo,
            "update-index",
            "--add",
            "--cacheinfo",
            "160000,2977346e6c458a345976688844740704860a83b9,vendor/sub",
        )
        messages = {f.path: f.message for f in hygiene.check(Tree.from_git(git_repo))}
        assert "gitlink" in messages["vendor/sub"]
        assert "build output" in messages["app.elf"]
        assert "ALLOWED_BINARIES" in messages["mystery.bin"]
        assert "MAX_FILE_BYTES" in messages["huge.txt"]
        assert "ok.py" not in messages

    def test_allowed_binary_passes(self, git_repo):
        (git_repo / "firmware/led_blink/tm4c").mkdir(parents=True)
        (git_repo / "firmware/led_blink/tm4c/firmware.bin").write_bytes(b"\0")
        git(git_repo, "add", ".")
        assert hygiene.check(Tree.from_git(git_repo)) == []

    def test_listed_large_file_passes(self, git_repo):
        (git_repo / "docs").mkdir()
        (git_repo / "docs/tutorial.mp4").write_bytes(b"x" * 600_000)
        git(git_repo, "add", ".")
        assert hygiene.check(Tree.from_git(git_repo)) == []


# ------------------------------------------------------------------ clean code
class TestMagicValues:
    def test_inline_numbers_are_flagged_but_names_defaults_and_small_ints_are_not(
        self, make_tree
    ):
        src = (
            "LIMIT = 4096\n"
            "class C:\n    SIZE = 64\n"
            "def f(x, retries=5):\n    y = x * 1 + 2 - 0\n    return y + 4096 + 0x1F\n"
        )
        found = magic.check(make_tree({"simulator/m.py": src}))
        assert sorted(f.line for f in found) == [6, 6]
        assert {f.key for f in found} == {"simulator/m.py"}

    def test_f_strings_docstrings_and_dunders_are_ignored(self, make_tree):
        src = '"""Module docs mention 12345."""\ndef f(a):\n    """Docstring."""\n    return f"value {a} here" + f"value {a} here" + __name__ == "__main__"\n'
        assert magic.check(make_tree({"simulator/m.py": src})) == []

    def test_a_string_written_inline_three_times_must_be_named(self, make_tree):
        tree = make_tree({
            "simulator/a.py": "def f():\n    return 'board-name'\n",
            "simulator/b.py": "def f():\n    return 'board-name'\n",
            "simulator/c.py": "def f():\n    return 'board-name' + 'rare-value'\n",
        })  # fmt: skip
        assert keys(magic.check(tree)) == ["string:board-name"]

    def test_two_uses_or_a_named_constant_are_fine(self, make_tree):
        tree = make_tree(
            {
                "simulator/a.py": "NAME = 'board-name'\ndef f():\n    return 'board-name'\n",
                "simulator/b.py": "x = 'board-name'\n",
            }
        )
        assert magic.check(tree) == []

    def test_tests_are_not_checked(self, make_tree):
        assert magic.check(make_tree({"tests/t.py": "assert x == 12345\n"})) == []


class TestSize:
    def test_long_functions_many_params_complexity_and_big_files(self, make_tree):
        body = "\n".join(f"    v{i} = {i}" for i in range(60))
        branches = "\n".join(f"    if a == {i}:\n        return {i}" for i in range(12))
        src = f"def long():\n{body}\n\ndef wide(a, b, c, d, e, f, g, h):\n    pass\n\ndef complex(a):\n{branches}\n"
        found = {
            f.key: f.value
            for f in size.check(make_tree({"simulator/m.py": src + "x = 1\n" * 500}))
        }
        assert found["simulator/m.py::long:lines"] == 61
        assert found["simulator/m.py::wide:params"] == 8
        assert found["simulator/m.py::complex:complexity"] == 13
        assert found["simulator/m.py:file-lines"] > 500

    def test_small_code_passes(self, make_tree):
        assert (
            size.check(make_tree({"simulator/m.py": "def f(a):\n    return a\n"})) == []
        )


class TestSuppressions:
    def test_blanket_suppressions_are_rejected(self, make_tree):
        src = "a = 1  # noqa\nb = 2  # type: ignore\nc = 3  # noqa: E501\nd = 4  # type: ignore[attr-defined]\ne = 5  # pylint: disable=unused-import\n"
        found = suppressions.blanket(make_tree({"simulator/m.py": src}))
        assert sorted(f.line for f in found) == [1, 2]

    def test_budget_counts_every_suppression_per_file_and_skips_tests(self, make_tree):
        tree = make_tree(
            {
                "simulator/m.py": "a = 1  # noqa: E501\nb = 2  # nosec B101\n",
                "tests/t.py": "a = 1  # nosec B101\n",
            }
        )
        assert totals(suppressions.budget(tree)) == {"simulator/m.py": 2}


# ------------------------------------------------------------------ docs, secrets, scope
class TestDocs:
    def test_broken_links_and_paths_are_reported(self, make_tree):
        tree = make_tree({
            "README.md": "See [guide](docs/guide.md) and [missing](docs/nope.md) and `src/real.py` and `src/gone.py`.\n",
            "docs/guide.md": "Back to [readme](../README.md#top).\n",
            "src/real.py": "",
        })  # fmt: skip
        assert sorted(f.message for f in docs.check(tree)) == [
            "'docs/nope.md' does not exist",
            "'src/gone.py' does not exist",
        ]

    def test_placeholders_urls_and_build_outputs_are_not_checked(self, make_tree):
        text = "[site](https://example.com) `src/<name>/x.py` `src/*.py` `src/app.elf` `build/out.bin` `src/real.py`\n"
        assert docs.check(make_tree({"README.md": text, "src/real.py": ""})) == []


class TestSecrets:
    def test_tokens_and_hard_coded_secrets_are_found(self, make_tree):
        github = "gh" + "p_" + "A" * 36
        aws = "AKIA" + "B" * 16
        key = "-----BEGIN " + "RSA PRIVATE KEY-----"
        hard = "api_key = '" + "x" * 20 + "'"
        tree = make_tree(
            {
                "cfg.py": f"TOKEN = '{github}'\n{aws}\n{key}\n{hard}\n",
                "ok.py": "token = os.environ['T']\n",
            }
        )
        assert sorted((f.line, f.message) for f in secrets.check(tree)) == [
            (1, "possible GitHub token"),
            (2, "possible AWS access key"),
            (3, "possible private key"),
            (4, "possible hard-coded secret"),
        ]

    def test_clean_files_pass(self, make_tree):
        assert (
            secrets.check(
                make_tree({"a.py": "x = 'short'\n", "b.md": "no secrets here"})
            )
            == []
        )


def test_scope_reports_python_outside_the_checked_directories(make_tree):
    tree = make_tree(
        {"simulator/a.py": "", "tests/t.py": "", "scripts/stray.py": "", "setup.py": ""}
    )
    assert sorted(f.path for f in scope.check(tree)) == ["scripts/stray.py", "setup.py"]


class TestDuplication:
    def test_copy_pasted_blocks_are_reported(self, make_tree, monkeypatch):
        block = "".join(
            f"    value_{i} = compute({i}) + helper({i})\n" for i in range(12)
        )
        tree = make_tree(
            {
                "simulator/a.py": f"def first():\n{block}",
                "simulator/b.py": f"def second():\n{block}",
            }
        )
        monkeypatch.setattr(duplication, "SOURCE_DIRS", ("simulator",))
        found = duplication.check(tree)
        assert found and found[0].key == "a & b" and found[0].value >= 8

    def test_unrelated_code_passes(self, make_tree, monkeypatch):
        monkeypatch.setattr(duplication, "SOURCE_DIRS", ("simulator",))
        assert (
            duplication.check(
                make_tree(
                    {"simulator/a.py": "x = 1\n", "simulator/b.py": "y = 'other'\n"}
                )
            )
            == []
        )


def test_pylint_output_without_findings_is_an_empty_list(make_tree, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="", stderr=""),
    )
    assert duplication.check(make_tree({"simulator/a.py": ""})) == []


@pytest.mark.parametrize(
    "module",
    [
        "layers",
        "hygiene",
        "magic",
        "size",
        "suppressions",
        "docs",
        "secrets",
        "scope",
        "duplication",
    ],
)
def test_every_gate_module_has_a_docstring_stating_its_rule(module):
    import importlib

    assert importlib.import_module(f"quality.gates.{module}").__doc__
