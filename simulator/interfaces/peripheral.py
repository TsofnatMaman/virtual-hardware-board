"""Peripheral protocol for memory-mapped devices.

A Peripheral is any component that responds to read/write operations
at specific memory addresses (MMIO). Peripherals are registered with
the address space and handle accesses to their address range.

PROTOCOL CONTRACT:
- Offsets are peripheral-relative (0x00 - max address in peripheral)
- CPU address translation is handled by AddressSpace
- Must support 1, 2, and 4-byte accesses (width checked by caller)
- Read: Return the register value or 0 if undefined
- Write: Update internal state or silently ignore writes to undefined regs (ARM behavior)
- Reset: Restore all registers to reset values
- Exceptions: Only raise for truly exceptional conditions (never for normal I/O)

BOARD-SPECIFIC SEMANTICS:
Different boards may interpret offset differently, based on their hardware:
- STM32F4: offset directly selects a register (0x14 = ODR)
- TM4C123: offset may encode additional information (e.g., bit masks in address)

Use board.memory_access_model to understand how addresses map to registers
for the specific board being used. See MemoryAccessModel interface for details.
"""

from __future__ import annotations

from typing import Protocol


class Peripheral(Protocol):
    """Memory-mapped peripheral interface (structural subtyping).

    Implementations must provide read(), write(), and reset() methods
    with the signatures below. This protocol does NOT enforce behavior,
    only the method existence.

    Note: Actual behavior validation happens at the board/test level.
    """

    def write(self, offset: int, size: int, value: int) -> None:
        """Write to a peripheral register.

        Args:
            offset: Peripheral-relative address (0x00+)
            size: Number of bytes to write (1, 2, or 4)
            value: Data to write

        Behavior:
            - Writes to undefined offsets are silently ignored (ARM Cortex-M standard)
            - Size is always valid (AddressSpace validates)
        """
        ...

    def read(self, offset: int, size: int) -> int:
        """Read from a peripheral register.

        Args:
            offset: Peripheral-relative address (0x00+)
            size: Number of bytes to read (1, 2, or 4)

        Returns:
            Register value, or 0 if offset is undefined

        Behavior:
            - Reads from undefined offsets return 0 (ARM standard)
            - May have side effects (e.g., interrupt clear on read)
        """
        ...

    # Optional convenience aliases (read/write with register naming)
    def read_register(self, offset: int, size: int) -> int:
        """Alias for read() in register terminology."""
        ...

    def write_register(self, offset: int, size: int, value: int) -> None:
        """Alias for write() in register terminology."""
        ...

    def reset(self) -> None:
        """Reset peripheral to its initial state.

        Called when the board is reset. All registers should return to
        their reset values. Persisted state (e.g., control registers)
        should be restored to power-on defaults.
        """
        ...

    def tick(self, cycles: int = 1) -> None:
        """Advance internal time for clocked peripherals (optional)."""
        ...
