"""Interface abstractions for the simulator.

Defines behavioral contracts that all implementations must satisfy:
- Board: MCU board interface (abstract base class)
- Peripheral: Memory-mapped peripheral protocol
- MemoryAccessModel: How addresses map to hardware registers (board-specific semantics)
- PinLevel, PinMode: GPIO enumerations (re-exported from core for convenience)
"""

from simulator.interfaces.board import Board
from simulator.interfaces.cpu import ICPU
from simulator.interfaces.clock import IClock, ClockSubscriber
from simulator.interfaces.interrupt_controller import IInterruptController, InterruptEvent
from simulator.interfaces.memory_map import IMemoryMap
from simulator.interfaces.peripheral import Peripheral
from simulator.interfaces.memory_access import MemoryAccessModel
from simulator.core.gpio_enums import PinLevel, PinMode

__all__ = [
    "Board",
    "ICPU",
    "IClock",
    "ClockSubscriber",
    "IInterruptController",
    "InterruptEvent",
    "IMemoryMap",
    "Peripheral",
    "MemoryAccessModel",
    "PinLevel",
    "PinMode",
]
