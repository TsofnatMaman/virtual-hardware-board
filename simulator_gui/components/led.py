"""LED GUI component."""

from __future__ import annotations

from PySide6 import QtCore, QtGui

from simulator_gui.backend import SimulatorBackend
from simulator_gui.components.base import ComponentController, ComponentGraphicsItem
from simulator_gui.config import HardwareBinding


class LedView(ComponentGraphicsItem):
    """Visual LED element."""

    def __init__(
        self,
        size: tuple[int, int] = (20, 20),
        on_color: str = "#ff3b30",
        off_color: str = "#3a0f0f",
        border_color: str = "#111111",
    ):
        super().__init__(size=size)
        self._on = False
        self._on_color = QtGui.QColor(on_color)
        self._off_color = QtGui.QColor(off_color)
        self._border_color = QtGui.QColor(border_color)

    def set_on(self, value: bool) -> None:
        if self._on != value:
            self._on = value
            self.update()

    def paint(self, painter: QtGui.QPainter, _option, _widget=None) -> None:  # type: ignore[override]
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = self.boundingRect().adjusted(1, 1, -1, -1)
        color = self._on_color if self._on else self._off_color

        gradient = QtGui.QRadialGradient(rect.center(), rect.width() / 2)
        gradient.setColorAt(0.0, color.lighter(140))
        gradient.setColorAt(1.0, color.darker(130))

        painter.setBrush(QtGui.QBrush(gradient))
        painter.setPen(QtGui.QPen(self._border_color, 1))
        painter.drawEllipse(rect)


class LedController(ComponentController):
    """Controller for LED state (read-only output)."""

    def __init__(self, component_id: str, binding: HardwareBinding, view: LedView):
        super().__init__(component_id, binding)
        self._view = view

    @property
    def view(self) -> LedView:
        return self._view

    def update(self, backend: SimulatorBackend) -> None:
        value = backend.read(self.binding.address, self.binding.size)
        on = bool(value & self.binding.mask) if self.binding.mask else bool(value)
        if self.binding.invert:
            on = not on
        self._view.set_on(on)
