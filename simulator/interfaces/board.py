"""Board abstraction interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from simulator.interfaces.memory import BaseMemory
from simulator.utils.config_loader import Simulator_Config


class BaseBoard(ABC):
    """Abstract interface for simulated embedded boards.

    Responsibilities:
    - Manage memory and peripherals
    - Aggregate interrupts from periphals
    - Expose board state in a GUI-agnostic form
    """

    # Optional board metadata (override in concrete implementations)
    FLASH_BASE: int | None = None
    SRAM_BASE: int | None = None
    SRAM_SIZE: int | None = None

    # Optional configuration payload (used by builder/factory system)
    config: Simulator_Config | None = None

    def __init__(self, config: Simulator_Config | None = None, **_kwargs: Any) -> None:
        self.config = config

    # ====== Core API (Required) ======

    @property
    @abstractmethod
    def memory(self) -> BaseMemory:
        """Get the board's memory map.

        Returns:
            BaseMemory instance managing address space
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        """Reset board and all peripherals to power-on state."""
        raise NotImplementedError

    @abstractmethod
    def get_pending_interrupt(self) -> Optional[int]:
        """Get pending interrupt request number.

        Returns:
            IRQ number if interrupt pending, None otherwise
        """
        raise NotImplementedError

    @abstractmethod
    def clear_pending_interrupt(self) -> None:
        """Clear the current pending interrupt."""
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

    # ====== Convenience Properties ======
    @property
    def has_pending_interrupt(self) -> bool:
        """Check if  interrupt is pending.

        Returns:
            True if interrupt pending, False otherwise
        """
        return self.get_pending_interrupt() is not None
