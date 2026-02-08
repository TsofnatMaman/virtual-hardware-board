"""Memory access models - how addresses map to registers.

Different hardware boards have fundamentally different ways of interpreting
memory addresses during read/write operations. This module defines the interface
for these different access patterns.

Examples:
- STM32: Direct offset mapping (offset 0x10 = IDR register)
- TM4C123: Bit-banded addressing (address encodes the bit mask)
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MemoryAccessModel(ABC):
    """Protocol for how addresses map to hardware registers.
    
    Different MCU architectures have different memory access semantics:
    
    - DIRECT ACCESS (STM32): Address directly selects a register
    - BIT-BANDED ACCESS (TM4C): Address encodes which bits are accessible
    - OTHER PATTERNS: Custom addressing schemes for future boards
    
    The MemoryAccessModel abstracts this difference, making it explicit that
    different boards have different access semantics.
    """
    
    @abstractmethod
    def decode_register_access(
        self, address: int, size: int
    ) -> tuple[str, int] | None:
        """Decode an address to determine what register is being accessed.
        
        This method is called BEFORE a peripheral's read/write method.
        It determines whether an address should be routed to a peripheral,
        and if so, which register within that peripheral.
        
        Args:
            address: Full 32-bit memory address
            size: Size of access (1, 2, 4 bytes)
        
        Returns:
            Tuple of (register_name, decoded_offset) if the address maps to
            a known register, or None if the address is not recognized.
        """
        ...
    
    @abstractmethod
    def encode_register_address(self, register_name: str) -> int:
        """Encode a register name back to its memory address.
        
        Used for documentation and introspection (e.g., printing register
        addresses for debugging).
        
        Args:
            register_name: Name of the register (e.g., "ODR", "IDR", "DATA")
        
        Returns:
            Base memory address of that register
        """
        ...
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the access model.
        
        Examples:
        - "STM32F4: Direct register offset mapping (ODR @ 0x14)"
        - "TM4C123: Bit-banded GPIO (address encodes bit mask)"
        """
        ...
