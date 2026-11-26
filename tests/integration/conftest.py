"""Fixtures for tests that build real firmware with arm-none-eabi-gcc."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from toolchain import TEMPLATE, WARNINGS_ARE_ERRORS  # noqa: E402


@pytest.fixture(name="build_project")
def fixture_build_project(tmp_path_factory):
    """Copy the C template, optionally replace src/main.c, build for a board.

    Returns (elf_path, bin_path).
    """
    counter = {"n": 0}

    def build(board: str, main_c: str | None = None):
        counter["n"] += 1
        proj = tmp_path_factory.mktemp(f"proj{counter['n']}") / "project"
        shutil.copytree(TEMPLATE, proj)
        if main_c is not None:
            (proj / "src" / "main.c").write_text(main_c, encoding="utf-8")
        result = subprocess.run(
            ["make", f"BOARD={board}", f"EXTRA_CFLAGS={WARNINGS_ARE_ERRORS}"],
            cwd=proj,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return proj / "build" / "app.elf", proj / "build" / "app.bin"

    return build
