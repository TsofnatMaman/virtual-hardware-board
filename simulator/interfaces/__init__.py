"""Interface abstractions for the simulator."""

from simulator.interfaces.board import BaseBoard
from simulator.interfaces.memory import BaseMemory
from simulator.interfaces.peripheral import BasePeripherals

__all__ = ["BaseBoard", "BaseMemory", "BasePeripherals"]
