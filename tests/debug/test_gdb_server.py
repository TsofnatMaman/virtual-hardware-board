from __future__ import annotations

import runpy
from dataclasses import dataclass

from simulator.debug import gdb_server
from simulator.debug.gdb_server import GdbRemoteServer, GdbTarget


class DummySnapshotRegister:
    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value


class DummySnapshot:
    def __init__(self, xpsr: int):
        self.registers = [DummySnapshotRegister("XPSR", xpsr)]


class DummyCPU:
    def __init__(self):
        self.regs = {idx: 0 for idx in range(16)}
        self.regs[15] = 0x1001

    def get_register(self, index: int) -> int:
        return self.regs[index]

    def set_register(self, index: int, value: int) -> None:
        self.regs[index] = value

    def get_snapshot(self):
        return DummySnapshot(0x01000000)


class DummyFlash:
    def __init__(self):
        self.loaded = b""

    def load_image(self, image: bytes) -> None:
        self.loaded = image


class DummyAddressSpace:
    def __init__(self):
        self.flash = DummyFlash()


class DummyBoard:
    def __init__(self):
        self.cpu = DummyCPU()
        self.memory = {}
        self.steps = 0
        self.address_space = DummyAddressSpace()
        self.reset_calls = 0

    def read(self, address: int, size: int = 4) -> int:
        return self.memory.get(address, 0)

    def write(self, address: int, size: int, value: int) -> None:
        self.memory[address] = value & 0xFF

    def step(self, cycles: int = 1) -> None:
        self.steps += cycles
        self.cpu.set_register(15, (self.cpu.get_register(15) + 2) | 1)

    def reset(self) -> None:
        self.reset_calls += 1


class FakeConn:
    def __init__(self, incoming: bytes):
        self.incoming = bytearray(incoming)
        self.sent = bytearray()

    def recv(self, size: int) -> bytes:
        if not self.incoming:
            return b""
        out = bytes(self.incoming[:size])
        del self.incoming[:size]
        return out

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)


@dataclass
class _Args:
    board: str
    firmware: str
    host: str = "127.0.0.1"
    port: int = 4444
    max_continue_steps: int = 99


def test_register_roundtrip_and_breakpoint_continue():
    target = GdbTarget(board=DummyBoard(), max_continue_steps=10)
    server = GdbRemoteServer(target)

    g_response = server._handle_packet("g")
    assert len(bytes.fromhex(g_response)) == 17 * 4  # nosec B101

    new_payload = (b"\x11\x00\x00\x00" * 17).hex()
    assert server._handle_packet(f"G{new_payload}") == "OK"  # nosec B101
    assert target.board.cpu.get_register(0) == 0x11  # nosec B101

    assert server._handle_packet("Z0,1004,2") == "OK"  # nosec B101
    target.board.cpu.set_register(15, 0x1001)
    assert server._handle_packet("c") == "T05thread:1;"  # nosec B101


def test_memory_read_write_packets():
    target = GdbTarget(board=DummyBoard())
    server = GdbRemoteServer(target)

    assert server._handle_packet("M2000,4:01020304") == "OK"  # nosec B101
    assert server._handle_packet("m2000,4") == "01020304"  # nosec B101


def test_query_packets():
    target = GdbTarget(board=DummyBoard())
    server = GdbRemoteServer(target)

    assert "PacketSize" in server._handle_packet(
        "qSupported:multiprocess+"
    )  # nosec B101
    assert server._handle_packet("qfThreadInfo") == "m1"  # nosec B101
    assert server._handle_packet("qsThreadInfo") == "l"  # nosec B101


def test_packet_io_helpers_checksum_ack_and_nack():
    target = GdbTarget(board=DummyBoard())
    server = GdbRemoteServer(target)

    payload = "qC"
    checksum = server._checksum(payload)

    # Leading '+' should be ignored, then packet is parsed.
    conn_ok = FakeConn(f"+${payload}#{checksum}".encode("ascii"))
    assert server._read_packet(conn_ok) == payload  # nosec B101
    assert conn_ok.sent == b"+"  # nosec B101

    # Wrong checksum should send NACK and return None.
    conn_bad = FakeConn(b"$qC#00")
    assert server._read_packet(conn_bad) is None  # nosec B101
    assert conn_bad.sent == b"-"  # nosec B101


def test_send_packet_and_dispatch_fallbacks():
    target = GdbTarget(board=DummyBoard())
    server = GdbRemoteServer(target)
    conn = FakeConn(b"")

    server._send_packet(conn, "OK")
    assert conn.sent == b"$OK#9a"  # nosec B101

    assert server._handle_packet("vCont?") == "vCont;c;s"  # nosec B101
    assert server._handle_packet("vCont;s") == "S05"  # nosec B101
    assert server._handle_packet("Hc0") == "OK"  # nosec B101
    assert server._handle_packet("Hg0") == "OK"  # nosec B101
    assert server._handle_packet("D") == "OK"  # nosec B101
    assert server._handle_packet("!") == ""  # nosec B101
    assert server._handle_packet("unknown") == ""  # nosec B101


def test_parse_args_build_target_and_main(monkeypatch, tmp_path):
    firmware_path = tmp_path / "fw.bin"
    firmware_path.write_bytes(b"abc")

    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--board",
            "tm4c123",
            "--firmware",
            str(firmware_path),
            "--host",
            "127.0.0.1",
            "--port",
            "5555",
            "--max-continue-steps",
            "123",
        ],
    )
    args = gdb_server.parse_args()
    assert args.board == "tm4c123"  # nosec B101
    assert args.port == 5555  # nosec B101
    assert args.max_continue_steps == 123  # nosec B101
    assert args.host == "127.0.0.1"  # nosec B101

    board = DummyBoard()
    monkeypatch.setattr(gdb_server, "create_board", lambda _name: board)
    target = gdb_server.build_target("tm4c123", str(firmware_path), 7)
    assert board.address_space.flash.loaded == b"abc"  # nosec B101
    assert board.reset_calls == 1  # nosec B101
    assert target.max_continue_steps == 7  # nosec B101

    calls: list[tuple[object | None, str, int]] = []

    class FakeServer:
        def __init__(self, target: GdbTarget, host: str, port: int):
            calls.append((target, host, port))

        def serve_forever(self) -> None:
            calls.append((None, "serve", 0))

    monkeypatch.setattr(
        gdb_server, "parse_args", lambda: _Args("tm4c123", str(firmware_path))
    )
    monkeypatch.setattr(gdb_server, "build_target", lambda *_args: target)
    monkeypatch.setattr(gdb_server, "GdbRemoteServer", FakeServer)
    gdb_server.main()

    assert calls[0][0] is target  # nosec B101
    assert calls[0][1] == "127.0.0.1"  # nosec B101
    assert calls[0][2] == 4444  # nosec B101
    assert calls[1] == (None, "serve", 0)  # nosec B101


def test_package_main_invokes_gdb_main(monkeypatch):
    invoked = {"count": 0}

    def _fake_main() -> None:
        invoked["count"] += 1

    monkeypatch.setattr("simulator.debug.gdb_server.main", _fake_main)
    runpy.run_module("simulator.debug.__main__", run_name="__main__")
    assert invoked["count"] == 1  # nosec B101


class FailingBoard(DummyBoard):
    def read(self, address: int, size: int = 4) -> int:
        raise ValueError("read fail")

    def write(self, address: int, size: int, value: int) -> None:
        raise ValueError("write fail")


def test_target_failure_paths_and_register_bounds():
    target = GdbTarget(board=DummyBoard(), max_continue_steps=1)

    short_payload = b"\x00" * 8
    assert target.write_registers(short_payload) is False  # nosec B101

    target.set_pc(0x2000)
    assert target.board.cpu.get_register(15) == 0x2001  # nosec B101

    target.breakpoints.clear()
    response = target.cont()
    assert response == "T05thread:1;"  # nosec B101


def test_target_memory_error_paths():
    target = GdbTarget(board=FailingBoard())
    assert target.read_memory(0x2000, 2) is None  # nosec B101
    assert target.write_memory(0x2000, b"\x01\x02") is False  # nosec B101


def test_read_packet_stream_termination_cases():
    server = GdbRemoteServer(GdbTarget(board=DummyBoard()))

    # EOF before packet start
    conn_no_start = FakeConn(b"")
    assert server._read_packet(conn_no_start) is None  # nosec B101

    # EOF while reading payload
    conn_no_payload_end = FakeConn(b"$abc")
    assert server._read_packet(conn_no_payload_end) is None  # nosec B101
