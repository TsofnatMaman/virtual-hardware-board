"""Top bar with board name and state."""

from __future__ import annotations

from PySide6 import QtWidgets

from simulator_gui.controller import SimulationState


class TopBar(QtWidgets.QFrame):
    def __init__(self, board_name: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

        self._name_label = QtWidgets.QLabel(board_name)
        self._state_label = QtWidgets.QLabel("Paused")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.addWidget(self._name_label)
        layout.addStretch(1)
        layout.addWidget(self._state_label)

    def set_state(self, state: SimulationState) -> None:
        if state == SimulationState.RUNNING:
            label = "Running"
        elif state == SimulationState.EXTERNAL:
            label = "External"
        else:
            label = "Paused"
        self._state_label.setText(label)
