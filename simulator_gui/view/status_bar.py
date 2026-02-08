"""Bottom status bar with system metrics."""

from __future__ import annotations

from PySide6 import QtWidgets

from simulator_gui.controller import StatusSample


class StatusBar(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self._cpu_label = QtWidgets.QLabel("CPU: --")
        self._mem_label = QtWidgets.QLabel("Mem: --")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.addWidget(self._cpu_label)
        layout.addWidget(self._mem_label)
        layout.addStretch(1)

    def update_status(self, sample: StatusSample) -> None:
        if sample.cpu_percent is None:
            self._cpu_label.setText("CPU: --")
        else:
            self._cpu_label.setText(f"CPU: {sample.cpu_percent:5.1f}%")

        if sample.memory_percent is None:
            self._mem_label.setText("Mem: --")
        else:
            self._mem_label.setText(f"Mem: {sample.memory_percent:5.1f}%")
