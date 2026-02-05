"""Abstract memory interface for the simulator."""

from abc import ABC, abstractmethod

from simulator.utils.config_loader import Memory_Config


class BaseMemory(ABC):
    """Absract interface for memory-mapped storage.

    Responsibilities:
    - Manage FLASH, SRAM, Bitband memory regions
    - Handle read/write operations with alignment and bounds checking
    - Support peripheral registration via bus interface
    - Pure storage - does NOT own peripherals
    """

    memory_config: Memory_Config | None = None

    def __init__(self, mem_config: Memory_Config):
        self.memory_config = mem_config

    @abstractmethod
    def read(self, address: int, size: int) -> int:
        """Read a value from memory.

        Args:
            address: Memory address to read
            size: Number of bytes (1, 2 or 4)

        Returns:
            Integer value read
        """

        raise NotImplementedError

    @abstractmethod
    def write(self, address: int, size: int, value: int) -> None:
        """Write a value to memory.

        Args:
            address: Memory address to write
            size: Number of bytes (1, 2 or 4)
            value: Integer value to write
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset memory to power-on state.

        Clears SRAM (volatile), leaves FLASH unchanged (persistent).
        Peripheral state is managed separately by peripherals themselves.
        """
        raise NotImplementedError
