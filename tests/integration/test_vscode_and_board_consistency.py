"""Adding a board touches many files; these tests fail if one of them is forgotten."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from simulator import list_available_boards, verify_boards_registered

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "c_project"

pytestmark = pytest.mark.integration


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _boards():
    verify_boards_registered()
    return sorted(list_available_boards())


# ------------------------------------------------------------------ the C template
@pytest.mark.parametrize("board", _boards())
class TestEveryBoardIsSupportedByTheTemplate:
    def test_board_files_exist(self, board):
        folder = TEMPLATE / "board" / board
        assert (
            folder / "linker.ld"
        ).is_file(), f"templates/c_project/board/{board}/linker.ld"  # nosec B101
        assert list(
            folder.glob("*.h")
        ), f"a register header in templates/c_project/board/{board}/"  # nosec B101

    def test_makefile_knows_the_board(self, board):
        text = (TEMPLATE / "Makefile").read_text(encoding="utf-8")
        assert re.search(
            rf"\$\(BOARD\),{board}\)", text
        ), f"templates/c_project/Makefile has no branch for {board}"  # nosec B101
        assert (
            board in text.split("$(error")[1]
        ), "the error message should list the board"  # nosec B101

    def test_build_task_and_debug_configuration_exist(self, board):
        tasks = {
            t["label"]: t for t in _load(TEMPLATE / ".vscode" / "tasks.json")["tasks"]
        }
        label = f"build ({board})"
        assert label in tasks, f"template tasks.json needs '{label}'"  # nosec B101
        assert f"BOARD={board}" in tasks[label]["command"]  # nosec B101
        launches = [
            c
            for c in _load(TEMPLATE / ".vscode" / "launch.json")["configurations"]
            if c.get("preLaunchTask") == label
        ]
        assert (
            len(launches) == 1
        ), f"template launch.json needs one configuration with preLaunchTask '{label}'"  # nosec B101

    def test_firmware_folder_and_makefile(self, board):
        assert (
            ROOT / "firmware" / "boards" / board / "linker.ld"
        ).is_file()  # nosec B101
        assert f"$(BOARD),{board})" in (ROOT / "firmware" / "Makefile").read_text(
            encoding="utf-8"
        )  # nosec B101

    def test_gui_layout_exists(self, board):
        assert (
            ROOT / "simulator_gui" / "boards" / f"{board}.yaml"
        ).is_file()  # nosec B101


@pytest.mark.parametrize(
    "base", [TEMPLATE / ".vscode", ROOT / ".vscode"], ids=["template", "repo"]
)
class TestVsCodeFilesAreInternallyConsistent:
    def test_json_is_valid(self, base):
        for name in ("launch.json", "tasks.json"):
            _load(base / name)

    def test_every_pre_launch_task_exists(self, base):
        labels = {t["label"] for t in _load(base / "tasks.json")["tasks"]}
        for cfg in _load(base / "launch.json")["configurations"]:
            for key in ("preLaunchTask", "postDebugTask"):
                if key in cfg:
                    assert (
                        cfg[key] in labels
                    ), f"{cfg['name']}: unknown task '{cfg[key]}'"  # nosec B101

    def test_task_dependencies_exist(self, base):
        tasks = _load(base / "tasks.json")["tasks"]
        labels = {t["label"] for t in tasks}
        for task in tasks:
            for dep in task.get("dependsOn", []):
                assert (
                    dep in labels
                ), f"{task['label']} depends on unknown '{dep}'"  # nosec B101

    def test_debug_configurations_use_the_default_port(self, base):
        for cfg in _load(base / "launch.json")["configurations"]:
            assert cfg["servertype"] == "external"  # nosec B101
            assert cfg["gdbTarget"] == "127.0.0.1:3333", cfg["name"]  # nosec B101


def test_repo_tasks_start_the_simulator_on_the_port_the_launch_files_expect():
    tasks = _load(ROOT / ".vscode" / "tasks.json")["tasks"]
    starts = [t for t in tasks if t["label"].startswith("sim: start")]
    assert starts, "no 'sim: start' tasks"  # nosec B101
    for task in starts:
        assert "3333" in task["command"], task["label"]  # nosec B101


def test_repo_launch_executables_match_the_build_outputs():
    tasks = {t["label"]: t for t in _load(ROOT / ".vscode" / "tasks.json")["tasks"]}
    for cfg in _load(ROOT / ".vscode" / "launch.json")["configurations"]:
        elf = Path(cfg["executable"]).name  # e.g. tm4c123.elf
        outputs = " ".join(t.get("command", "") for t in tasks.values())
        assert (
            elf.replace(".elf", ".bin") in outputs
        ), f"{cfg['name']}: no build task writes {elf}"  # nosec B101


def test_readme_documents_the_board_checklist():
    text = (TEMPLATE / "README.md").read_text(encoding="utf-8")
    assert (
        "gdbTarget" in text and "--gdb-port" in text and "Adding another board" in text
    )  # nosec B101
