"""Minimal GDB Remote Serial Protocol server for simulator boards.

This module provides enough of the remote protocol for source-level debugging
from VS Code (or plain gdb) against a running simulator board.
"""

from __future__ import annotations

import argparse
import select
import socket
import threading
from dataclasses import dataclass, field
from pathlib import Path

from simulator import create_board
from simulator.core.exceptions import SimulatorError
from simulator.debug.session import DebugSession, StopReason
from simulator.interfaces.board import Board

_SIGNAL_TRAP = "S05"
_STOP_REPLY = "T05thread:1;"
_STOP_INTERRUPT = "T02thread:1;"  # SIGINT, reply to Ctrl+C
_WATCH_PREFIX = {"write": "watch", "read": "rwatch", "access": "awatch"}
_WATCH_PACKET_KIND = {"2": "write", "3": "read", "4": "access"}
_CTRL_C = b"\x03"


def stop_reply(stop: StopReason) -> str:
    """Translate a session stop into a GDB stop-reply packet."""
    if stop.reason == "halt":
        return _STOP_INTERRUPT
    if stop.reason == "watchpoint" and stop.address is not None:
        prefix = _WATCH_PREFIX.get(stop.watch_kind or "", "watch")
        return f"T05{prefix}:{stop.address:x};thread:1;"
    return _STOP_REPLY


@dataclass
class GdbTarget:
    """GDB-facing adapter over the shared :class:`DebugSession`."""

    board: Board
    max_continue_steps: int = 0  # 0 = unlimited (Ctrl+C halts)
    lock: threading.RLock | None = None
    session: DebugSession = field(init=False)

    def __post_init__(self) -> None:
        self.session = DebugSession(self.board, lock=self.lock)

    @property
    def breakpoints(self) -> set[int]:
        return self.session.breakpoints

    @property
    def _needs_reset(self) -> bool:
        return self.session.needs_reset

    def read_registers(self) -> bytes:
        values = self.session.read_core_registers()
        return b"".join(value.to_bytes(4, "little") for value in values)

    def write_registers(self, payload: bytes) -> bool:
        if len(payload) < 17 * 4:
            return False
        for idx in range(16):
            value = int.from_bytes(payload[idx * 4 : (idx + 1) * 4], "little")
            self.session.write_register(idx, value)
        return True

    def read_memory(self, address: int, length: int) -> bytes | None:
        try:
            return self.session.read_memory(address, length)
        except (SimulatorError, ValueError):
            return None

    def write_memory(self, address: int, data: bytes) -> bool:
        try:
            self.session.write_memory(address, data)
        except (SimulatorError, ValueError):
            return False
        return True

    def restart(self) -> str:
        self.session.reset()
        return _SIGNAL_TRAP

    def set_pc(self, address: int) -> None:
        self.session.set_pc(address)

    def step(self) -> str:
        stop = self.session.step()
        return stop_reply(stop) if stop.reason == "watchpoint" else _SIGNAL_TRAP

    def cont(self) -> str:
        max_steps = self.max_continue_steps if self.max_continue_steps > 0 else None
        return stop_reply(self.session.run(max_steps=max_steps))

    def halt(self) -> None:
        """Interrupt a running :meth:`cont` (thread-safe)."""
        self.session.request_halt()

    def set_watchpoint(self, kind: str, address: int, size: int) -> bool:
        try:
            self.session.add_watchpoint(address, size, kind)
        except (NotImplementedError, ValueError):
            return False
        return True

    def clear_watchpoint(self, kind: str, address: int, size: int) -> bool:
        return self.session.remove_watchpoint(address, size, kind)


class GdbRemoteServer:
    """Tiny single-client GDB remote server."""

    def __init__(self, target: GdbTarget, host: str = "127.0.0.1", port: int = 3333):
        self.target = target
        self.host = host
        self.port = port
        self._conn: socket.socket | None = None

    @staticmethod
    def _checksum(payload: str) -> str:
        return f"{sum(payload.encode('latin-1')) & 0xFF:02x}"

    def _send_packet(self, conn: socket.socket, payload: str) -> None:
        packet = f"${payload}#{self._checksum(payload)}".encode("ascii")
        conn.sendall(packet)

    def _recv_until_packet_start(self, conn: socket.socket) -> bool:
        while True:
            char = conn.recv(1)
            if not char:
                return False
            if char == b"+":
                continue
            if char == b"$":
                return True

    def _recv_payload(self, conn: socket.socket) -> str | None:
        data = bytearray()
        while True:
            char = conn.recv(1)
            if not char:
                return None
            if char == b"#":
                return data.decode("latin-1")
            data.extend(char)

    def _read_packet(self, conn: socket.socket) -> str | None:
        if not self._recv_until_packet_start(conn):
            return None

        payload = self._recv_payload(conn)
        if payload is None:
            return None

        received_checksum = conn.recv(2)
        expected = self._checksum(payload).encode("latin-1")
        if received_checksum.lower() != expected:
            conn.sendall(b"-")
            return None

        conn.sendall(b"+")
        return payload

    def _handle_monitor(self, payload: str) -> str:
        """Handle ``qRcmd`` (gdb ``monitor ...``) commands."""
        try:
            command = bytes.fromhex(payload[len("qRcmd,") :]).decode("ascii").strip()
        except ValueError:
            return "E01"
        words = command.split()
        if not words:
            return "OK"
        if words[0] in {"reset", "halt"}:
            if words[0] == "reset":
                self.target.restart()
            return "OK"
        return ""

    def _handle_query(self, payload: str) -> str:
        if payload.startswith("qRcmd,"):
            return self._handle_monitor(payload)
        if payload.startswith("qSupported"):
            return "PacketSize=4000;swbreak+;hwbreak-"
        if payload in {"qAttached", "qC"}:
            return "1"
        if payload.startswith("qfThreadInfo"):
            return "m1"
        if payload.startswith("qsThreadInfo"):
            return "l"
        if payload.startswith("qTStatus"):
            return ""
        return ""

    @staticmethod
    def _decode_x_payload(raw: str) -> bytes:
        data = raw.encode("latin-1")
        out = bytearray()
        idx = 0
        while idx < len(data):
            byte = data[idx]
            if byte == 0x7D and idx + 1 < len(data):
                idx += 1
                out.append(data[idx] ^ 0x20)
            else:
                out.append(byte)
            idx += 1
        return bytes(out)

    def _handle_register_ops(self, payload: str) -> str | None:
        if payload == "g":
            return self.target.read_registers().hex()
        if payload.startswith("G"):
            success = self.target.write_registers(bytes.fromhex(payload[1:]))
            return "OK" if success else "E01"
        return None

    def _handle_memory_ops(self, payload: str) -> str | None:
        if payload.startswith("m"):
            addr_hex, length_hex = payload[1:].split(",", maxsplit=1)
            data = self.target.read_memory(int(addr_hex, 16), int(length_hex, 16))
            return data.hex() if data is not None else "E01"

        if payload.startswith("M"):
            header, data_hex = payload[1:].split(":", maxsplit=1)
            addr_hex, _length_hex = header.split(",", maxsplit=1)
            success = self.target.write_memory(
                int(addr_hex, 16), bytes.fromhex(data_hex)
            )
            return "OK" if success else "E02"

        if payload.startswith("X"):
            header, raw_data = payload[1:].split(":", maxsplit=1)
            addr_hex, _length_hex = header.split(",", maxsplit=1)
            data = self._decode_x_payload(raw_data)
            success = self.target.write_memory(int(addr_hex, 16), data)
            return "OK" if success else "E03"

        return None

    def _interrupt_requested(self, conn: socket.socket) -> bool:
        """True if the client sent Ctrl+C (0x03) or closed the connection."""
        ready, _, _ = select.select([conn], [], [], 0)
        if not ready:
            return False
        try:
            data = conn.recv(1)
        except OSError:
            return True
        return data == _CTRL_C or data == b""

    def _resume(self) -> str:
        """Continue execution, stopping early on Ctrl+C from the client."""
        conn = self._conn
        if conn is None:
            return self.target.cont()

        result: list[str] = []
        worker = threading.Thread(
            target=lambda: result.append(self.target.cont()),
            daemon=True,
            name="sim-gdb-run",
        )
        worker.start()
        while worker.is_alive():
            if self._interrupt_requested(conn):
                self.target.halt()
                break
            worker.join(0.01)
        worker.join()
        return result[0]

    def _handle_exec_ops(self, payload: str) -> str | None:
        if payload.startswith("c"):
            if len(payload) > 1:
                self.target.set_pc(int(payload[1:], 16))
            return self._resume()

        if payload.startswith("s"):
            if len(payload) > 1:
                self.target.set_pc(int(payload[1:], 16))
            return self.target.step()

        if payload == "?":
            return _SIGNAL_TRAP

        return None

    def _handle_watchpoint_ops(self, payload: str) -> str | None:
        """Handle ``Z2/Z3/Z4`` (write/read/access watch) and ``z2/z3/z4``."""
        if len(payload) < 2 or payload[0] not in "Zz" or payload[1] not in "234":
            return None
        kind = _WATCH_PACKET_KIND[payload[1]]
        parts = payload.split(",")
        try:
            address, size = int(parts[1], 16), int(parts[2], 16)
        except (IndexError, ValueError):
            return "E01"
        if payload[0] == "Z":
            return "OK" if self.target.set_watchpoint(kind, address, size) else ""
        self.target.clear_watchpoint(kind, address, size)
        return "OK"

    def _handle_breakpoint_ops(self, payload: str) -> str | None:
        if payload.startswith("Z0,"):
            address = int(payload.split(",", maxsplit=2)[1], 16)
            self.target.breakpoints.add(address & 0xFFFFFFFE)
            return "OK"

        if payload.startswith("z0,"):
            address = int(payload.split(",", maxsplit=2)[1], 16)
            self.target.breakpoints.discard(address & 0xFFFFFFFE)
            return "OK"

        return None

    def _handle_vcont(self, payload: str) -> str | None:
        if payload.startswith("vCont?"):
            return "vCont;c;s"
        if payload.startswith("vCont;"):
            if ";s" in payload:
                return self.target.step()
            return self._resume()
        return None

    def _handle_packet(self, payload: str) -> str:
        if payload.startswith("q"):
            return self._handle_query(payload)

        for handler in (
            self._handle_register_ops,
            self._handle_memory_ops,
            self._handle_exec_ops,
            self._handle_breakpoint_ops,
            self._handle_watchpoint_ops,
            self._handle_vcont,
        ):
            response = handler(payload)
            if response is not None:
                return response

        if payload in {"Hc0", "Hg0", "D"}:
            return "OK"
        if payload == "R":
            return self.target.restart()
        if payload in {"k", "!"}:
            return ""

        return ""

    def _safe_handle_packet(self, payload: str) -> str:
        """Never let one bad packet drop the debugger connection."""
        try:
            return self._handle_packet(payload)
        except (SimulatorError, ValueError, RuntimeError) as exc:
            print(f"[gdb] error handling '{payload[:32]}': {exc}")
            return "E01"

    def serve_forever(
        self,
        stop_event: threading.Event | None = None,
        poll_timeout_s: float = 0.2,
    ) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            server.settimeout(poll_timeout_s)
            print(f"[gdb] listening on {self.host}:{self.port}")

            while True:
                if stop_event is not None and stop_event.is_set():
                    break

                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue

                print(f"[gdb] client connected: {addr[0]}:{addr[1]}")
                self._conn = conn
                with conn:
                    while True:
                        payload = self._read_packet(conn)
                        if payload is None:
                            break
                        response = self._safe_handle_packet(payload)
                        if payload == "k":
                            break
                        self._send_packet(conn, response)
                self._conn = None
                print("[gdb] client disconnected")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GDB remote server for simulator")
    parser.add_argument("--board", default="tm4c123", help="Board key in registry")
    parser.add_argument(
        "--firmware", default=None, help="Optional path to firmware .bin"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=3333, help="Bind port")
    parser.add_argument(
        "--max-continue-steps",
        type=int,
        default=0,
        help="Instruction budget per continue (0 = unlimited, stop with Ctrl+C)",
    )
    return parser.parse_args()


def build_target(
    board_name: str, firmware_path: str | None, max_continue_steps: int
) -> GdbTarget:
    board = create_board(board_name)
    if firmware_path:
        firmware = Path(firmware_path).read_bytes()
        board.address_space.flash.load_image(firmware)
        board.reset()
    return GdbTarget(board=board, max_continue_steps=max_continue_steps)


def main() -> None:
    args = parse_args()
    target = build_target(args.board, args.firmware, args.max_continue_steps)
    GdbRemoteServer(target=target, host=args.host, port=args.port).serve_forever()


if __name__ == "__main__":
    main()
