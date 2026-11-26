"""Shared fixtures for the GUI tests (run headless with Qt's offscreen platform)."""

from __future__ import annotations

import os
import struct

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

try:  # the GUI is an optional dependency
    import PySide6  # noqa: F401  # pylint: disable=unused-import
except ImportError:  # pragma: no cover - only without requirements-gui.txt
    if os.environ.get("REQUIRE_FULL_TEST_ENV"):
        raise
    collect_ignore_glob = ["test_*.py"]


@pytest.fixture(scope="session", name="qapp")
def fixture_qapp():
    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def boot_image(board) -> bytes:
    """Smallest valid image: initial SP, a Thumb reset vector, then NOPs."""
    base = board.address_space.flash.base
    sp = board.address_space.sram.base + 0x1000
    return struct.pack("<II", sp, base + 8 + 1) + b"\x00" * 64  # 0x0000 = movs r0, r0


@pytest.fixture(name="booted_board")
def fixture_booted_board():
    from simulator import create_board

    def make(key: str = "tm4c123"):
        board = create_board(key)
        board.address_space.flash.load_image(boot_image(board))
        board.reset()
        return board

    return make


@pytest.fixture(name="make_boot_image")
def fixture_make_boot_image():
    return boot_image
