"""Cortex-M CPU simulation via Unicorn Engine.

This module provides a thin, isolated wrapper around Unicorn for CPU execution.
The CPU is responsible for: instruction execution, register management, and
memory access hooks into the AddressSpace.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from simulator.core.memmap import AddressSpace
from simulator.utils.consts import align_to_page
from simulator.interfaces.cpu import CpuSnapshot, RegisterValue

if TYPE_CHECKING:
    from simulator.interfaces.interrupt_controller import InterruptEvent

logger = logging.getLogger(__name__)

try:
    from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB
    from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MEM_READ, UC_MEM_WRITE
    from unicorn.arm_const import (
        UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
        UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
        UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
        UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
        UC_ARM_REG_XPSR, UC_ARM_REG_MSP,
    )
    UNICORN_AVAILABLE = True
except ImportError:
    UNICORN_AVAILABLE = False
    # Provide dummy values for type checking
    UC_ARCH_ARM = UC_MODE_THUMB = 0
    UC_HOOK_MEM_READ = UC_HOOK_MEM_WRITE = 0
    UC_MEM_READ = UC_MEM_WRITE = 0
    UC_ARM_REG_R0 = UC_ARM_REG_R1 = UC_ARM_REG_R2 = UC_ARM_REG_R3 = 0
    UC_ARM_REG_R4 = UC_ARM_REG_R5 = UC_ARM_REG_R6 = UC_ARM_REG_R7 = 0
    UC_ARM_REG_R8 = UC_ARM_REG_R9 = UC_ARM_REG_R10 = UC_ARM_REG_R11 = 0
    UC_ARM_REG_R12 = UC_ARM_REG_SP = UC_ARM_REG_LR = UC_ARM_REG_PC = 0
    UC_ARM_REG_XPSR = UC_ARM_REG_MSP = 0


# Map R0-R15, SP, LR, PC
_ARM_REG_MAP = {
    0: UC_ARM_REG_R0, 1: UC_ARM_REG_R1, 2: UC_ARM_REG_R2, 3: UC_ARM_REG_R3,
    4: UC_ARM_REG_R4, 5: UC_ARM_REG_R5, 6: UC_ARM_REG_R6, 7: UC_ARM_REG_R7,
    8: UC_ARM_REG_R8, 9: UC_ARM_REG_R9, 10: UC_ARM_REG_R10, 11: UC_ARM_REG_R11,
    12: UC_ARM_REG_R12,
    13: UC_ARM_REG_SP,   # R13 = SP
    14: UC_ARM_REG_LR,   # R14 = LR
    15: UC_ARM_REG_PC,   # R15 = PC
}

_XPSR_THUMB_BIT = 0x01000000
_PC_THUMB_MASK = 0xFFFFFFFE


class UnicornEngine:
    """Minimal Unicorn wrapper.
    
    This isolates Unicorn-specific code so it can be replaced/tested easily.
    """
    
    def __init__(self):
        if not UNICORN_AVAILABLE:
            raise ImportError("Unicorn is required. Install: pip install unicorn")
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    
    def map_memory(self, base: int, size: int) -> None:
        """Map a memory region in the emulator."""
        self.uc.mem_map(base, align_to_page(size))
    
    def write_memory(self, base: int, data: bytes) -> None:
        """Write bytes into emulator memory."""
        self.uc.mem_write(base, data)
    
    def read_memory(self, base: int, size: int) -> bytes:
        """Read bytes from emulator memory."""
        return self.uc.mem_read(base, size)
    
    def set_register(self, reg_const: int, value: int) -> None:
        """Set a CPU register."""
        self.uc.reg_write(reg_const, value & 0xFFFFFFFF)
    
    def get_register(self, reg_const: int) -> int:
        """Get a CPU register."""
        return self.uc.reg_read(reg_const)
    
    def add_memory_hook(self, callback, begin: int, end: int) -> None:
        """Add a hook for memory accesses in [begin, end)."""
        self.uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, callback, begin=begin, end=end)
    
    def step(self, pc: int) -> None:
        """Execute one instruction from PC."""
        # Cortex-M is always Thumb; Unicorn expects bit0 set for Thumb execution.
        self.uc.emu_start(pc | 1, 0xFFFFFFFF, count=1)


class CortexM:
    """ARM Cortex-M CPU simulator.
    
    Responsibilities:
    - Execute CPU instructions via Unicorn
    - Manage CPU registers (R0-R15, XPSR, etc.)
    - Coordinate with AddressSpace for memory access
    
    The CPU does NOT manage memory mapping or bootstrapping the engine.
    Those are the caller's responsibility. This keeps the CPU simple and
    replaceable.
    """
    
    def __init__(self, engine: UnicornEngine, address_space: AddressSpace):
        """Initialize CPU with pre-configured engine and address space.
        
        Args:
            engine: A UnicornEngine instance (pre-mapped and ready)
            address_space: The memory address space to use for accesses
        
        The caller is responsible for:
        - Creating and mapping all memory regions in the engine
        - Setting up hooks for MMIO
        """
        self.engine = engine
        self.address_space = address_space
        self._pending_interrupts: list["InterruptEvent"] = []
    
    def reset(self) -> None:
        """Reset CPU: clear registers, load firmware from flash, set PC/MSP.
        
        Assumes firmware image is already in flash. The AddressSpace must be
        pre-populated with firmware (typically via FlashMemory.load_image()).
        """
        # Clear all general-purpose registers
        for reg_idx in range(13):
            self.engine.set_register(_ARM_REG_MAP[reg_idx], 0)
        self.engine.set_register(UC_ARM_REG_XPSR, _XPSR_THUMB_BIT)
        
        # Read boot sequence from flash
        # Vector table: [0] = MSP, [1] = ResetVector
        msp = self.address_space.read(self.address_space.flash.base, 4)
        reset_vector = self.address_space.read(self.address_space.flash.base + 4, 4)
        
        # Copy firmware from AddressSpace to Unicorn (for efficiency)
        firmware = self.address_space.read_block(
            self.address_space.flash.base,
            self.address_space.flash.size,
        )
        self.engine.write_memory(self.address_space.flash.base, firmware)
        
        # Validate boot configuration
        sram_range = self.address_space.sram.range
        if not sram_range.contains(msp):
            raise RuntimeError(
                f"Invalid boot MSP 0x{msp:08X}: not in SRAM {sram_range}"
            )
        
        if reset_vector & 1 == 0:
            raise RuntimeError(
                f"Invalid reset vector 0x{reset_vector:08X}: Thumb bit not set"
            )
        
        # Set stack pointer and program counter
        self.engine.set_register(UC_ARM_REG_MSP, msp)
        self.engine.set_register(UC_ARM_REG_SP, msp)
        # Unicorn expects the Thumb bit set in PC when running in THUMB mode.
        self.engine.set_register(UC_ARM_REG_PC, reset_vector)
    
    def step(self) -> None:
        """Execute one CPU instruction."""
        pc = self.engine.get_register(UC_ARM_REG_PC)
        try:
            self.engine.step(pc)
        except Exception as exc:
            logger.error(f"CPU execution error at PC=0x{pc:08X}: {exc}")
            raise

    def tick(self, cycles: int = 1) -> None:
        """Advance the CPU by a number of cycles (step-per-cycle)."""
        for _ in range(cycles):
            self.step()

    def handle_interrupt(self, event: "InterruptEvent") -> None:
        """Handle an interrupt event (default: queue it)."""
        self._pending_interrupts.append(event)
    
    def get_register(self, index: int) -> int:
        """Get a register by index (0-15)."""
        if index not in _ARM_REG_MAP:
            raise ValueError(f"Invalid register index {index}; must be 0-15")
        return self.engine.get_register(_ARM_REG_MAP[index])
    
    def set_register(self, index: int, value: int) -> None:
        """Set a register by index (0-15)."""
        if index not in _ARM_REG_MAP:
            raise ValueError(f"Invalid register index {index}; must be 0-15")
        self.engine.set_register(_ARM_REG_MAP[index], value)

    def get_snapshot(self) -> CpuSnapshot:
        """Return a snapshot of CPU registers and flags for debug/GUI."""
        reg_defs = [
            ("R0", UC_ARM_REG_R0, "GPR"),
            ("R1", UC_ARM_REG_R1, "GPR"),
            ("R2", UC_ARM_REG_R2, "GPR"),
            ("R3", UC_ARM_REG_R3, "GPR"),
            ("R4", UC_ARM_REG_R4, "GPR"),
            ("R5", UC_ARM_REG_R5, "GPR"),
            ("R6", UC_ARM_REG_R6, "GPR"),
            ("R7", UC_ARM_REG_R7, "GPR"),
            ("R8", UC_ARM_REG_R8, "GPR"),
            ("R9", UC_ARM_REG_R9, "GPR"),
            ("R10", UC_ARM_REG_R10, "GPR"),
            ("R11", UC_ARM_REG_R11, "GPR"),
            ("R12", UC_ARM_REG_R12, "GPR"),
            ("SP", UC_ARM_REG_SP, "SP/PC"),
            ("LR", UC_ARM_REG_LR, "SP/PC"),
            ("PC", UC_ARM_REG_PC, "SP/PC"),
            ("XPSR", UC_ARM_REG_XPSR, "STATUS"),
            ("MSP", UC_ARM_REG_MSP, "STATUS"),
        ]

        registers = [
            RegisterValue(name, self.engine.get_register(reg), group)
            for name, reg, group in reg_defs
        ]

        xpsr = self.engine.get_register(UC_ARM_REG_XPSR)
        flags = {
            "N": bool(xpsr & (1 << 31)),
            "Z": bool(xpsr & (1 << 30)),
            "C": bool(xpsr & (1 << 29)),
            "V": bool(xpsr & (1 << 28)),
            "Q": bool(xpsr & (1 << 27)),
            "T": bool(xpsr & (1 << 24)),
        }

        return CpuSnapshot(registers=registers, flags=flags)
    
    # Private helpers -------------------------------------------------------
    
    def _memory_hook(self, uc, access, address, size, value, _user_data):
        """Callback for MMIO accesses.
        
        When the CPU accesses the MMIO window, we dispatch to AddressSpace.
        """
        try:
            if access == UC_MEM_READ:
                val = self.address_space.read(address, size)
                uc.mem_write(address, val.to_bytes(size, "little"))
            elif access == UC_MEM_WRITE:
                self.address_space.write(address, size, value)
        except Exception as exc:
            logger.error(f"MMIO access error at 0x{address:08X}: {exc}")
            raise
