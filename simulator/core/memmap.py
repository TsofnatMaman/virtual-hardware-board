"""Address space dispatcher.

Coordinates access to all memory regions (Flash, RAM, Peripherals, Bitband).
This is much simpler than the old MemoryBus because each region owns its behavior.
"""

from __future__ import annotations

import bisect
from typing import Optional

from simulator.core.address_space import (
    AddressRange,
    BitBandRegion,
    FlashMemory,
    MemoryRegion,
    PeripheralWindow,
    RamMemory,
)
from simulator.core.exceptions import (
    MemoryAccessError,
    MemoryAlignmentError,
    MemoryBoundsError,
)
from simulator.interfaces.memory_map import IMemoryMap
from simulator.interfaces.peripheral import Peripheral


class PeripheralMapping:
    """Represents a single peripheral at a base address."""

    def __init__(self, base: int, size: int, peripheral: Peripheral):
        self.base = base
        self.size = size
        self.range = AddressRange(base, size)
        self.peripheral = peripheral


class AddressSpace(IMemoryMap):
    """Maps all CPU-visible addresses to their target regions.

    This replaces the old "MemoryBus" concept. It's just an address dispatcher,
    not a "bus" in the electrical sense.
    """

    def __init__(
        self,
        flash: FlashMemory,
        sram: RamMemory,
        mmio: PeripheralWindow,
        bitband_regions: list[BitBandRegion],
    ):
        self.flash = flash
        self.sram = sram
        self.mmio = mmio
        self.bitband_regions = bitband_regions

        # Peripheral registry for MMIO dispatch
        self._peripherals: dict[int, PeripheralMapping] = {}
        self._periph_bases: list[int] = []

    def register_peripheral(self, base: int, size: int, peripheral: Peripheral) -> None:
        """Register a peripheral at a given base address.

        Raises ValueError if the peripheral overlaps with an existing one.
        """
        if size <= 0:
            raise ValueError("Peripheral size must be > 0")

        if not self.mmio.range.contains_range(base, size):
            raise MemoryBoundsError(base, size, "MMIO")

        # Check for overlaps
        idx = bisect.bisect_left(self._periph_bases, base)

        # Check overlap with previous peripheral
        if idx > 0:
            prev_base = self._periph_bases[idx - 1]
            prev = self._peripherals[prev_base]
            if base < prev.base + prev.size:
                raise ValueError(
                    f"Peripheral overlap at 0x{base:08X} with existing "
                    f"peripheral at 0x{prev.base:08X}-0x{prev.base + prev.size:08X}"
                )

        # Check overlap with next peripheral
        if idx < len(self._periph_bases):
            next_base = self._periph_bases[idx]
            if base + size > next_base:
                raise ValueError(
                    f"Peripheral overlap at 0x{base:08X}-0x{base + size:08X} "
                    f"with next peripheral at 0x{next_base:08X}"
                )

        mapping = PeripheralMapping(base, size, peripheral)
        self._periph_bases.insert(idx, base)
        self._peripherals[base] = mapping

    def find_peripheral(self, address: int) -> Optional[PeripheralMapping]:
        """Find the peripheral containing this address."""
        if not self._periph_bases:
            return None

        # Binary search
        idx = bisect.bisect_right(self._periph_bases, address) - 1
        if idx >= 0:
            base = self._periph_bases[idx]
            mapping = self._peripherals[base]
            if mapping.range.contains(address):
                return mapping

        return None

    def resolve_region(self, address: int) -> MemoryRegion | None:
        """Resolve which memory region contains the address."""
        for region in self.regions:
            if region.contains(address):
                return region
        return None

    def read(self, address: int, size: int) -> int:
        """Read from the address space."""
        self._validate_access(address, size)

        # Check bitband
        for bb in self.bitband_regions:
            if bb.contains(address):
                if size != 4:
                    raise MemoryAccessError(
                        address, message="Bitband accesses must be 4 bytes"
                    )
                return self._bitband_read(bb, address)

        # Check standard regions
        if self.flash.contains(address):
            return self.flash.read(address, size)
        if self.sram.contains(address):
            return self.sram.read(address, size)

        # Check peripherals
        if self.mmio.contains(address):
            mapping = self.find_peripheral(address)
            if mapping:
                offset = address - mapping.base
                return mapping.peripheral.read(offset, size)
            raise MemoryAccessError(address, message="No peripheral at this address")

        raise MemoryAccessError(address, message="Address not mapped")

    def write(self, address: int, size: int, value: int) -> None:
        """Write to the address space."""
        self._validate_access(address, size)

        # Check bitband
        for bb in self.bitband_regions:
            if bb.contains(address):
                if size != 4:
                    raise MemoryAccessError(
                        address, message="Bitband accesses must be 4 bytes"
                    )
                self._bitband_write(bb, address, value)
                return

        # Check standard regions
        if self.flash.contains(address):
            self.flash.write(address, size, value)
            return
        if self.sram.contains(address):
            self.sram.write(address, size, value)
            return

        # Check peripherals
        if self.mmio.contains(address):
            mapping = self.find_peripheral(address)
            if mapping:
                offset = address - mapping.base
                mapping.peripheral.write(offset, size, value)
                return
            raise MemoryAccessError(address, message="No peripheral at this address")

        raise MemoryAccessError(address, message="Address not mapped")

    def read_block(self, address: int, size: int) -> bytes:
        """Read a contiguous block (for boot/DMA)."""
        if self.flash.contains(address) and self.flash.range.contains_range(
            address, size
        ):
            return self.flash.read_block(address, size)
        if self.sram.contains(address) and self.sram.range.contains_range(
            address, size
        ):
            return self.sram.read_block(address, size)
        raise MemoryAccessError(
            address, message="Block read not supported for this region"
        )

    def reset(self) -> None:
        """Reset all regions and peripherals."""
        self.sram.reset()
        for mapping in self._peripherals.values():
            mapping.peripheral.reset()

    def get_memory_map(self) -> dict:
        """Return a human-readable description of the memory layout."""
        return {
            "flash": {
                "base": f"0x{self.flash.base:08X}",
                "size": f"0x{self.flash.size:X}",
            },
            "sram": {
                "base": f"0x{self.sram.base:08X}",
                "size": f"0x{self.sram.size:X}",
            },
            "mmio": {
                "base": f"0x{self.mmio.base:08X}",
                "size": f"0x{self.mmio.size:X}",
            },
            "bitband": [
                {
                    "alias_base": f"0x{bb.base:08X}",
                    "alias_size": f"0x{bb.size:X}",
                    "target_base": f"0x{bb.target.base:08X}",
                    "target_size": f"0x{bb.target.size:X}",
                    "target_is_peripheral": bb.target_is_peripheral,
                }
                for bb in self.bitband_regions
            ],
            "peripherals": [
                {
                    "base": f"0x{mapping.base:08X}",
                    "size": f"0x{mapping.size:X}",
                    "end": f"0x{mapping.base + mapping.size:08X}",
                }
                for mapping in self._peripherals.values()
            ],
        }

    @property
    def regions(self) -> list[MemoryRegion]:
        """Return all regions managed by this address space."""
        return [self.flash, self.sram, self.mmio, *self.bitband_regions]

    def _validate_access(self, address: int, size: int) -> None:
        """Check access size and alignment."""
        if size not in (1, 2, 4):
            raise MemoryAccessError(
                address, message="Access size must be 1, 2, or 4 bytes"
            )
        if size > 1 and address % size != 0:
            raise MemoryAlignmentError(address, size)

    def _bitband_read(self, bitband: BitBandRegion, address: int) -> int:
        """Read a bit via bitband alias."""
        target_addr, bit_idx = bitband.translate(address)

        # Read the underlying word
        if bitband.target_is_peripheral:
            mapping = self.find_peripheral(target_addr)
            if not mapping:
                raise MemoryAccessError(
                    target_addr, message="No peripheral under bitband"
                )
            offset = target_addr - mapping.base
            word = mapping.peripheral.read(offset, 4)
        else:
            word = self.sram.read(target_addr, 4)

        # Extract the bit
        return (word >> bit_idx) & 1

    def _bitband_write(self, bitband: BitBandRegion, address: int, value: int) -> None:
        """Write a bit via bitband alias."""
        target_addr, bit_idx = bitband.translate(address)

        # Read-modify-write the underlying word
        if bitband.target_is_peripheral:
            mapping = self.find_peripheral(target_addr)
            if not mapping:
                raise MemoryAccessError(
                    target_addr, message="No peripheral under bitband"
                )
            offset = target_addr - mapping.base
            word = mapping.peripheral.read(offset, 4)
        else:
            word = self.sram.read(target_addr, 4)

        # Modify the bit
        if value & 1:
            word |= 1 << bit_idx
        else:
            word &= ~(1 << bit_idx)

        # Write back
        if bitband.target_is_peripheral:
            mapping = self.find_peripheral(target_addr)
            if not mapping:
                raise MemoryAccessError(
                    target_addr, message="No peripheral under bitband"
                )
            offset = target_addr - mapping.base
            mapping.peripheral.write(offset, 4, word)
        else:
            self.sram.write(target_addr, 4, word)


class BaseMemoryMap(AddressSpace):
    """Compatibility alias for AddressSpace (matches UML terminology)."""
