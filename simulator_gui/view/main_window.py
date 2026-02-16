"""Main GUI window."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from simulator_gui.config import GuiBoardConfig
from simulator_gui.controller import SimulationController, SimulationState
from simulator_gui.registry import ComponentInstance
from simulator_gui.view.board_canvas import BoardCanvas
from simulator_gui.view.register_panel import RegisterPanel
from simulator_gui.view.status_bar import StatusBar
from simulator_gui.view.top_bar import TopBar


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        controller: SimulationController,
        config: GuiBoardConfig,
        components: list[ComponentInstance],
        cycles_per_tick: int = 1000,
        tick_ms: int = 16,
        external_clock: bool = False,
    ):
        super().__init__()
        self._controller = controller
        self._config = config
        self._cycles_per_tick = cycles_per_tick

        self.setWindowTitle(f"{config.board_name} Simulator")

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self._top_bar = TopBar(config.board_name)
        self._board_canvas = BoardCanvas(config)
        self._board_canvas.set_components(components)
        self._register_panel = RegisterPanel()
        self._status_bar = StatusBar()

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(self._board_canvas)
        splitter.addWidget(self._register_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._top_bar)
        layout.addWidget(splitter, 1)
        layout.addWidget(self._status_bar)

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(tick_ms)

        if external_clock:
            self._controller.set_external(True)
        else:
            self._controller.set_running(True)
        self._top_bar.set_state(self._controller.state)

    def _tick(self) -> None:
        if self._controller.state == SimulationState.RUNNING:
            self._controller.step(self._cycles_per_tick)

        self._controller.update_components()
        self._register_panel.update_snapshot(self._controller.snapshot())
        self._status_bar.update_status(self._controller.status())
        self._top_bar.set_state(self._controller.state)
