"""Core modules for the simulator.

Core infrastructure for board-agnostic functionality:
- register: Hardware register abstraction
- address_space: Memory regions (Flash, RAM, Bitband, etc.)
- memmap: Address space dispatcher
- cpu: CortexM CPU via Unicorn Engine
- gpio_enums: GPIO pin level and mode enumerations (shared infrastructure)
- board: Board registry and factory (infrastructure; Board ABC is in interfaces)
"""

# New architecture
from simulator.core.register import (
    Register,
    SimpleRegister,
    ReadOnlyRegister,
    WriteOnlyRegister,
    RegisterFile,
    RegisterDescriptor,
)
from simulator.core.address_space import (
    AddressRange,
    MemoryRegion,
    FlashMemory,
    RamMemory,
    BitBandRegion,
    PeripheralWindow,
)
from simulator.core.memmap import AddressSpace, BaseMemoryMap, PeripheralMapping
from simulator.core.cpu import CortexM, UnicornEngine
from simulator.core.clock import Clock
from simulator.core.interrupt_controller import InterruptController
from simulator.core.peripheral import BasePeripheral
from simulator.core.simulation_engine import SimulationEngine
from simulator.core.gpio_enums import PinLevel, PinMode
from simulator.core.board import BoardRegistry, create_board, list_available_boards

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
