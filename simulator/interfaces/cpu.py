"""CPU interface for board integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.interfaces.interrupt_controller import InterruptEvent


class ICPU(ABC):
    """CPU abstraction used by boards and the simulation engine."""

    @abstractmethod
    def step(self) -> None:
        """Execute a single instruction."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset CPU state."""
        ...

    def tick(self, cycles: int = 1) -> None:
        """Advance CPU by the given number of cycles (default: step cycles)."""
        for _ in range(cycles):
            self.step()

    def handle_interrupt(self, _event: "InterruptEvent") -> None:
        """Handle an interrupt event (default: no-op)."""
        return None
