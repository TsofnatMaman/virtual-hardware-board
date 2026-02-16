"""TCP debug server for external debuggers.

Can optionally launch the GUI for the same board instance.
"""

from __future__ import annotations

import argparse
import json
import socketserver
import threading
from pathlib import Path

from simulator import STM32C031Board, STM32F4Board, TM4C123Board
from simulator.core.board import (
    create_board,
    list_available_boards,
    verify_boards_registered,
)
from simulator.debug.session import DebugSession


class _DebugHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        session: DebugSession = self.server.session  # type: ignore[attr-defined]
        while True:
            line = self.rfile.readline()
            if not line:
                break
            try:
                request = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError as exc:
                response = {"ok": False, "error": f"Invalid JSON: {exc}"}
            else:
                response = session.handle_request(request)

            self.wfile.write((json.dumps(response) + "\n").encode("utf-8"))


class DebugServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, host: str, port: int, session: DebugSession):
        super().__init__((host, port), _DebugHandler)
        self.session = session


def _load_firmware(board, firmware_path: str | None) -> None:
    if not firmware_path:
        return
    data = Path(firmware_path).read_bytes()
    board.address_space.flash.load_image(data)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Virtual hardware board debug server")
    parser.add_argument("--board", required=True, help="Board name to simulate")
    parser.add_argument("--firmware", help="Firmware .bin to load into flash")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=3333, help="Bind port (default: 3333)"
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run headless (do not launch GUI)",
    )
    return parser.parse_args()


def _run_with_gui(
    board, board_key: str, session: DebugSession, lock: threading.RLock, args: argparse.Namespace
) -> int:
    try:
        from simulator_gui.app import run_gui
    except Exception as exc:  # pragma: no cover - optional GUI dependency
        print(f"GUI unavailable: {exc}")
        server = DebugServer(args.host, args.port, session)
        print(f"Debug server listening on {args.host}:{args.port} (board={board_key})")
        server.serve_forever()
        return 0

    server = DebugServer(args.host, args.port, session)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Debug server listening on {args.host}:{args.port} (board={board_key})")
    try:
        return run_gui(
            ["--board", board_key],
            board=board,
            board_key=board_key,
            lock=lock,
            external_clock=True,
        )
    finally:
        server.shutdown()
        server.server_close()


def main() -> int:
    # Ensure boards are registered
    _ = (STM32F4Board, TM4C123Board, STM32C031Board)
    verify_boards_registered()

    args = _parse_args()
    if args.board not in list_available_boards():
        raise SystemExit(
            f"Unknown board '{args.board}'. Available: {list_available_boards()}"
        )

    board = create_board(args.board)
    _load_firmware(board, args.firmware)
    board.reset()

    lock = threading.RLock()
    session = DebugSession(board, lock=lock)

    if not args.no_gui:
        return _run_with_gui(board, args.board, session, lock, args)

    server = DebugServer(args.host, args.port, session)
    print(f"Debug server listening on {args.host}:{args.port} (board={args.board})")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
