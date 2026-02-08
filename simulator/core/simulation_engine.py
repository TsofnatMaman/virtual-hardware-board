"""Simulation engine for orchestrating board execution."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.interfaces.board import Board


class SimulationEngine:
    """Minimal simulation engine.

    This delegates execution to the board's step/reset methods.
    """

    def run(self, board: "Board", cycles: int = 1) -> None:
        """Run the board for the given number of cycles."""
        self.step(board, cycles)

    def step(self, board: "Board", cycles: int = 1) -> None:
        """Advance the board by a number of cycles."""
        board.step(cycles)

    def reset(self, board: "Board") -> None:
        """Reset the board."""
        board.reset()
