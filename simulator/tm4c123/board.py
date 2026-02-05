from __future__ import annotations

from typing import Any

from overrides import override  # type: ignore

from simulator.interfaces.board import BaseBoard
from simulator.interfaces.cpu import BaseCPU
from simulator.interfaces.memory import BaseMemory
from simulator.interfaces.peripheral import BasePeripherals
from simulator.tm4c123.cpu import TM4C123_CPU
from simulator.tm4c123.memory import TM4C123_Memory
from simulator.utils.config_loader import Simulator_Config, load_config

from .configs import BOARD_NAME


class TM4C123_Board(BaseBoard):
    """TM4C123 (Tiva C) board implementation.

    Architecture:
    - Board owns CPU (which masters memory bus) and Peripherals
    - CPU owns Memory (FLASH, SRAM, bitband regions)
    - Peripherals are registered with Memory for address mapping
    - Board manages peripheral lifecycle and integration
    """

    def __init__(self, **_kwargs: Any) -> None:
        config: Simulator_Config = load_config(BOARD_NAME)
        super().__init__(config, **_kwargs)

        # Step 1: Create memory (pure storage)
        self._memory = TM4C123_Memory(config.memory)

        # Step 2: Create CPU (masters the memory bus)
        self._cpu = TM4C123_CPU(self._memory)

        # Step 3: Initialize and register peripherals
        self._peripherals: dict[str, BasePeripherals] = {}
        self._initialize_peripherals()

    def _initialize_peripherals(self) -> None:
        """Initialize all board peripherals and register with memory.
        
        TODO: Create actual peripheral instances (GPIO, UART, Timers, etc.)
        and register them with memory at their mapped addresses.
        
        Example:
            self._peripherals["GPIOA"] = GPIO_Port("GPIOA")
            self._memory.register_peripheral(0x40004000, 0x1000, self._peripherals["GPIOA"])
        """
        pass

    @property
    @override
    def cpu(self) -> BaseCPU:
        """Get the board's CPU.

        Returns:
            TM4C123_CPU instance
        """
        return self._cpu

    @property
    @override
    def memory(self) -> BaseMemory:
        """Get the board's memory.

        Returns:
            TM4C123_Memory instance
        """
        return self._memory

    @property
    @override
    def peripherals(self) -> dict[str, BasePeripherals]:
        """Get the board's peripherals.

        Returns:
            Dictionary of peripheral instances
        """
        return self._peripherals

    @override
    def reset(self) -> None:
        """Reset board to power-on state.
        
        Resets CPU and all registered peripherals.
        The memory is implicitly reset when CPU resets and peripherals reset.
        """
        self._cpu.reset()
        self._memory.reset()
        
        # Reset all peripherals to power-on state
        for periph in self._peripherals.values():
            periph.reset()