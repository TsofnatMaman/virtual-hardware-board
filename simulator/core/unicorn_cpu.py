"""Base implementation for ARM Cortex-M CPUs using Unicorn Engine."""

from __future__ import annotations

import logging
from enum import IntEnum
from typing import override

from simulator.interfaces.cpu import BaseCPU
from simulator.interfaces.memory import BaseMemory

logger = logging.getLogger(__name__)

try:
    from unicorn import (
        Uc, UC_ARCH_ARM, UC_MODE_THUMB,
        UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE,
        UC_MEM_READ, UC_MEM_WRITE
    )
    from unicorn.arm_const import (
        UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
        UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
        UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
        UC_ARM_REG_R12, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
        UC_ARM_REG_XPSR, UC_ARM_REG_MSP, UC_ARM_REG_PSP
    )
    UNICORN_AVAILABLE = True
except ImportError:
    UNICORN_AVAILABLE = False
    # Define dummies to avoid NameError during class definition
    UC_ARCH_ARM = UC_MODE_THUMB = 0
    UC_HOOK_MEM_READ = UC_HOOK_MEM_WRITE = 0
    UC_MEM_READ = UC_MEM_WRITE = 0
    UC_ARM_REG_PC = UC_ARM_REG_XPSR = UC_ARM_REG_MSP = UC_ARM_REG_SP = 0
    logger.error("Unicorn Engine not found. Please install via 'pip install unicorn'")


class Reg(IntEnum):
    """ARM Cortex-M4 Register Indices."""
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4
    R5 = 5
    R6 = 6
    R7 = 7
    R8 = 8
    R9 = 9
    R10 = 10
    R11 = 11
    R12 = 12
    SP = 13
    LR = 14
    PC = 15


class BaseCortexM_CPU(BaseCPU):
    """Base class for Unicorn-based Cortex-M simulations (M3/M4/M7)."""

    def __init__(self, memory: BaseMemory) -> None:
        self._memory = memory

        if not UNICORN_AVAILABLE:
            raise ImportError("Unicorn Engine is required but not installed.")

        self._uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB)

        self._reg_map = {
            Reg.R0: UC_ARM_REG_R0, Reg.R1: UC_ARM_REG_R1, Reg.R2: UC_ARM_REG_R2, Reg.R3: UC_ARM_REG_R3,
            Reg.R4: UC_ARM_REG_R4, Reg.R5: UC_ARM_REG_R5, Reg.R6: UC_ARM_REG_R6, Reg.R7: UC_ARM_REG_R7,
            Reg.R8: UC_ARM_REG_R8, Reg.R9: UC_ARM_REG_R9, Reg.R10: UC_ARM_REG_R10, Reg.R11: UC_ARM_REG_R11,
            Reg.R12: UC_ARM_REG_R12, Reg.SP: UC_ARM_REG_SP, Reg.LR: UC_ARM_REG_LR, Reg.PC: UC_ARM_REG_PC,
        }

    @property
    @override
    def memory(self) -> BaseMemory:
        return self._memory

    @override
    def step(self) -> None:
        pc = self._uc.reg_read(UC_ARM_REG_PC)
        try:
            self._uc.emu_start(pc, 0xFFFFFFFF, count=1)
        except Exception as e:
            logger.error(f"CPU Fault at PC={hex(pc)}: {e}")

    def get_register(self, reg: int) -> int:
        return self._uc.reg_read(self._reg_map[reg])

    def set_register(self, reg: int, value: int) -> None:
        self._uc.reg_write(self._reg_map[reg], value)

    def _reset_registers(self) -> None:
        """Reset core registers to default values."""
        for reg_const in self._reg_map.values():
            self._uc.reg_write(reg_const, 0)
        self._uc.reg_write(UC_ARM_REG_XPSR, 0x01000000)

    def _setup_mmio(self, base: int, size: int) -> None:
        """Map MMIO region and attach hooks."""
        self._uc.mem_map(base, size)
        self._uc.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self._mmio_hook, begin=base, end=base + size)

    def reset_core(self, flash_base: int, flash_size: int) -> None:
        """Perform standard Cortex-M reset sequence.

        1. Reset registers.
        2. Sync firmware from BaseMemory to Unicorn memory.
        3. Load MSP and PC from Vector Table.
        """
        self._reset_registers()

        # Sync Flash Content: Copy firmware from BaseMemory to Unicorn Memory
        if hasattr(self._memory, 'read_block'):
            firmware = self._memory.read_block(flash_base, flash_size)
            self._uc.mem_write(flash_base, firmware)

        # Read Initial SP and PC from the (now synced) memory
        # Vector Table is at the beginning of Flash
        initial_sp = self._memory.read(flash_base, 4)
        reset_vector = self._memory.read(flash_base + 4, 4)

        self._uc.reg_write(UC_ARM_REG_MSP, initial_sp)
        self._uc.reg_write(UC_ARM_REG_SP, initial_sp)
        self._uc.reg_write(UC_ARM_REG_PC, reset_vector & 0xFFFFFFFE)

    def _mmio_hook(self, uc, access, address, size, value, user_data):
        if access == UC_MEM_READ:
            val = self._memory.read(address, size)
            uc.mem_write(address, val.to_bytes(size, 'little'))
        elif access == UC_MEM_WRITE:
            self._memory.write(address, size, value)