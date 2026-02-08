"""Board registry and factory.

Provides discovery and instantiation of board implementations that are
registered globally during module initialization.

Board implementations must call register_board() in their module's
__init__.py for auto-discovery. This happens automatically when the
board module is imported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type

if TYPE_CHECKING:
    from simulator.interfaces.board import Board


class BoardRegistry:
    """Registry of available board implementations.

    This decouples board discovery from board implementation, making it
    easy to add new boards without modifying board classes.

    THREAD SAFETY: Not thread-safe. All board registration should happen
    during module initialization before any threads are spawned.
    """

    def __init__(self):
        self._boards: dict[str, Type[Board]] = {}

    def register(self, name: str, board_class: Type[Board]) -> None:
        """Register a board implementation."""
        if name in self._boards:
            raise ValueError(f"Board '{name}' already registered")
        self._boards[name] = board_class

    def get(self, name: str) -> Type[Board]:
        """Get a board class by name."""
        if name not in self._boards:
            raise ValueError(
                f"Unknown board '{name}'. Available: {list(self._boards.keys())}"
            )
        return self._boards[name]

    def list_boards(self) -> list[str]:
        """List all registered board names."""
        return list(self._boards.keys())

    def create(self, name: str, **kwargs) -> Any:
        """Instantiate a board by name."""
        board_class = self.get(name)
        return board_class(**kwargs)


# Global registry
_REGISTRY = BoardRegistry()


def register_board(
    name: str, board_class: Type[Board]
) -> None:  # Board in quotes due to TYPE_CHECKING
    """Register a board globally."""
    _REGISTRY.register(name, board_class)


def get_board(name: str) -> Type[Board]:  # Board in quotes due to TYPE_CHECKING
    """Get a board class by name."""
    return _REGISTRY.get(name)


def create_board(name: str, **kwargs) -> Any:
    """Create a board instance by name."""
    return _REGISTRY.create(name, **kwargs)


def list_available_boards() -> list[str]:
    """List all registered boards."""
    return _REGISTRY.list_boards()


def verify_boards_registered() -> None:
    """Verify that at least one board is registered.

    This is a diagnostic function to catch import/registration issues.
    Call this early in application startup if using boards dynamically.

    Raises:
        RuntimeError: If no boards are registered
    """
    boards = list_available_boards()
    if not boards:
        raise RuntimeError(
            "No boards registered! Ensure board modules are imported. "
            "Example: from simulator.stm32 import STM32F4Board"
        )
