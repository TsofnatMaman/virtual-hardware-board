"""Core modules for the simulator.

Core infrastructure for board-agnostic functionality:
- register: Hardware register abstraction
- address_space: Memory regions (Flash, RAM, Bitband, etc.)
- memmap: Address space dispatcher
- cpu: CortexM CPU via Unicorn Engine
- gpio_enums: GPIO pin level and mode enumerations (shared infrastructure)
- board: Board registry and factory (infrastructure; Board ABC is in interfaces)
"""

from simulator.core.address_space import (
    AddressRange,
    BitBandRegion,
    FlashMemory,
    MemoryRegion,
    PeripheralWindow,
    RamMemory,
)
from simulator.core.board import BoardRegistry, create_board, list_available_boards
from simulator.core.clock import Clock
from simulator.core.cpu import CortexM, UnicornEngine
from simulator.core.gpio_enums import PinLevel, PinMode
from simulator.core.interrupt_controller import InterruptController
from simulator.core.memmap import AddressSpace, BaseMemoryMap, PeripheralMapping
from simulator.core.peripheral import BasePeripheral

# New architecture
from simulator.core.register import (
    ReadOnlyRegister,
    Register,
    RegisterDescriptor,
    RegisterFile,
    SimpleRegister,
    WriteOnlyRegister,
)
from simulator.core.simulation_engine import SimulationEngine
from simulator.core.sysctl import SysCtl

__all__ = [
    # Register abstractions
    "Register",
    "SimpleRegister",
    "ReadOnlyRegister",
    "WriteOnlyRegister",
    "RegisterFile",
    "RegisterDescriptor",
    # Memory regions
    "AddressRange",
    "MemoryRegion",
    "FlashMemory",
    "RamMemory",
    "BitBandRegion",
    "PeripheralWindow",
    # Address space
    "AddressSpace",
    "BaseMemoryMap",
    "PeripheralMapping",
    # CPU
    "CortexM",
    "UnicornEngine",
    # Clock / Interrupts
    "Clock",
    "InterruptController",
    # Peripheral base
    "BasePeripheral",
    "SysCtl",
    # Simulation engine
    "SimulationEngine",
    # GPIO shared infrastructure
    "PinLevel",
    "PinMode",
    # Board registry
    "BoardRegistry",
    "create_board",
    "list_available_boards",
]
