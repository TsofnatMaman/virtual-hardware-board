"""Abstract memory interface for the simulator."""

from abc import ABC, abstractmethod

from simulator.interfaces.peripheral import BasePeripherals
from simulator.utils.config_loader import Memory_Config


class BaseMemory(ABC):
    """Absract interface for memory-mapped storage and peripherals."""

    memory_config: Memory_Config | None = None

    def __init__(self, mem_config: Memory_Config):
        self.memory_config = mem_config

    @abstractmethod
    def read(self, address: int, size: int) -> int:
        """Read a value from memory or peripheral.

        Args:
            address: Memory address to read
            size: Number of bytes (1, 2 or 4)

        Returns:
            Interger value read
        """

        raise NotImplementedError

    @abstractmethod
    def write(self, address: int, size: int, value: int) -> None:
        """Write a value to memory or peripheral.

        Args:
            address: Memory address to write
            size: Number of bytes (1, 2 or 4)
            value: Integer value to write
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def peripherals(self) -> dict[int, BasePeripherals]:
        """Get all peripherals mapped in memory.

        Returns:
            Dictionary mapping base addresses to peripheral instances
        """
        raise NotImplementedError
