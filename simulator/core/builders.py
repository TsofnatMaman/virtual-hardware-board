"""Utilities for building and configuring address spaces and CPUs.

This module provides factories to reduce boilerplate when creating
boards. It encodes the common patterns (memory setup, hooking, etc.)
in reusable functions.
"""

from simulator.core.address_space import (
    AddressRange,
    BitBandRegion,
    FlashMemory,
    PeripheralWindow,
    RamMemory,
)
from simulator.core.cpu import CortexM, UnicornEngine
from simulator.core.memmap import AddressSpace, BaseMemoryMap
from simulator.utils.config_loader import MemoryConfig


def create_address_space_from_config(mem_config: MemoryConfig) -> AddressSpace:
    """Create a complete address space from memory configuration.

    Args:
        mem_config: Memory layout configuration (flash, SRAM, MMIO, bitband)

    Returns:
        Fully initialized AddressSpace
    """
    flash = FlashMemory(AddressRange(mem_config.flash_base, mem_config.flash_size))
    sram = RamMemory(
        AddressRange(mem_config.sram_base, mem_config.sram_size), name="SRAM"
    )
    mmio = PeripheralWindow(
        AddressRange(mem_config.periph_base, mem_config.periph_size)
    )

    bitband_regions = [
        BitBandRegion(
            AddressRange(mem_config.bitband_sram_base, mem_config.bitband_sram_size),
            AddressRange(mem_config.sram_base, mem_config.sram_size),
            target_is_peripheral=False,
        ),
        BitBandRegion(
            AddressRange(
                mem_config.bitband_periph_base, mem_config.bitband_periph_size
            ),
            AddressRange(mem_config.periph_base, mem_config.periph_size),
            target_is_peripheral=True,
        ),
    ]

    return BaseMemoryMap(flash, sram, mmio, bitband_regions)


def create_cpu_for_address_space(address_space: AddressSpace) -> CortexM:
    """Create and initialize a CPU for the given address space.

    This handles all the engineering: creating Unicorn, mapping memory,
    setting up MMIO hooks.

    Args:
        address_space: The address space to attach to

    Returns:
        Fully initialized CortexM CPU
    """
    engine = UnicornEngine()

    # Map all memory regions
    engine.map_memory(address_space.flash.base, address_space.flash.size)
    engine.map_memory(address_space.sram.base, address_space.sram.size)
    engine.map_memory(address_space.mmio.base, address_space.mmio.size)

    # Create CPU (before hooking, so the CPU manages the hook)
    cpu = CortexM(engine, address_space)

    # Add MMIO hook
    engine.add_memory_hook(
        cpu._memory_hook,  # pylint: disable=protected-access
        address_space.mmio.base,
        address_space.mmio.base + address_space.mmio.size,
    )

    return cpu
