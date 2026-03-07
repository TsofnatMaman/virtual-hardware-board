"""STM32 vendor implementations.

Contains implementations for STM32 microcontroller variants.
"""

from simulator.core.board import register_board

from .board import STM32F4Board
from .gpio import STM32GPIO

register_board("stm32f4", STM32F4Board)

__all__ = ["STM32F4Board", "STM32GPIO"]
