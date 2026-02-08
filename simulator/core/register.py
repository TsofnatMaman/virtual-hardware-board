"""Hardware register abstraction layer.

Registers are the fundamental unit of hardware behavior. This module provides
a clean contract for register behavior without tying it to a specific
peripheral implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RegisterDescriptor:
    """Metadata about a single register.

    This is documentation and validation, not enforcement. The actual
    read/write behavior is implemented in RegisterFile or peripheral code.
    """

    offset: int
    name: str
    width: int  # 1, 2, 4 bytes
    read_only: bool = False
    write_only: bool = False
    reset_value: int = 0
    side_effects_on_read: bool = False
    side_effects_on_write: bool = False


class Register(ABC):
    """Base class for any register with custom read/write behavior.

    A register is storage at a specific offset with specific width.
    Hardware behavior (like read-only or side-effects) is implemented
    by subclasses.

    For simple registers (just storage), use SimpleRegister.
    For registers with special behavior (like BSRR), subclass and override
    read() / write().
    """

    def __init__(self, offset: int, width: int, reset_value: int = 0):
        """Initialize a register.

        Args:
            offset: Address offset within the peripheral
            width: Native width in bytes (1, 2, 4) - for documentation only
            reset_value: Value to return to on reset()
        """
        self.offset = offset
        self.width = width  # Documentation only; not enforced
        self.reset_value = reset_value
        self.value = reset_value

    @abstractmethod
    def read(self, access_size: int) -> int:
        """Read from this register.

        Args:
            access_size: Bytes being read (1, 2, or 4). Caller ensures alignment.

        Returns:
            Register value, masked to requested size.

        Subclasses should override for registers with side effects on read.
        """
        ...

    @abstractmethod
    def write(self, access_size: int, val: int) -> None:
        """Update register value from a write.

        Args:
            access_size: Bytes being written (1, 2, or 4). Caller ensures alignment.
            val: Value being written (already masked to access_size).

        Subclasses should override for registers with side effects on write,
        or if the register is read-only/write-only.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset to default state."""
        ...


class SimpleRegister(Register):
    """A register that is just storage (no side effects)."""

    def read(self, access_size: int) -> int:
        mask = (1 << (access_size * 8)) - 1
        return self.value & mask

    def write(self, access_size: int, val: int) -> None:
        mask = (1 << (access_size * 8)) - 1
        self.value = (self.value & ~mask) | (val & mask)

    def reset(self) -> None:
        self.value = self.reset_value


class ReadOnlyRegister(SimpleRegister):
    """A read-only register. Writes are silently ignored."""

    def write(self, access_size: int, val: int) -> None:
        pass  # Ignore writes


class WriteOnlyRegister(SimpleRegister):
    """A write-only register. Reads always return reset value."""

    def read(self, access_size: int) -> int:
        return self.reset_value


class RegisterFile:
    """Storage and dispatch for a set of registers.

    Maps offset -> Register. Allows mixing simple and complex register types.

    Handles alignment and size validation to catch bugs early.
    """

    def __init__(self):
        self._registers: dict[int, Register] = {}

    def add(self, reg: Register) -> None:
        """Add a register to this file.

        Raises:
            ValueError: If a register already exists at this offset
        """
        if reg.offset in self._registers:
            raise ValueError(f"Register at offset 0x{reg.offset:X} already exists")
        self._registers[reg.offset] = reg

    def read(self, offset: int, access_size: int, default_reset: int = 0) -> int:
        """Read from offset.

        Args:
            offset: Register offset
            access_size: 1, 2, or 4 bytes
            default_reset: Value to return if offset not registered

        If the offset is not in any register, returns default_reset (typically 0).
        """
        self._validate_size(access_size)

        if offset in self._registers:
            return self._registers[offset].read(access_size)
        return default_reset & ((1 << (access_size * 8)) - 1)

    def write(self, offset: int, access_size: int, val: int) -> None:
        """Write to offset.

        Args:
            offset: Register offset
            access_size: 1, 2, or 4 bytes
            val: Value to write (will be masked to access_size)

        If the offset is not in any register, the write is silently ignored.
        This matches hardware behavior: writes to undefined offsets have no effect.
        """
        self._validate_size(access_size)

        if offset in self._registers:
            self._registers[offset].write(access_size, val)

    def reset(self) -> None:
        """Reset all registers."""
        for reg in self._registers.values():
            reg.reset()

    def get_register(self, offset: int) -> Optional[Register]:
        """Return the register at offset, or None."""
        return self._registers.get(offset)

    # Private helpers -------------------------------------------------------

    @staticmethod
    def _validate_size(size: int) -> None:
        """Check that size is valid."""
        if size not in (1, 2, 4):
            raise ValueError(f"Invalid access size {size}; must be 1, 2, or 4 bytes")
