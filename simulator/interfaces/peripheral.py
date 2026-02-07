"""Abstract peripheral interface definitions."""

from abc import ABC, abstractmethod


class BasePeripherals(ABC):
    """Abstract interface for memory-mapped peripherals."""

    @abstractmethod
    def write_register(self, offset: int, value: int) -> None:
        """Write a 32-bit value to a register.

        Args:
            offset: Register offset in bytes
            value: 32-bit value to write
        """
        raise NotImplementedError

    @abstractmethod
    def read_register(self, offset: int) -> int:
        """Read a 32-bit value from a register.

        Args:
            offset: Register offset in bytes

        Returns:
            32-bit register value
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset peripheral to power-on state."""
        raise NotImplementedError
