"""Memory address space model.

The address space is made up of regions (Flash, SRAM, MMIO). Each region
owns its own read/write behavior. This is a cleaner model than MemoryBus
trying to dispatch everything.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from simulator.core.exceptions import MemoryAccessError, MemoryBoundsError


@dataclass(frozen=True)
class AddressRange:
    """An immutable address range."""
    base: int
    size: int
    
    def contains(self, address: int) -> bool:
        return self.base <= address < self.base + self.size
    
    def contains_range(self, address: int, size: int) -> bool:
        return self.contains(address) and address + size <= self.base + self.size
    
    def __str__(self) -> str:
        return f"0x{self.base:08X}-0x{self.base + self.size:08X}"


class MemoryRegion(ABC):
    """Base class for any memory region (Flash, SRAM, MMIO, etc.)."""
    
    def __init__(self, address_range: AddressRange, name: str):
        self.range = address_range
        self.name = name
    
    @property
    def base(self) -> int:
        return self.range.base
    
    @property
    def size(self) -> int:
        return self.range.size
    
    def contains(self, address: int) -> bool:
        return self.range.contains(address)
    
    @abstractmethod
    def read(self, address: int, size: int) -> int:
        """Read from this region. Address is absolute (not offset)."""
        ...
    
    @abstractmethod
    def write(self, address: int, size: int, value: int) -> None:
        """Write to this region. Address is absolute."""
        ...
    
    @abstractmethod
    def reset(self) -> None:
        """Reset this region to initial state."""
        ...


class FlashMemory(MemoryRegion):
    """Non-volatile, read-only storage for firmware."""
    
    def __init__(self, address_range: AddressRange):
        super().__init__(address_range, "FLASH")
        self._data = bytearray(address_range.size)
    
    def load_image(self, data: bytes) -> None:
        """Load firmware image into flash."""
        if len(data) > len(self._data):
            raise ValueError(f"Firmware {len(data)} bytes exceeds flash {len(self._data)} bytes")
        self._data[:len(data)] = data
    
    def read(self, address: int, size: int) -> int:
        if not self.range.contains_range(address, size):
            raise MemoryBoundsError(address, size, self.name)
        offset = address - self.base
        return int.from_bytes(self._data[offset:offset + size], "little")
    
    def write(self, address: int, size: int, value: int) -> None:
        raise MemoryAccessError(
            address, message=f"Cannot write to flash memory at 0x{address:08X}"
        )
    
    def read_block(self, address: int, size: int) -> bytes:
        """Read a contiguous block of flash (used for boot)."""
        if not self.range.contains_range(address, size):
            raise MemoryBoundsError(address, size, self.name)
        offset = address - self.base
        return bytes(self._data[offset:offset + size])
    
    def reset(self) -> None:
        pass  # Flash doesn't "reset"


class RamMemory(MemoryRegion):
    """Volatile, read-write storage."""
    
    def __init__(self, address_range: AddressRange, name: str = "SRAM"):
        super().__init__(address_range, name)
        self._data = bytearray(address_range.size)
    
    def read(self, address: int, size: int) -> int:
        if not self.range.contains_range(address, size):
            raise MemoryBoundsError(address, size, self.name)
        offset = address - self.base
        return int.from_bytes(self._data[offset:offset + size], "little")
    
    def write(self, address: int, size: int, value: int) -> None:
        if not self.range.contains_range(address, size):
            raise MemoryBoundsError(address, size, self.name)
        mask = (1 << (size * 8)) - 1
        offset = address - self.base
        self._data[offset:offset + size] = (value & mask).to_bytes(size, "little")
    
    def read_block(self, address: int, size: int) -> bytes:
        """Read a contiguous block of RAM."""
        if not self.range.contains_range(address, size):
            raise MemoryBoundsError(address, size, self.name)
        offset = address - self.base
        return bytes(self._data[offset:offset + size])
    
    def reset(self) -> None:
        """Zero out all RAM on reset."""
        self._data[:] = b"\x00" * len(self._data)


class BitBandRegion(MemoryRegion):
    """Bit-band alias window.
    
    ARM Cortex-M bit-band regions allow byte-level bit access via 32-bit words.
    Each 32-byte region of the target maps to 32 words, where each word 
    controls one bit.
    
    This region is read-only; actual read/write is handled by BitBandAccessor.
    """
    
    def __init__(
        self,
        alias_range: AddressRange,
        target_range: AddressRange,
        target_is_peripheral: bool,
    ):
        super().__init__(alias_range, f"BITBAND[{target_range.base:08X}]")
        self.target = target_range
        self.target_is_peripheral = target_is_peripheral
    
    def translate(self, alias_address: int) -> tuple[int, int]:
        """Convert alias address to (target_address, bit_index).
        
        ARM bitband: alias offset = (byte_offset * 32) + (bit_index * 4)
        So: byte_offset = alias_offset // 32, bit_index = (alias_offset % 32) // 4
        """
        if not self.range.contains(alias_address):
            raise MemoryBoundsError(alias_address, 4, self.name)
        
        alias_offset = alias_address - self.base
        byte_offset = (alias_offset // 32) * 4
        bit_index = (alias_offset % 32) // 4
        target_address = self.target.base + byte_offset
        
        if not self.target.contains(target_address):
            raise MemoryBoundsError(
                alias_address, 4, f"{self.name} -> invalid target"
            )
        
        return target_address, bit_index
    
    def read(self, address: int, size: int) -> int:
        raise RuntimeError("BitBand regions are not directly readable; use AddressSpace")
    
    def write(self, address: int, size: int, value: int) -> None:
        raise RuntimeError("BitBand regions are not directly writable; use AddressSpace")
    
    def reset(self) -> None:
        pass


class PeripheralWindow(MemoryRegion):
    """MMIO window base class. Actual reads/writes are routed to peripherals."""
    
    def __init__(self, address_range: AddressRange):
        super().__init__(address_range, "MMIO")
    
    def read(self, address: int, size: int) -> int:
        raise RuntimeError("PeripheralWindow.read() should not be called; use AddressSpace")
    
    def write(self, address: int, size: int, value: int) -> None:
        raise RuntimeError("PeripheralWindow.write() should not be called; use AddressSpace")
    
    def reset(self) -> None:
        pass
