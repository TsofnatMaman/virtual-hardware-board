"""Toggle switch component."""

from __future__ import annotations

from PySide6 import QtCore, QtGui

from simulator_gui.backend import SimulatorBackend
from simulator_gui.components.base import ComponentController, ComponentGraphicsItem
from simulator_gui.config import HardwareBinding


class SwitchView(ComponentGraphicsItem):
    toggled = QtCore.Signal(bool)

    def __init__(
        self,
        size: tuple[int, int] = (26, 26),
        on_color: str = "#10b981",
        off_color: str = "#2f2f2f",
        border_color: str = "#111111",
    ):
        super().__init__(size=size)
        self._on = False
        self._on_color = QtGui.QColor(on_color)
        self._off_color = QtGui.QColor(off_color)
        self._border_color = QtGui.QColor(border_color)
        self.setAcceptedMouseButtons(QtCore.Qt.LeftButton)

    def set_on(self, value: bool) -> None:
        if self._on != value:
            self._on = value
            self.update()

    def paint(self, painter: QtGui.QPainter, _option, _widget=None) -> None:  # type: ignore[override]
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        rect = self.boundingRect().adjusted(1, 1, -1, -1)
        color = self._on_color if self._on else self._off_color
        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(QtGui.QPen(self._border_color, 1))
        painter.drawRoundedRect(rect, 6, 6)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        self._on = not self._on
        self.update()
        self.toggled.emit(self._on)
        super().mousePressEvent(event)


class SwitchController(ComponentController):
    """Controller for toggle switch (writes on toggle)."""

    def __init__(self, component_id: str, binding: HardwareBinding, view: SwitchView):
        super().__init__(component_id, binding)
        self._view = view
        view.toggled.connect(self._on_toggled)

    @property
    def view(self) -> SwitchView:
        return self._view

    def update(self, backend: SimulatorBackend) -> None:
        if self.binding.direction not in ("output", "bidirectional"):
            return
        value = backend.read(self.binding.address, self.binding.size)
        on = bool(value & self.binding.mask) if self.binding.mask else bool(value)
        if self.binding.invert:
            on = not on
        self._view.set_on(on)

    def _on_toggled(self, on: bool) -> None:
        if self.binding.direction not in ("input", "bidirectional"):
            return
        if self._backend is None:
            return
        current = self._backend.read(self.binding.address, self.binding.size)
        if on:
            value = current | self.binding.mask
        else:
            value = current & ~self.binding.mask
        self._backend.write(self.binding.address, self.binding.size, value)
