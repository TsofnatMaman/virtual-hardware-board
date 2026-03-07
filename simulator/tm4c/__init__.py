"""TM4C vendor implementations.

Contains implementations for TM4C microcontroller variants.
"""

from simulator.core.board import register_board

from .board import TM4C123Board
from .gpio import TM4C123GPIO

register_board("tm4c123", TM4C123Board)

__all__ = ["TM4C123Board", "TM4C123GPIO"]
