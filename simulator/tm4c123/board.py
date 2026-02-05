from __future__ import annotations

from typing import Any

from overrides import override

from simulator.interfaces.board import BaseBoard
from simulator.interfaces.memory import BaseMemory
from simulator.tm4c123.memory import TM4C123_Memory
from simulator.utils.config_loader import Simulator_Config, load_config

from .configs import BOARD_NAME


class TM4C123_Board(BaseBoard):
    """
    TM4C123 (Tiva C) board implementation.

    Responsibilities:
    - Owns and initializes memory + peripherals
    - Aggresgates interrupt signals
    - Exposes board state in a GUI-agnostic form
    """

    # Board memory characteristics (used by CPU / loader validation)

    def __init__(self, **_kwargs: Any) -> None:
        config: Simulator_Config = load_config(BOARD_NAME)
        super().__init__(config, **_kwargs)
        self._memory = TM4C123_Memory(config.memory)

    @property
    @override
    def memory(self) -> BaseMemory:
        return self._memory
