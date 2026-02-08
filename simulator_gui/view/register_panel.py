"""Register view panel."""

from __future__ import annotations

from PySide6 import QtWidgets

from simulator.interfaces.cpu import CpuSnapshot


class RegisterPanel(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._flags_label = QtWidgets.QLabel("FLAGS: --")
        self._table = QtWidgets.QTableWidget(self)
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Register", "Value"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self._table.setAlternatingRowColors(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._flags_label)
        layout.addWidget(self._table)

        self._reg_names: list[str] = []

    def update_snapshot(self, snapshot: CpuSnapshot) -> None:
        if snapshot.flags:
            flags = " ".join(f"{k}={int(v)}" for k, v in snapshot.flags.items())
            self._flags_label.setText(f"FLAGS: {flags}")
        else:
            self._flags_label.setText("FLAGS: --")

        regs = list(snapshot.registers)
        names = [r.name for r in regs]

        if names != self._reg_names:
            self._reg_names = names
            self._table.setRowCount(len(regs))
            for row, reg in enumerate(regs):
                name_item = QtWidgets.QTableWidgetItem(reg.name)
                value_item = QtWidgets.QTableWidgetItem("")
                self._table.setItem(row, 0, name_item)
                self._table.setItem(row, 1, value_item)

        for row, reg in enumerate(regs):
            value_item = self._table.item(row, 1)
            if value_item is not None:
                value_item.setText(f"0x{reg.value:08X}")
