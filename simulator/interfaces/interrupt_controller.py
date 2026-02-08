"""Interrupt controller interface and interrupt event types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InterruptEvent:
    """Represents a pending interrupt event."""

    source: object
    vector: int | None = None
    timestamp: int | None = None


class InterruptTarget(Protocol):
    """CPU-like target that can receive interrupts."""

    def handle_interrupt(self, event: InterruptEvent) -> None:
        """Handle a delivered interrupt event."""
        ...


class IInterruptController(ABC):
    """Interrupt controller pub/sub interface."""

    @abstractmethod
    def subscribe(self, peripheral: object) -> None:
        """Register a peripheral as a potential interrupt source."""
        ...

    @abstractmethod
    def attach_cpu(self, cpu: InterruptTarget) -> None:
        """Attach a CPU (or target) to receive interrupts."""
        ...

    @abstractmethod
    def notify(self, source: object, vector: int | None = None) -> InterruptEvent:
        """Notify the controller that an interrupt occurred."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Clear pending interrupts and detach state if needed."""
        ...
