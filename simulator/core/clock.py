"""Clock implementation for simulation timing."""

from __future__ import annotations

from typing import Callable, List

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

    def _validate_cycles(self, cycles: int) -> None:
        if cycles < 0:
            raise ValueError("cycles must be >= 0")

    def _repeat_call(self, fn: Callable[[], None], cycles: int) -> None:
        for _ in range(cycles):
            fn()

    def _call_with_cycles(self, tick_fn: Callable[[int], None], cycles: int) -> bool:
        try:
            tick_fn(cycles)
        except TypeError:
            return False
        return True

    def _notify_subscriber(self, subscriber: ClockSubscriber, cycles: int) -> None:
        tick_fn = getattr(subscriber, "tick", None)
        if callable(tick_fn):
            if self._call_with_cycles(tick_fn, cycles):
                return
            self._repeat_call(tick_fn, cycles)
            return

        step_fn = getattr(subscriber, "step", None)
        if callable(step_fn):
            self._repeat_call(step_fn, cycles)

    def tick(self, cycles: int = 1) -> None:
        self._validate_cycles(cycles)
        if cycles == 0:
            return

        self._cycle_count += cycles

        # Notify subscribers once per tick batch
        for subscriber in list(self._subscribers):
            self._notify_subscriber(subscriber, cycles)

    def reset(self) -> None:
        self._cycle_count = 0
