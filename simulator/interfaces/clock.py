"""Clock interface for simulation timing and pub/sub tick propagation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


class ClockSubscriber(Protocol):
    """Anything that can advance on clock ticks."""

    def tick(self, cycles: int = 1) -> None:
        """Advance the subscriber by the given number of cycles."""
        ...


class IClock(ABC):
    """Clock interface used by boards and the simulation engine."""

    @property
    @abstractmethod
    def frequency(self) -> int:
        """Clock frequency in Hz."""
        ...

    @property
    @abstractmethod
    def cycle_count(self) -> int:
        """Total number of cycles elapsed."""
        ...

    @abstractmethod
    def subscribe(self, subscriber: ClockSubscriber) -> None:
        """Subscribe a component to clock ticks."""
        ...

    @abstractmethod
    def unsubscribe(self, subscriber: ClockSubscriber) -> None:
        """Unsubscribe a component from clock ticks."""
        ...

    @abstractmethod
    def tick(self, cycles: int = 1) -> None:
        """Advance the clock and notify subscribers."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset cycle count to zero."""
        ...
