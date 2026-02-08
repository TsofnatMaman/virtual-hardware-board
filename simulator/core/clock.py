"""Clock implementation for simulation timing."""

from __future__ import annotations

from typing import List

from simulator.interfaces.clock import ClockSubscriber, IClock


class Clock(IClock):
    """Simple pub/sub clock that notifies subscribers on tick()."""

    def __init__(self, frequency: int = 1_000_000):
        if frequency <= 0:
            raise ValueError("Clock frequency must be positive")
        self._frequency = frequency
        self._cycle_count = 0
        self._subscribers: List[ClockSubscriber] = []

    @property
    def frequency(self) -> int:
        return self._frequency

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    def subscribe(self, subscriber: ClockSubscriber) -> None:
        if subscriber not in self._subscribers:
            self._subscribers.append(subscriber)

    def unsubscribe(self, subscriber: ClockSubscriber) -> None:
        if subscriber in self._subscribers:
            self._subscribers.remove(subscriber)

    def tick(self, cycles: int = 1) -> None:
        if cycles < 0:
            raise ValueError("cycles must be >= 0")
        if cycles == 0:
            return

        self._cycle_count += cycles

        # Notify subscribers once per tick batch
        for subscriber in list(self._subscribers):
            # Prefer tick(cycles) if implemented
            try:
                subscriber.tick(cycles)
            except (TypeError, AttributeError):
                # Fallback: subscriber.tick() or subscriber.step()
                if hasattr(subscriber, "tick"):
                    for _ in range(cycles):
                        subscriber.tick()
                elif hasattr(subscriber, "step"):
                    for _ in range(cycles):
                        subscriber.step()

    def reset(self) -> None:
        self._cycle_count = 0
