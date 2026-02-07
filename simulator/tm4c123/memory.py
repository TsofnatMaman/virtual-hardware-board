"""TM4C123 memory management with FLASH, SRAM, peripherals, and bit-band support."""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import cast, override

from simulator.core.exceptions import (
    MemoryAccessError,
    MemoryBoundsError,
)
from simulator.interfaces.memory import BaseMemory
from simulator.interfaces.peripheral import BasePeripherals
from simulator.utils.config_loader import Memory_Config


@dataclass(frozen=True)
class PeripheralMapping:
    """Maps peripheral address range to peripheral instance."""

    base: int
    size: int
    instance: BasePeripherals


class TM4C123_Memory(BaseMemory):
    """TM4C123 memory implementation with FLASH, SRAM, peripherals, and bit-band regions."""

    def __init__(self, mem_config: Memory_Config) -> None:
        super().__init__(mem_config)

        # Backing storage
        self._flash = bytearray(mem_config.flash_size)
        self._sram = bytearray(mem_config.sram_size)

        # Peripheral mappings
        self._peripherals: dict[int, PeripheralMapping] = {}
        self._peripheral_starts: list[int] = []
        self._last_peripheral_mapping: PeripheralMapping | None = None

    # ==========================================================
    # Helpers
    # ==========================================================

    def _get_config(self) -> Memory_Config:
        """Get memory config with proper type hint."""
        return cast(Memory_Config, self.memory_config)

    # ==========================================================
    # Public API
    # ==========================================================

    def register_peripheral(self, base_address: int, size: int, peripheral: BasePeripherals) -> PeripheralMapping:
        """Register a peripheral instance to a memory region.

        Args:
            peripheral: The peripheral instance (e.g., GPIO, UART)
            base_address: Start address in memory
            size: Size of the peripheral's address space

        Returns:
            The created PeripheralMapping object.
        """
        # Check for overlapping ranges with existing peripherals
        if size <= 0:
            raise ValueError("peripheral size must be positive")

        new_start = base_address
        new_end = base_address + size

        # Find insertion point
        idx = bisect.bisect_right(self._peripheral_starts, new_start)

        # Check previous mapping for overlap
        if idx - 1 >= 0:
            prev_base = self._peripheral_starts[idx - 1]
            prev = self._peripherals[prev_base]
            if prev.base + prev.size > new_start:
                raise ValueError(f"peripheral range overlaps with existing peripheral at 0x{prev.base:X}")

        # Check next mapping for overlap
        if idx < len(self._peripheral_starts):
            next_base = self._peripheral_starts[idx]
            if new_end > next_base:
                raise ValueError(f"peripheral range overlaps with existing peripheral at 0x{next_base:X}")

        mapping = PeripheralMapping(base=base_address, size=size, instance=peripheral)
        self._peripherals[base_address] = mapping
        bisect.insort(self._peripheral_starts, base_address)

        return mapping

    @override
    def read(self, address: int, size: int) -> int:
        if size not in (1, 2, 4):
            raise MemoryAccessError(
                address=address,
                details={"size": size, "reason": "invalid read size"},
            )

        if self._is_flash(address):
            return self._read_flash(address, size)
        if self._is_sram(address):
            return self._read_sram(address, size)
        if self._is_bitband_alias(address):
            return self._read_bitband(address)
        if self._is_peripheral(address):
            return self._read_peripheral(address, size)

        raise MemoryAccessError(address)

    @override
    def write(self, address: int, size: int, value: int) -> None:
        if size not in (1, 2, 4):
            raise MemoryAccessError(
                address=address,
                details={"size": size, "reason": "invalid write size"},
            )

        if self._is_flash(address):
            raise MemoryAccessError(
                address=address,
                details={"reason": "write to flash is forbidden"},
            )
        if self._is_sram(address):
            self._write_sram(address, size, value)
            return
        if self._is_bitband_alias(address):
            self._write_bitband(address, value)
            return
        if self._is_peripheral(address):
            self._write_peripheral(address, value, size)
            return

        raise MemoryAccessError(address)

    @override
    def reset(self) -> None:
        """Reset memory to power-on state.

        Clears SRAM (volatile, power-dependent).
        FLASH is left unchanged (persistent, non-volatile).
        """
        # Only clear SRAM. Do NOT unregister peripherals here; peripheral
        # lifecycle is managed by the board. Clear only the last-access cache.
        self._sram[:] = bytearray(len(self._sram))
        self._last_peripheral_mapping = None

    @override
    def read_block(self, address: int, size: int) -> bytes:
        if self._is_flash(address):
            cfg = self._get_config()
            offset = address - cfg.flash_base
            return bytes(self._flash[offset : offset + size])

        if self._is_sram(address):
            cfg = self._get_config()
            offset = address - cfg.sram_base
            return bytes(self._sram[offset : offset + size])

        return b"\x00" * size

    # ==========================================================
    # Address classification
    # ==========================================================

    def _is_flash(self, address: int) -> bool:
        cfg = self._get_config()
        return self._in_region(
            address,
            cfg.flash_base,
            cfg.flash_size,
        )

    def _is_sram(self, address: int) -> bool:
        cfg = self._get_config()
        return self._in_region(
            address,
            cfg.sram_base,
            cfg.sram_size,
        )

    def _is_peripheral(self, address: int) -> bool:
        cfg = self._get_config()
        return self._in_region(
            address,
            cfg.periph_base,
            cfg.periph_size,
        )

    def _is_bitband_alias(self, address: int) -> bool:
        cfg = self._get_config()
        return self._in_region(
            address,
            cfg.bitband_base,
            cfg.bitband_size,
        )

    @staticmethod
    def _in_region(address: int, base: int, size: int) -> bool:
        return base <= address < base + size

    # ==========================================================
    # Flash
    # ==========================================================

    def _read_flash(self, address: int, size: int) -> int:
        cfg = self._get_config()
        offset = address - cfg.flash_base
        return self._read_bytes(
            self._flash,
            offset,
            size,
            base_address=cfg.flash_base,
            region="flash",
        )

    # ==========================================================
    # SRAM
    # ==========================================================

    def _read_sram(self, address: int, size: int) -> int:
        cfg = self._get_config()
        offset = address - cfg.sram_base
        return self._read_bytes(
            self._sram,
            offset,
            size,
            base_address=cfg.sram_base,
            region="sram",
        )

    def _write_sram(self, address: int, size: int, value: int) -> None:
        cfg = self._get_config()
        offset = address - cfg.sram_base
        self._write_bytes(
            self._sram,
            offset,
            size,
            value,
            base_address=cfg.sram_base,
            region="sram",
        )

    # ==========================================================
    # Peripherals
    # ==========================================================

    def _read_peripheral(self, address: int, size: int) -> int:
        mapping = self._find_peripheral(address)
        offset = address - mapping.base
        return mapping.instance.read(offset, size)

    def _write_peripheral(self, address: int, value: int, size: int) -> None:
        mapping = self._find_peripheral(address)
        offset = address - mapping.base
        mapping.instance.write(offset, size, value)

    def _find_peripheral(self, address: int) -> PeripheralMapping:
        # Check cache (last accessed peripheral)
        last = self._last_peripheral_mapping
        if last and last.base <= address < last.base + last.size:
            return last

        # Optimized lookup using bisect (O(log N))
        # Find the insertion point for address in the sorted starts list
        # If we have a starts index list, use bisect for fast lookup
        if self._peripheral_starts:
            idx = bisect.bisect_right(self._peripheral_starts, address) - 1
            if idx >= 0:
                base = self._peripheral_starts[idx]
                mapping = self._peripherals[base]
                if address < base + mapping.size:
                    # Update cache
                    self._last_peripheral_mapping = mapping
                    return mapping

        # Fallback: tests and some code may populate _peripherals dict
        # directly without maintaining _peripheral_starts. Scan dict as
        # a fallback (O(N)). Update cache if found.
        for mapping in self._peripherals.values():
            if mapping.base <= address < mapping.base + mapping.size:
                self._last_peripheral_mapping = mapping
                return mapping

        raise MemoryAccessError(address)

    # ==========================================================
    # Bit-band alias
    # ==========================================================

    def _read_bitband(self, address: int) -> int:
        underlying = self._bitband_to_underlying(address)
        bit = self._bitband_bit(address)
        value = self.read(underlying, 4)
        return (value >> bit) & 1

    def _write_bitband(self, address: int, value: int) -> None:
        underlying = self._bitband_to_underlying(address)
        bit = self._bitband_bit(address)

        current = self.read(underlying, 4)
        if value & 1:
            current |= 1 << bit
        else:
            current &= ~(1 << bit)

        self.write(underlying, 4, current)

    def _bitband_to_underlying(self, address: int) -> int:
        cfg = self._get_config()
        if address < cfg.bitband_base or address >= cfg.bitband_base + cfg.bitband_size:
            raise MemoryAccessError(address)

        # Compute bit-word offset and then underlying byte offset
        bit_word_offset = (address - cfg.bitband_base) // 4
        underlying_byte_offset = bit_word_offset // 32

        # Candidate underlying addresses for SRAM and Peripherals
        sram_candidate = cfg.sram_base + underlying_byte_offset
        periph_candidate = cfg.periph_base + underlying_byte_offset

        # Prefer SRAM if candidate falls within SRAM region
        if self._in_region(sram_candidate, cfg.sram_base, cfg.sram_size):
            return sram_candidate

        # Otherwise, if within peripheral region, use peripheral base
        if self._in_region(periph_candidate, cfg.periph_base, cfg.periph_size):
            return periph_candidate

        # Not a valid underlying address
        raise MemoryAccessError(address)

    def _bitband_bit(self, address: int) -> int:
        cfg = self._get_config()
        if address < cfg.bitband_base or address >= cfg.bitband_base + cfg.bitband_size:
            raise MemoryAccessError(address)
        bit_word_offset = (address - cfg.bitband_base) // 4
        return bit_word_offset % 32

    # ==========================================================
    # Raw memory helpers
    # ==========================================================

    def _read_bytes(
        self,
        memory: bytearray,
        offset: int,
        size: int,
        *,
        base_address: int,
        region: str,
    ) -> int:
        if offset < 0 or offset + size > len(memory):
            raise MemoryBoundsError(
                address=base_address + offset,
                size=size,
                region=region,
            )

        return int.from_bytes(memory[offset : offset + size], "little")

    def _write_bytes(
        self,
        memory: bytearray,
        offset: int,
        size: int,
        value: int,
        *,
        base_address: int,
        region: str,
    ) -> None:
        if offset < 0 or offset + size > len(memory):
            raise MemoryBoundsError(
                address=base_address + offset,
                size=size,
                region=region,
            )

        # Mask value to size and write bytes
        value &= (1 << (size * 8)) - 1
        memory[offset : offset + size] = value.to_bytes(size, "little")
