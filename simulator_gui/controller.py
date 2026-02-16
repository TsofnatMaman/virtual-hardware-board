"""Simulation controller (Presenter-ish, framework-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterable

from simulator_gui.backend import SimulatorBackend
from simulator_gui.components.base import ComponentController
from simulator.interfaces.cpu import CpuSnapshot

try:
    import psutil  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    psutil = None


class SimulationState(Enum):
    RUNNING = auto()
    PAUSED = auto()
    EXTERNAL = auto()


@dataclass
class StatusSample:
    cpu_percent: float | None
    memory_percent: float | None


class SystemMonitor:
    """Process-level CPU/memory monitoring."""

    def __init__(self):
        self._proc = psutil.Process() if psutil else None
        if self._proc is not None:
            self._proc.cpu_percent(interval=None)

    def sample(self) -> StatusSample:
        if self._proc is None:
            return StatusSample(None, None)
        return StatusSample(
            cpu_percent=float(self._proc.cpu_percent(interval=None)),
            memory_percent=float(self._proc.memory_percent()),
        )


class SimulationController:
    """Coordinator for stepping the simulator and updating GUI components."""

    def __init__(
        self,
        backend: SimulatorBackend,
        components: Iterable[ComponentController],
    ):
        self._backend = backend
        self._components = list(components)
        for comp in self._components:
            comp.attach_backend(backend)
        self._state = SimulationState.PAUSED
        self._monitor = SystemMonitor()

    @property
    def state(self) -> SimulationState:
        return self._state

    def set_running(self, running: bool) -> None:
        self._state = SimulationState.RUNNING if running else SimulationState.PAUSED

    def set_external(self, external: bool) -> None:
        if external:
            self._state = SimulationState.EXTERNAL
        elif self._state == SimulationState.EXTERNAL:
            self._state = SimulationState.PAUSED

    def reset(self) -> None:
        self._backend.reset()

    def step(self, cycles: int) -> None:
        self._backend.step(cycles)

    def update_components(self) -> None:
        for comp in self._components:
            comp.update(self._backend)

    def snapshot(self) -> CpuSnapshot:
        return self._backend.cpu_snapshot()

    def status(self) -> StatusSample:
        return self._monitor.sample()
