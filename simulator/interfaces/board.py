"""Board abstraction interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from simulator.interfaces.cpu import BaseCPU
from simulator.interfaces.memory import BaseMemory
from simulator.interfaces.peripheral import BasePeripherals
from simulator.utils.config_loader import Simulator_Config


class BaseBoard(ABC):
    """Abstract interface for simulated embedded boards.

    Responsibilities:
    - Own and manage CPU (processor that masters memory bus)
    - Own and manage Memory (storage for code and data)
    - Own and manage Peripherals (GPIO, UART, Timers, etc.)
    - Control board lifecycle (reset, power management, etc.)
    - Expose components for observation/debugging
    """

    # Optional configuration payload (used by builder/factory system)
    config: Simulator_Config | None = None

    def __init__(self, config: Simulator_Config | None = None, **_kwargs: Any) -> None:
        self.config = config

    # ====== Core API (Required) ======

    @property
    @abstractmethod
    def cpu(self) -> BaseCPU:
        """Get the board's CPU (processor that masters memory bus).

        Returns:
            BaseCPU instance managing instruction execution
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def memory(self) -> BaseMemory:
        """Get the board's memory (storage for code and data).

        Returns:
            BaseMemory instance managing address space (FLASH, SRAM, etc.)
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def peripherals(self) -> dict[str, BasePeripherals]:
        """Get the board's peripherals (GPIO, UART, Timers, etc.).

        Returns:
            Dictionary mapping peripheral names to instances
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset board to power-on state.

        Resets CPU and all peripherals.
        """
        raise NotImplementedError

    # ====== Optional API (Extensible) ======

    def gui_state(self) -> dict[str, Any]:
        """Get board state for GUI or headless display.

        Override this method to expose LEDs, buttons, displays, etc.

        Returns:
            Dictionary with board state (LEDs, buttons, etc.)
        """
        return {}

    def get_name(self) -> str:
        """Get board name for display.

        Returns:
            Human-readable board name
        """

        return "Unknown"