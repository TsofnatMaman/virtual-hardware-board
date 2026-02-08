"""Base classes for GUI components."""

from __future__ import annotations

from abc import ABC, abstractmethod

from PySide6 import QtCore, QtWidgets

from simulator_gui.backend import SimulatorBackend
from simulator_gui.config import HardwareBinding, Rect


class ComponentController(ABC):
    """Non-UI logic for a component (pure business logic)."""

    def __init__(self, component_id: str, binding: HardwareBinding):
        self.component_id = component_id
        self.binding = binding
        self._backend: SimulatorBackend | None = None

    def attach_backend(self, backend: SimulatorBackend) -> None:
        self._backend = backend

    @abstractmethod
    def update(self, backend: SimulatorBackend) -> None:
        ...


class ComponentGraphicsItem(QtWidgets.QGraphicsObject):
    """Shared base for all visual components."""

    def __init__(self, size: tuple[int, int] = (24, 24)):
        super().__init__()
        self._rect = QtCore.QRectF(0, 0, float(size[0]), float(size[1]))

    def set_rect(self, rect: Rect) -> None:
        self.prepareGeometryChange()
        self.setPos(rect.x, rect.y)
        self._rect = QtCore.QRectF(0, 0, rect.width, rect.height)
        self.update()

    def boundingRect(self) -> QtCore.QRectF:  # type: ignore[override]
        return self._rect
