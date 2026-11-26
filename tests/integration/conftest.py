"""Fixtures for tests that build real firmware with arm-none-eabi-gcc."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "c_project"

HAVE_TOOLCHAIN = bool(shutil.which("arm-none-eabi-gcc") and shutil.which("make"))
needs_toolchain = pytest.mark.skipif(
    not HAVE_TOOLCHAIN, reason="arm-none-eabi-gcc/make not installed"
)
GDB = shutil.which("gdb-multiarch") or shutil.which("arm-none-eabi-gdb")

# CI sets REQUIRE_FULL_TEST_ENV=1 so a missing tool fails the run instead of skipping tests.
if os.environ.get("REQUIRE_FULL_TEST_ENV") and not (HAVE_TOOLCHAIN and GDB):
    raise RuntimeError(
        "REQUIRE_FULL_TEST_ENV is set but arm-none-eabi-gcc, make or gdb is missing"
    )
needs_gdb = pytest.mark.skipif(
    GDB is None, reason="gdb-multiarch / arm-none-eabi-gdb not installed"
)


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
            ["make", f"BOARD={board}"],
            cwd=proj,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return proj / "build" / "app.elf", proj / "build" / "app.bin"

    return build


def load_and_reset(board, bin_path: Path) -> None:
    board.address_space.flash.load_image(bin_path.read_bytes())
    board.reset()


def watch_register(board, address: int, steps: int, size: int = 4) -> list[int]:
    """Step the CPU and return the distinct consecutive values of a register."""
    seen: list[int] = []
    for _ in range(steps):
        board.step(1)
        value = board.read(address, size)
        if not seen or seen[-1] != value:
            seen.append(value)
    return seen
