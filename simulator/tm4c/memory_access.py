"""TM4C123 memory access model - bit-banded GPIO addressing.

TM4C123 GPIO uses a unique "masked data" window where the address itself
encodes which bits are accessible. This is hardware bit-banding.

The GPIO data register (DATA) occupies a window of addresses where:
  - Address difference from base determines which bits are masked
  - mask = 1 << ((offset >> 2) & 0x7)  for an 8-bit GPIO port
  
For example, reading/writing address (base + 0x004) accesses only bit 0 of DATA.
Reading/writing address (base + 0x008) accesses only bit 1 of DATA.
And so on, up to bits 0-7.

When all bits are desired, address (base + 0x3FC) gives unrestricted access.

Register offsets (from TM4C123 datasheet):
- 0x00-0x3FC: DATA (masked window - 256 addresses, each selects different bits)
- 0x400: DIR    (direction: 0=input, 1=output)
- 0x404: IS     (interrupt sense: 0=edge, 1=level)
- 0x408: IBE    (interrupt both edges: 1=both)
- 0x40C: IEV    (interrupt event: 0=falling, 1=rising)
- 0x410: IM     (interrupt mask)
- 0x414: RIS    (raw interrupt status)
- 0x418: MIS    (masked interrupt status, read-only)
- 0x41C: ICR    (interrupt clear, write-only)
- 0x420: AFSEL  (alternate function select)
- 0x42C: DR2R/DR4R/DR8R: drive strength
- 0x500: DEN    (digital enable)
"""

from __future__ import annotations

from simulator.interfaces.memory_access import MemoryAccessModel


class TM4C123BitBandedAccessModel(MemoryAccessModel):
    """Bit-banded addressing for TM4C123 GPIO.

    The DATA register occupies a special window where address determines bit mask:
        offset = address - gpio_base
        if 0 <= offset <= 0x3FC:
            mask = 1 << ((offset >> 2) & 0x7)   # For 8-bit GPIO (Cortex-M4)

    This allows atomic single-bit reads/writes without bit manipulation in software.

    Regular control registers (DIR, AFSEL, etc.) use standard offset mapping.
    """

    # Regular control registers (standard offset mapping, outside masked window)
    _CONTROL_REGISTERS = {
        0x400: "DIR",
        0x404: "IS",
        0x408: "IBE",
        0x40C: "IEV",
        0x410: "IM",
        0x414: "RIS",
        0x418: "MIS",  # Read-only
        0x41C: "ICR",  # Write-only
        0x420: "AFSEL",
        0x500: "DEN",
    }

    _CONTROL_ADDRESSES = {v: k for k, v in _CONTROL_REGISTERS.items()}

    def __init__(self, gpio_base: int, num_pins: int = 8):
        """Initialize with GPIO port base address.

        Args:
            gpio_base: Base address of GPIO port (e.g., 0x40004000 for GPIOA)
            num_pins: Number of pins (typically 8 for TM4C)
        """
        self.gpio_base = gpio_base
        self.num_pins = num_pins
        self._num_pins_mask = (1 << num_pins) - 1
        self._masked_data_size = num_pins * 4  # Each pin gets 4 bytes in masked window

    def decode_register_access(self, address: int, size: int) -> tuple[str, int] | None:
        """Map address to register (handling bit-banded DATA window).

        Args:
            address: Full 32-bit memory address
            size: Access size (must be 4 bytes for masked DATA)

        Returns:
            (register_name, offset_or_mask) where register_name is:
            - "DATA" for masked addresses (offset encodes bit mask)
            - Standard register name for control registers (DIR, AFSEL, etc.)
            Or None if address is invalid
        """
        if address < self.gpio_base or address >= self.gpio_base + 0x600:
            return None

        offset = address - self.gpio_base

        # Masked DATA window: 0x00-0x3FC
        if 0 <= offset <= 0x3FC:
            # Address encodes bit information: (offset >> 2) & 0x7 = bit_index
            # Return both the register name and the offset
            # Caller can decode bit index if needed: bit_index = (offset >> 2) & (num_pins - 1)
            return ("DATA_MASKED", offset)

        # Control registers: standard mapping outside masked window
        if offset in self._CONTROL_REGISTERS:
            return (self._CONTROL_REGISTERS[offset], offset)

        return None

    def encode_register_address(self, register_name: str) -> int:
        """Convert register name to absolute address.

        For masked DATA, returns the base address (full access mask: all bits).
        For control registers, returns their fixed address.
        """
        if register_name in {"DATA", "DATA_MASKED"}:
            return self.gpio_base + 0x3FC  # Full access mask

        if register_name in self._CONTROL_ADDRESSES:
            return self.gpio_base + self._CONTROL_ADDRESSES[register_name]

        raise ValueError(f"Unknown register: {register_name}")

    @property
    def description(self) -> str:
        """Human-readable description of this access model."""
        return (
            f"TM4C123 Bit-Banded GPIO Addressing\n"
            f"  Base: 0x{self.gpio_base:08X}\n"
            f"  Pattern: Masked window (0x00-0x3FC) - address encodes bit mask\n"
            f"  Example: 0x{self.gpio_base + 0x004:08X} → DATA bit 0 only\n"
            f"  Example: 0x{self.gpio_base + 0x3FC:08X} → DATA all bits\n"
            f"  Control registers (DIR, AFSEL, etc.) use standard offset mapping"
        )
