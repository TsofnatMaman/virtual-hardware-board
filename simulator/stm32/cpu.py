"""STM32 ARM Cortex-M4 CPU implementation."""

from __future__ import annotations

import logging
from typing import override

from simulator.core.unicorn_cpu import BaseCortexM_CPU
from simulator.interfaces.memory import BaseMemory

logger = logging.getLogger(__name__)

class STM32_CPU(BaseCortexM_CPU):
    """STM32 ARM Cortex-M4 processor simulation.

    Responsibilities:
    - Fetch instructions from memory
    - Execute ARM Thumb-2 instructions
    - Manage registers, PC, SP, etc.
    - Access memory via memory bus
    """

    # Boot Alias (Flash is mirrored here at boot in STM32)
    ALIAS_BASE = 0x00000000
    # ALIAS_SIZE will be derived from flash size in config

    def __init__(self, memory: BaseMemory) -> None:
        """Initialize CPU with memory bus.

        Args:
            memory: BaseMemory instance for instruction/data access
        """
        super().__init__(memory)

        # Map Memory Regions from Configuration
        cfg = self.memory.memory_config
        self._uc.mem_map(cfg.flash_base, cfg.flash_size)
        self._uc.mem_map(cfg.sram_base, cfg.sram_size)
        
        # Boot Alias (0x00000000 maps to Flash)
        self._uc.mem_map(self.ALIAS_BASE, cfg.flash_size)
        
        # Peripherals: Map a large region for MMIO (0x40000000 - 0x60000000)
        self._setup_mmio(0x40000000, 512 * 1024 * 1024)

    @override
    def reset(self) -> None:
        """Reset CPU to power-on state."""
        try:
            cfg = self.memory.memory_config
            # Standard Core Reset (Regs + Flash Sync + Vector Table)
            self.reset_core(cfg.flash_base, cfg.flash_size)

            # STM32 Specific: Sync Alias Region
            if hasattr(self._memory, 'read_block'):
                firmware = self._memory.read_block(cfg.flash_base, cfg.flash_size)
                self._uc.mem_write(self.ALIAS_BASE, firmware)
            
        except AttributeError:
            logger.warning("Memory interface does not support read_block. CPU reset incomplete.")