"""Interrupt controller implementation."""

from __future__ import annotations

from typing import List, Optional

from simulator.interfaces.clock import IClock
from simulator.interfaces.interrupt_controller import (
    IInterruptController,
    InterruptEvent,
    InterruptTarget,
)


class InterruptController(IInterruptController):
    """Simple interrupt controller with pub/sub semantics."""

    def __init__(self, clock: Optional[IClock] = None):
        self._clock = clock
        self._subscribers: List[object] = []
        self._cpu: Optional[InterruptTarget] = None
        self._pending: List[InterruptEvent] = []

    def subscribe(self, peripheral: object) -> None:
        if peripheral not in self._subscribers:
            self._subscribers.append(peripheral)

    def attach_cpu(self, cpu: InterruptTarget) -> None:
        self._cpu = cpu

    def notify(self, source: object, vector: int | None = None) -> InterruptEvent:
        timestamp = self._clock.cycle_count if self._clock is not None else None
        event = InterruptEvent(source=source, vector=vector, timestamp=timestamp)
        self._pending.append(event)
        if self._cpu is not None:
            self._cpu.handle_interrupt(event)
        return event

    def reset(self) -> None:
        self._pending.clear()
