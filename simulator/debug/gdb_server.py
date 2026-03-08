"""Minimal GDB Remote Serial Protocol server for simulator boards.

This module provides enough of the remote protocol for source-level debugging
from VS Code (or plain gdb) against a running simulator board.
"""

from __future__ import annotations

import argparse
import socket
from dataclasses import dataclass, field
from pathlib import Path

from simulator import create_board
from simulator.core.exceptions import SimulatorError
from simulator.interfaces.board import Board

_SIGNAL_TRAP = "S05"
_STOP_REPLY = "T05thread:1;"


@dataclass
class GdbTarget:
    """Wrap a board and expose debugger-friendly primitives."""

    board: Board
    max_continue_steps: int = 250_000
    breakpoints: set[int] = field(default_factory=set)

    def _canonical_pc(self, value: int) -> int:
        return value & 0xFFFFFFFE

    def read_registers(self) -> bytes:
        regs = [self.board.cpu.get_register(i) & 0xFFFFFFFF for i in range(16)]
        snapshot = self.board.cpu.get_snapshot()
        xpsr = next((r.value for r in snapshot.registers if r.name == "XPSR"), 0)
        regs.append(xpsr & 0xFFFFFFFF)
        return b"".join(value.to_bytes(4, "little") for value in regs)

    def write_registers(self, payload: bytes) -> bool:
        if len(payload) < 17 * 4:
            return False
        for idx in range(16):
            value = int.from_bytes(payload[idx * 4 : (idx + 1) * 4], "little")
            self.board.cpu.set_register(idx, value)
        return True

    def read_memory(self, address: int, length: int) -> bytes | None:
        data = bytearray()
        for offset in range(length):
            try:
                data.append(self.board.read(address + offset, 1))
            except (SimulatorError, ValueError):
                return None
        return bytes(data)

    def write_memory(self, address: int, data: bytes) -> bool:
        for offset, byte in enumerate(data):
            try:
                self.board.write(address + offset, 1, byte)
            except (SimulatorError, ValueError):
                return False
        return True

    def set_pc(self, address: int) -> None:
        self.board.cpu.set_register(15, address | 1)

    def step(self) -> str:
        self.board.step(1)
        return _SIGNAL_TRAP

    def cont(self) -> str:
        for _ in range(self.max_continue_steps):
            pc = self._canonical_pc(self.board.cpu.get_register(15))
            if pc in self.breakpoints:
                return _STOP_REPLY
            self.board.step(1)
        return _STOP_REPLY


class GdbRemoteServer:
    """Tiny single-client GDB remote server."""

    def __init__(self, target: GdbTarget, host: str = "127.0.0.1", port: int = 3333):
        self.target = target
        self.host = host
        self.port = port

    @staticmethod
    def _checksum(payload: str) -> str:
        return f"{sum(payload.encode('ascii')) & 0xFF:02x}"

    def _send_packet(self, conn: socket.socket, payload: str) -> None:
        packet = f"${payload}#{self._checksum(payload)}".encode("ascii")
        conn.sendall(packet)

    def _read_packet(self, conn: socket.socket) -> str | None:
        while True:
            char = conn.recv(1)
            if not char:
                return None
            if char == b"+":
                continue
            if char == b"$":
                break

        data = bytearray()
        while True:
            char = conn.recv(1)
            if not char:
                return None
            if char == b"#":
                break
            data.extend(char)

        received_checksum = conn.recv(2)
        payload = data.decode("ascii")
        expected = self._checksum(payload).encode("ascii")
        if received_checksum.lower() != expected:
            conn.sendall(b"-")
            return None

        conn.sendall(b"+")
        return payload

    def _handle_query(self, payload: str) -> str:
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
            return ""

        return None

    def _handle_exec_ops(self, payload: str) -> str | None:
        if payload.startswith("c"):
            if len(payload) > 1:
                self.target.set_pc(int(payload[1:], 16))
            return self.target.cont()

        if payload.startswith("s"):
            if len(payload) > 1:
                self.target.set_pc(int(payload[1:], 16))
            return self.target.step()

        if payload == "?":
            return _SIGNAL_TRAP

        return None

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
            return self.target.cont()
        return None

    def _handle_packet(self, payload: str) -> str:
        if payload.startswith("q"):
            return self._handle_query(payload)

        for handler in (
            self._handle_register_ops,
            self._handle_memory_ops,
            self._handle_exec_ops,
            self._handle_breakpoint_ops,
            self._handle_vcont,
        ):
            response = handler(payload)
            if response is not None:
                return response

        if payload in {"Hc0", "Hg0", "D"}:
            return "OK"
        if payload in {"k", "!"}:
            return ""

        return ""

    def serve_forever(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(1)
            print(f"[gdb] listening on {self.host}:{self.port}")

            while True:
                conn, addr = server.accept()
                print(f"[gdb] client connected: {addr[0]}:{addr[1]}")
                with conn:
                    while True:
                        payload = self._read_packet(conn)
                        if payload is None:
                            break
                        response = self._handle_packet(payload)
                        if payload == "k":
                            break
                        self._send_packet(conn, response)
                print("[gdb] client disconnected")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GDB remote server for simulator")
    parser.add_argument("--board", default="tm4c123", help="Board key in registry")
    parser.add_argument("--firmware", required=True, help="Path to firmware .bin")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host")
    parser.add_argument("--port", type=int, default=3333, help="Bind port")
    parser.add_argument(
        "--max-continue-steps",
        type=int,
        default=250_000,
        help="Instruction budget per continue command",
    )
    return parser.parse_args()


def build_target(
    board_name: str, firmware_path: str, max_continue_steps: int
) -> GdbTarget:
    board = create_board(board_name)
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
