"""CPU abstraction interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulator.interfaces.memory import BaseMemory


class BaseCPU(ABC):
    """Abstract interface for simulated processors.

    Responsibilities:
    - Fetch instructions from memory
    - Execute instructions
    - Manage CPU state (registers, program counter, etc.)
    - Read/write data via memory bus
    """

    @property
    @abstractmethod
    def memory(self) -> BaseMemory:
        """Get the CPU's memory bus.

        Returns:
            BaseMemory instance for instruction/data access
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset CPU to power-on state."""
        raise NotImplementedError

    @abstractmethod
    def step(self) -> None:
        """Execute one instruction cycle."""
        raise NotImplementedError
