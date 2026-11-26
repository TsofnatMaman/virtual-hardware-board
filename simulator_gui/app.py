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
from simulator.debug.defaults import DEFAULT_HOST
from simulator_gui.backend import BoardBackend
from simulator_gui.config import load_gui_config
from simulator_gui.controller import SimulationController
from simulator_gui.registry import default_registry
from simulator_gui.view.main_window import MainWindow

REGISTER_PANEL_WIDTH = 300  # the register table next to the board
BARS_HEIGHT = 120  # top bar + status bar
GDB_THREAD_NAME = "sim-gdb-server"
GDB_JOIN_TIMEOUT_S = 1.0


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
        default=DEFAULT_HOST,
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


def _make_board(args: argparse.Namespace):
    """The board named on the command line, with `--firmware` loaded."""
    board = create_board(args.board)
    if args.firmware:
        board.address_space.flash.load_image(Path(args.firmware).read_bytes())
        board.reset()
    return board


def _load_layout(args: argparse.Namespace, board, board_key: str | None):
    key = _resolve_board_key(board_key, getattr(board, "name", None))
    if key is None:
        raise ValueError("Unable to resolve board key for GUI config.")
    return load_gui_config(
        args.gui_config or Path(__file__).parent / "boards" / f"{key}.yaml"
    )


def _start_gdb_server(board, args: argparse.Namespace, lock):
    """Serve GDB in a background thread; returns (stop event, thread)."""
    stop = threading.Event()
    target = GdbTarget(board, max_continue_steps=args.gdb_max_continue_steps, lock=lock)
    server = GdbRemoteServer(target=target, host=args.gdb_host, port=args.gdb_port)
    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"stop_event": stop},
        daemon=True,
        name=GDB_THREAD_NAME,
    )
    thread.start()
    return stop, thread


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
        board, board_key = _make_board(args), args.board
    layout = _load_layout(args, board, board_key)
    instances = [default_registry().create(c) for c in layout.components]

    debugger = args.gdb_port is not None
    lock = lock or (threading.RLock() if debugger else None)
    controller = SimulationController(
        BoardBackend(board, lock=lock), [i.controller for i in instances]
    )
    gdb = _start_gdb_server(board, args, lock) if debugger else None

    # Qt's event loop blocks Python's SIGINT handling; restore the default so
    # Ctrl+C in the terminal quits the simulator as users expect.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QtWidgets.QApplication(sys.argv)
    # With a debugger attached it owns the clock: the GUI only repaints.
    window = MainWindow(
        controller, layout, instances, cycles_per_tick=args.cycles, tick_ms=args.tick_ms,
        external_clock=external_clock or debugger,
    )  # fmt: skip
    window.resize(
        layout.canvas.width + REGISTER_PANEL_WIDTH, layout.canvas.height + BARS_HEIGHT
    )
    window.show()
    exit_code = app.exec()

    if gdb:
        gdb[0].set()
        gdb[1].join(timeout=GDB_JOIN_TIMEOUT_S)
    return exit_code


def main() -> None:
    raise SystemExit(run_gui())


if __name__ == "__main__":
    main()
