"""Paths, tool detection and helpers shared by the integration tests."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "c_project"

WARNINGS_ARE_ERRORS = "-Werror"  # firmware must compile without a single warning
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
