"""BoardBackend, SimulationController and the layout engine (no window needed)."""

from __future__ import annotations

import threading

import pytest

from simulator_gui import controller as controller_module
from simulator_gui.backend import BoardBackend
from simulator_gui.components.base import ComponentController
from simulator_gui.config import ComponentConfig, HardwareBinding, Rect
from simulator_gui.controller import (
    SimulationController,
    SimulationState,
    StatusSample,
    SystemMonitor,
)
from simulator_gui.layout import FlowLayoutEngine


class RecordingLock:
    """A context manager that records how often the backend takes the lock."""

    def __init__(self):
        self.entered = 0

    def __enter__(self):
        self.entered += 1

    def __exit__(self, *exc):
        return False


def test_backend_forwards_to_the_board_under_the_lock(booted_board):
    lock = RecordingLock()
    board = booted_board("tm4c123")
    backend = BoardBackend(board, lock=lock)
    assert backend.board_name == "TM4C123"  # nosec B101
    backend.write(0x20000100, 4, 0xCAFEBABE)
    assert backend.read(0x20000100, 4) == 0xCAFEBABE  # nosec B101
    backend.step(5)
    backend.reset()
    assert any(r.name == "PC" for r in backend.cpu_snapshot().registers)  # nosec B101
    assert lock.entered == 5  # nosec B101  (write, read, step, reset, snapshot)


def test_backend_with_a_real_lock_is_thread_safe(booted_board):
    # Without a lock the backend is single-threaded (the GUI timer); with a shared
    # RLock a debugger thread and the GUI can use the same board (see run_gui).
    backend = BoardBackend(booted_board("stm32f4"), lock=threading.RLock())
    errors = []

    def hammer():
        try:
            for _ in range(50):
                backend.step(2)
                backend.read(0x40020C14, 4)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(exc)

    threads = [threading.Thread(target=hammer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors  # nosec B101


class FakeComponent(ComponentController):
    def __init__(self):
        super().__init__("fake", HardwareBinding(address=0, mask=1))
        self.updates = 0

    def update(self, backend):
        self.updates += 1


def test_controller_state_machine(booted_board):
    ctrl = SimulationController(BoardBackend(booted_board()), [])
    assert ctrl.state == SimulationState.PAUSED  # nosec B101
    ctrl.set_running(True)
    assert ctrl.state == SimulationState.RUNNING  # nosec B101
    ctrl.set_running(False)
    assert ctrl.state == SimulationState.PAUSED  # nosec B101
    ctrl.set_external(True)
    assert ctrl.state == SimulationState.EXTERNAL  # nosec B101
    ctrl.set_external(False)
    assert ctrl.state == SimulationState.PAUSED  # nosec B101
    ctrl.set_running(True)
    ctrl.set_external(False)  # only leaves EXTERNAL, never overrides RUNNING
    assert ctrl.state == SimulationState.RUNNING  # nosec B101


def test_controller_steps_resets_and_updates_components(booted_board):
    board = booted_board()
    comp = FakeComponent()
    ctrl = SimulationController(BoardBackend(board), [comp])
    assert comp._backend is not None  # nosec B101  (attached)
    ctrl.step(3)
    ctrl.update_components()
    ctrl.update_components()
    assert comp.updates == 2  # nosec B101
    ctrl.reset()
    assert ctrl.snapshot().registers  # nosec B101
    assert isinstance(ctrl.status(), StatusSample)  # nosec B101


def test_system_monitor_without_psutil(monkeypatch):
    monkeypatch.setattr(controller_module, "psutil", None)
    sample = SystemMonitor().sample()
    assert (sample.cpu_percent, sample.memory_percent) == (None, None)  # nosec B101


def test_system_monitor_with_psutil_returns_numbers():
    pytest.importorskip("psutil")
    sample = SystemMonitor().sample()
    assert sample.memory_percent is not None and sample.memory_percent > 0  # nosec B101


def _cfg(cid: str) -> ComponentConfig:
    return ComponentConfig(cid, "LED", None, {}, HardwareBinding(0, 1))


def test_flow_layout_wraps_rows_and_is_deterministic():
    comps = [_cfg(f"c{i}") for i in range(5)]
    area = Rect(10, 20, 100, 100)
    pos = FlowLayoutEngine().layout(comps, area, item_size=(30, 20), spacing=5)
    assert pos["c0"] == Rect(10, 20, 30, 20)  # nosec B101
    assert pos["c1"] == Rect(45, 20, 30, 20)  # nosec B101
    assert pos["c2"] == Rect(80, 20, 30, 20) or pos["c2"].y > 20  # nosec B101
    assert FlowLayoutEngine().layout(comps, area, (30, 20), 5) == pos  # nosec B101


def test_flow_layout_puts_overflow_off_canvas():
    comps = [_cfg("a"), _cfg("b"), _cfg("c")]
    pos = FlowLayoutEngine().layout(
        comps, Rect(0, 0, 30, 20), item_size=(30, 20), spacing=4
    )
    assert pos["a"] == Rect(0, 0, 30, 20)  # nosec B101
    assert pos["b"].x > 30 and pos["b"].y > 20  # nosec B101
    assert (
        pos["c"] == pos["b"]
    )  # nosec B101  (all overflow items share the parking spot)
