"""Base peripheral helpers for shared behavior."""

from __future__ import annotations

from typing import Optional

from simulator.interfaces.interrupt_controller import IInterruptController


class BasePeripheral:
    """Optional base class for peripherals.

    Provides common wiring hooks for interrupts and clock ticks.
    Concrete peripherals still implement read/write/reset behavior.
    """

    def __init__(self, name: str, size: int, base_addr: int = 0):
        self.name = name
        self.size = size
        self.base_addr = base_addr
        self._interrupt_controller: Optional[IInterruptController] = None

    def attach_interrupt_controller(self, controller: IInterruptController) -> None:
        """Attach an interrupt controller to emit events."""
        self._interrupt_controller = controller

    def emit_interrupt(self, vector: int | None = None) -> None:
        """Emit an interrupt via the attached controller (if any)."""
        if self._interrupt_controller is not None:
            self._interrupt_controller.notify(self, vector)

    def tick(self, cycles: int = 1) -> None:
        """Advance internal time. Default is no-op."""
        _ = cycles

    def read(self, offset: int, size: int) -> int:
        """Read from a peripheral register (override in subclasses)."""
        raise NotImplementedError("read() must be implemented by subclasses")

    def write(self, offset: int, size: int, value: int) -> None:
        """Write to a peripheral register (override in subclasses)."""
        raise NotImplementedError("write() must be implemented by subclasses")

    def reset(self) -> None:
        """Reset peripheral state (override in subclasses)."""
        raise NotImplementedError("reset() must be implemented by subclasses")

    def read_register(self, offset: int, size: int) -> int:
        """Alias for read() using register terminology."""
        return self.read(offset, size)

    def write_register(self, offset: int, size: int, value: int) -> None:
        """Alias for write() using register terminology."""
        self.write(offset, size, value)
