"""CPU interface for board integration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, Mapping

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

    @abstractmethod
    def get_snapshot(self) -> "CpuSnapshot":
        """Return a debug snapshot of CPU registers and flags."""
        ...

    def tick(self, cycles: int = 1) -> None:
        """Advance CPU by the given number of cycles (default: step cycles)."""
        for _ in range(cycles):
            self.step()

    def handle_interrupt(self, _event: "InterruptEvent") -> None:
        """Handle an interrupt event (default: no-op)."""
        return None


@dataclass(frozen=True)
class RegisterValue:
    """Single register value for UI/debug panels."""

    name: str
    value: int
    group: str = "core"


@dataclass(frozen=True)
class CpuSnapshot:
    """Snapshot of CPU state for UI/debug panels."""

    registers: Iterable[RegisterValue]
    flags: Mapping[str, bool]
