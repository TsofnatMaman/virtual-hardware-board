"""STM32C031 board implementation."""

from simulator.core.board import register_board

from .board import STM32C031Board

register_board("stm32c031", STM32C031Board)

__all__ = ["STM32C031Board"]
