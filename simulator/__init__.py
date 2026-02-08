"""Virtual Hardware Board Simulator.

This module provides simulation of ARM Cortex-M microcontrollers (STM32, TM4C123)
including CPU execution, memory management, and peripheral simulation.

New Architecture:
- Clean separation of concerns: CPU, memory, peripherals
- Explicit vendor differences (no generic base classes)
- Hardware-faithful register semantics
- Extensible board registry

Getting started:
    from simulator import create_board
    
    board = create_board("stm32f4")
    board.cpu.reset()
    board.cpu.step()
"""

# Core abstractions
from simulator.interfaces.board import Board
from simulator.core.board import create_board, list_available_boards, verify_boards_registered
from simulator.core.memmap import AddressSpace, BaseMemoryMap
from simulator.core.cpu import CortexM
from simulator.core.clock import Clock
from simulator.core.interrupt_controller import InterruptController
from simulator.core.simulation_engine import SimulationEngine
from simulator.core.sysctl import SysCtl

# Board implementations (auto-registers when imported)
from simulator.stm32 import STM32F4Board
from simulator.tm4c import TM4C123Board

__all__ = [
    # Core
    "Board",
    "AddressSpace",
    "BaseMemoryMap",
    "CortexM",
    "Clock",
    "InterruptController",
    "SimulationEngine",
    "SysCtl",
    # Board creation
    "create_board",
    "list_available_boards",
    "verify_boards_registered",
    # Concrete boards
    "STM32F4Board",
    "TM4C123Board",
]
