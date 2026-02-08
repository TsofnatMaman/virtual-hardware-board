"""GUI application entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6 import QtWidgets

from simulator_gui.backend import BoardBackend
from simulator_gui.config import load_gui_config
from simulator_gui.controller import SimulationController
from simulator_gui.registry import default_registry
from simulator_gui.view.main_window import MainWindow
from simulator.stm32.board import STM32F4Board
from simulator.stm32c031.board import STM32C031Board
from simulator.tm4c.board import TM4C123Board


BOARD_MAP = {
    "stm32f4": STM32F4Board,
    "stm32c031": STM32C031Board,
    "tm4c123": TM4C123Board,
}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Virtual Hardware Board GUI")
    parser.add_argument("--board", default="tm4c123", choices=BOARD_MAP.keys())
    parser.add_argument("--gui-config", default=None, help="Path to GUI config YAML")
    parser.add_argument("--firmware", default=None, help="Path to firmware.bin")
    parser.add_argument("--cycles", type=int, default=1000, help="Cycles per GUI tick")
    parser.add_argument("--tick-ms", type=int, default=16, help="GUI tick interval (ms)")
    return parser.parse_args(argv)


def run_gui(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])

    board_cls = BOARD_MAP[args.board]
    board = board_cls()

    if args.firmware:
        firmware = Path(args.firmware).read_bytes()
        board.address_space.flash.load_image(firmware)
        board.reset()

    config_path = args.gui_config
    if config_path is None:
        config_path = Path(__file__).parent / "boards" / f"{args.board}.yaml"
    gui_config = load_gui_config(config_path)

    registry = default_registry()
    component_instances = [registry.create(c) for c in gui_config.components]
    controllers = [c.controller for c in component_instances]

    backend = BoardBackend(board)
    controller = SimulationController(backend, controllers)

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(
        controller,
        gui_config,
        component_instances,
        cycles_per_tick=args.cycles,
        tick_ms=args.tick_ms,
    )
    window.resize(gui_config.canvas.width + 300, gui_config.canvas.height + 120)
    window.show()
    return app.exec()


def main() -> None:
    raise SystemExit(run_gui())


if __name__ == "__main__":
    main()
