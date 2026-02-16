"""GUI backend interfaces and adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ContextManager
from contextlib import nullcontext
from typing import Protocol

from simulator.interfaces.board import Board
from simulator.interfaces.cpu import CpuSnapshot


class SimulatorBackend(Protocol):
    """Minimal simulator backend required by the GUI."""

    @property
    def board_name(self) -> str:
        ...

    def step(self, cycles: int) -> None:
        ...

    def reset(self) -> None:
        ...

    def read(self, address: int, size: int) -> int:
        ...

    def write(self, address: int, size: int, value: int) -> None:
        ...

    def cpu_snapshot(self) -> CpuSnapshot:
        ...


@dataclass
class BoardBackend(SimulatorBackend):
    """Adapter that exposes a Board through the SimulatorBackend interface."""

    board: Board
    lock: ContextManager | None = None

    def __post_init__(self) -> None:
        if self.lock is None:
            self.lock = nullcontext()

    @property
    def board_name(self) -> str:
        return self.board.name

    def step(self, cycles: int) -> None:
        assert self.lock is not None
        with self.lock:
            self.board.step(cycles)

    def reset(self) -> None:
        assert self.lock is not None
        with self.lock:
            self.board.reset()

    def read(self, address: int, size: int) -> int:
        assert self.lock is not None
        with self.lock:
            return self.board.read(address, size)

    def write(self, address: int, size: int, value: int) -> None:
        assert self.lock is not None
        with self.lock:
            self.board.write(address, size, value)

    def cpu_snapshot(self) -> CpuSnapshot:
        assert self.lock is not None
        with self.lock:
            return self.board.cpu.get_snapshot()
