"""GUI backend interfaces and adapters."""

from __future__ import annotations

from dataclasses import dataclass
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

    @property
    def board_name(self) -> str:
        return self.board.name

    def step(self, cycles: int) -> None:
        self.board.step(cycles)

    def reset(self) -> None:
        self.board.reset()

    def read(self, address: int, size: int) -> int:
        return self.board.read(address, size)

    def write(self, address: int, size: int, value: int) -> None:
        self.board.write(address, size, value)

    def cpu_snapshot(self) -> CpuSnapshot:
        return self.board.cpu.get_snapshot()
