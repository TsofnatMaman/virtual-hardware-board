"""Momentary button component."""

from __future__ import annotations

from PySide6 import QtCore, QtGui

from simulator_gui.backend import SimulatorBackend
from simulator_gui.components.base import ComponentController, ComponentGraphicsItem
from simulator_gui.config import HardwareBinding


class ButtonView(ComponentGraphicsItem):
    pressed = QtCore.Signal()
    released = QtCore.Signal()

    def __init__(
        self,
        size: tuple[int, int] = (26, 26),
        on_color: str = "#f59e0b",
        off_color: str = "#2f2f2f",
        border_color: str = "#111111",
    ):
        super().__init__(size=size)
        self._pressed = False
        self._on_color = QtGui.QColor(on_color)
        self._off_color = QtGui.QColor(off_color)
        self._border_color = QtGui.QColor(border_color)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

    def paint(self, painter: QtGui.QPainter, _option, _widget=None) -> None:  # type: ignore[override]
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = self.boundingRect().adjusted(1, 1, -1, -1)
        color = self._on_color if self._pressed else self._off_color
        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(QtGui.QPen(self._border_color, 1))
        painter.drawRoundedRect(rect, 4, 4)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._pressed = True
        self.update()
        self.pressed.emit()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        self._pressed = False
        self.update()
        self.released.emit()
        super().mouseReleaseEvent(event)


class ButtonController(ComponentController):
    """Controller for momentary button (writes on press/release)."""

    def __init__(self, component_id: str, binding: HardwareBinding, view: ButtonView):
        super().__init__(component_id, binding)
        self._view = view
        view.pressed.connect(self._on_press)
        view.released.connect(self._on_release)

    @property
    def view(self) -> ButtonView:
        return self._view

    def update(self, backend: SimulatorBackend) -> None:
        # No periodic update needed for momentary input.
        _ = backend

    def _on_press(self) -> None:
        self._write_value(True)

    def _on_release(self) -> None:
        self._write_value(False)

    def _write_value(self, active: bool) -> None:
        if self.binding.direction not in ("input", "bidirectional"):
            return
        if self._backend is None:
            return
        current = self._backend.read(self.binding.address, self.binding.size)
        if active:
            value = current | self.binding.mask
        else:
            value = current & ~self.binding.mask
        self._backend.write(self.binding.address, self.binding.size, value)
