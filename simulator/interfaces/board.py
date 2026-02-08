"""Board abstraction - behavioral contract.

A Board represents a complete MCU system with CPU, memory, and peripherals.
Every concrete board must implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from simulator.core.memmap import AddressSpace
from simulator.interfaces.clock import IClock
from simulator.interfaces.cpu import ICPU
from simulator.interfaces.interrupt_controller import IInterruptController
from simulator.interfaces.memory_map import IMemoryMap
from simulator.interfaces.peripheral import Peripheral

if TYPE_CHECKING:
    from simulator.interfaces.memory_access import MemoryAccessModel


class Board(ABC):
    """Base class for MCU boards.

    Each board is a complete system: CPU, memory map, and peripherals.
    The Board is responsible for wiring everything together.

    Every concrete board implementation (e.g., STM32F4Board, TM4C123Board)
    must inherit from this class and implement all abstract properties.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable board name (e.g., 'STM32F4', 'TM4C123')."""
        ...

    @property
    @abstractmethod
    def cpu(self) -> ICPU:  # Returns CortexM, but avoiding circular import
        """The CPU instance."""
        ...

    @property
    @abstractmethod
    def address_space(self) -> AddressSpace:
        """The memory address space dispatcher."""
        ...

    @property
    @abstractmethod
    def memory_map(self) -> IMemoryMap:
        """Board memory map (alias for address_space)."""
        ...

    @property
    @abstractmethod
    def peripherals(self) -> dict[str, Peripheral]:
        """All registered peripherals, keyed by name."""
        ...

    @property
    @abstractmethod
    def clock(self) -> IClock:
        """System clock (pub/sub tick source)."""
        ...

    @property
    @abstractmethod
    def interrupt_ctrl(self) -> IInterruptController:
        """Interrupt controller for peripheral events."""
        ...

    @property
    @abstractmethod
    def memory_access_model(self) -> MemoryAccessModel:
        """The memory access model that defines address-to-register mapping.

        Different boards have fundamentally different ways of interpreting
        memory addresses. This property exposes the board's access semantics:

        - STM32: Direct register offset mapping
        - TM4C123: Bit-banded addressing (address encodes bit mask)

        Use this to understand how this board's peripherals interpret addresses.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset the entire board."""
        ...

    @abstractmethod
    def step(self, cycles: int = 1) -> None:
        """Advance the board by a number of cycles."""
        ...

    @abstractmethod
    def read(self, address: int, size: int = 4) -> int:
        """Read from the board's memory map."""
        ...

    @abstractmethod
    def write(self, address: int, size: int, value: int) -> None:
        """Write to the board's memory map."""
        ...
