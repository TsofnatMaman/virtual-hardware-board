"""GUI application entry point."""

from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path

from PySide6 import QtWidgets

from simulator import create_board, list_available_boards, verify_boards_registered
from simulator.debug import GdbRemoteServer, GdbTarget
from simulator_gui.backend import BoardBackend
from simulator_gui.config import load_gui_config
from simulator_gui.controller import SimulationController
from simulator_gui.registry import default_registry
from simulator_gui.view.main_window import MainWindow


def _available_boards() -> list[str]:
    verify_boards_registered()
    boards = sorted(list_available_boards())
    if not boards:
        raise RuntimeError("No boards registered")
    return boards

BOARD_NAME_TO_KEY = {
    "STM32F4": "stm32f4",
    "STM32C031": "stm32c031",
    "TM4C123": "tm4c123",
}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    boards = _available_boards()
    default_board = "tm4c123" if "tm4c123" in boards else boards[0]

    parser = argparse.ArgumentParser(description="Virtual Hardware Board GUI")
    parser.add_argument("--board", default=default_board, choices=boards)
    parser.add_argument("--gui-config", default=None, help="Path to GUI config YAML")
    parser.add_argument("--firmware", default=None, help="Path to firmware.bin")
    parser.add_argument("--cycles", type=int, default=1000, help="Cycles per GUI tick")
    parser.add_argument(
        "--tick-ms", type=int, default=16, help="GUI tick interval (ms)"
    )
    parser.add_argument(
        "--gdb-port",
        type=int,
        default=None,
        help="Enable in-process GDB server on this port",
    )
    parser.add_argument(
        "--gdb-host",
        default="127.0.0.1",
        help="Bind host for in-process GDB server",
    )
    parser.add_argument(
        "--gdb-max-continue-steps",
        type=int,
        default=0,
        help="Instruction budget per GDB continue (0 = unlimited, Ctrl+C stops)",
    )
    return parser.parse_args(argv)


def _resolve_board_key(board_key: str | None, board_name: str | None) -> str | None:
    if board_key:
        return board_key
    if board_name:
        return BOARD_NAME_TO_KEY.get(board_name)
    return None


def run_gui(
    argv: list[str] | None = None,
    *,
    board=None,
    board_key: str | None = None,
    lock=None,
    external_clock: bool = False,
) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    if board is None:
        board = create_board(args.board)
        board_key = args.board

        if args.firmware:
            firmware = Path(args.firmware).read_bytes()
            board.address_space.flash.load_image(firmware)
            board.reset()

    resolved_key = _resolve_board_key(board_key, getattr(board, "name", None))
    if resolved_key is None:
        raise ValueError("Unable to resolve board key for GUI config.")

    config_path = args.gui_config
    if config_path is None:
        config_path = Path(__file__).parent / "boards" / f"{resolved_key}.yaml"
    gui_config = load_gui_config(config_path)

    registry = default_registry()
    component_instances = [registry.create(c) for c in gui_config.components]
    controllers = [c.controller for c in component_instances]

    if lock is None and args.gdb_port is not None:
        lock = threading.RLock()
    # With a debugger attached it owns the clock: the GUI only repaints.
    external_clock = external_clock or args.gdb_port is not None

    backend = BoardBackend(board, lock=lock)
    controller = SimulationController(backend, controllers)

    gdb_stop_event = None
    gdb_thread = None
    if args.gdb_port is not None:
        gdb_stop_event = threading.Event()
        gdb_server = GdbRemoteServer(
            target=GdbTarget(
                board,
                max_continue_steps=args.gdb_max_continue_steps,
                lock=lock,
            ),
            host=args.gdb_host,
            port=args.gdb_port,
        )
        gdb_thread = threading.Thread(
            target=gdb_server.serve_forever,
            kwargs={"stop_event": gdb_stop_event},
            daemon=True,
            name="sim-gdb-server",
        )
        gdb_thread.start()

    # Qt's event loop blocks Python's SIGINT handling; restore the default so
    # Ctrl+C in the terminal quits the simulator as users expect.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(
        controller,
        gui_config,
        component_instances,
        cycles_per_tick=args.cycles,
        tick_ms=args.tick_ms,
        external_clock=external_clock,
    )
    window.resize(gui_config.canvas.width + 300, gui_config.canvas.height + 120)
    window.show()
    exit_code = app.exec()

    if gdb_stop_event is not None:
        gdb_stop_event.set()
    if gdb_thread is not None:
        gdb_thread.join(timeout=1.0)

    return exit_code


def main() -> None:
    raise SystemExit(run_gui())


if __name__ == "__main__":
    main()
