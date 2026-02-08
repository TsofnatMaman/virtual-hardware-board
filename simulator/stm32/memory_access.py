"""STM32F4 memory access model - direct register offset mapping.

STM32 GPIO uses straightforward memory-mapped registers where the address
directly indicates which register is being accessed.

Register offsets (relative to GPIO port base):
- 0x00: MODER   (mode)
- 0x04: OTYPER  (output type)
- 0x08: OSPEEDR (output speed)
- 0x0C: PUPDR   (pull-up/pull-down)
- 0x10: IDR     (input data)
- 0x14: ODR     (output data)
- 0x18: BSRR    (bit set/reset)
- 0x1C: LCKR    (lock)
- 0x20: AFRL    (alternate function low)
- 0x24: AFRH    (alternate function high)
"""

from __future__ import annotations

from simulator.interfaces.memory_access import MemoryAccessModel


class STM32F4DirectAccessModel(MemoryAccessModel):
    """Direct register offset mapping for STM32F4 GPIO.

    In this model, address directly selects a register:
        register = (address - gpio_base) & 0xFF

    This is the simplest and most common pattern for ARM Cortex-M MCUs.
    """

    # Register offset mappings (from STM32F4 datasheet)
    _REGISTERS = {
        0x00: "MODER",
        0x04: "OTYPER",
        0x08: "OSPEEDR",
        0x0C: "PUPDR",
        0x10: "IDR",
        0x14: "ODR",
        0x18: "BSRR",
        0x1C: "LCKR",
        0x20: "AFRL",
        0x24: "AFRH",
    }

    _ADDRESSES = {v: k for k, v in _REGISTERS.items()}

    def __init__(self, gpio_base: int):
        """Initialize with GPIO port base address.

        Args:
            gpio_base: Base address of GPIO port (e.g., 0x40020000 for GPIOA)
        """
        self.gpio_base = gpio_base

    def decode_register_access(self, address: int, size: int) -> tuple[str, int] | None:
        """Map address to register offset.

        Args:
            address: Full 32-bit memory address
            size: Access size (ignored for direct mapping)

        Returns:
            (register_name, offset_within_register) if valid, None otherwise
        """
        if address < self.gpio_base or address >= self.gpio_base + 0x100:
            return None

        offset = address - self.gpio_base
        reg_offset = offset & 0xFF  # Keep only register offset

        if reg_offset not in self._REGISTERS:
            return None

        register_name = self._REGISTERS[reg_offset]
        return (register_name, offset)

    def encode_register_address(self, register_name: str) -> int:
        """Convert register name to absolute address."""
        if register_name not in self._ADDRESSES:
            raise ValueError(f"Unknown register: {register_name}")
        return self.gpio_base + self._ADDRESSES[register_name]

    @property
    def description(self) -> str:
        """Human-readable description of this access model."""
        return (
            f"STM32F4 Direct Register Offset Mapping\n"
            f"  Base: 0x{self.gpio_base:08X}\n"
            f"  Pattern: address selects register directly\n"
            f"  Example: 0x{self.gpio_base + 0x14:08X} → ODR (output data)"
        )
