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
    def write_data_masked(self, offset: int, value: int, mask: int) -> None:
        """Read masked bits from a register.

        Args:
            offset: Register offset in bytes
            value: Value to write to masked bits
            mask: Bitmask specifying which bits to modify
        """
        raise NotImplementedError

    @abstractmethod
    def read_data_masked(self, offset: int, mask: int) -> int:
        """Read masked bits from a register.

        Args:
            offset: Register offset in bytes
            mask: Bitmask specifying witch bits to read

        Returns:
            Masked register value
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset peripheral to power-on state."""
        raise NotImplementedError
