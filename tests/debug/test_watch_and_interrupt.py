"""Integration tests on a real board: watchpoints, SRAM coherence, Ctrl+C."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("unicorn")

from simulator import create_board  # noqa: E402
from simulator.debug import DebugSession, GdbRemoteServer, GdbTarget  # noqa: E402

FIRMWARE = Path(__file__).resolve().parents[2] / "firmware/led_blink/tm4c/firmware.bin"
GPIOF_DATA = 0x400253FC


@pytest.fixture(name="session")
def fixture_session() -> DebugSession:
    board = create_board("tm4c123")
    board.address_space.flash.load_image(FIRMWARE.read_bytes())
    board.reset()
    return DebugSession(board)


def test_sram_reads_see_cpu_stores(session):
    session.run(max_steps=3000)
    sp = session.read_register(13)
    engine_view = bytes(session.board.cpu.engine.read_memory(sp, 16))
    assert session.read_memory(sp, 16) == engine_view  # nosec B101
    assert any(engine_view)  # nosec B101


def test_sram_write_is_visible_to_cpu_and_bus(session):
    session.write_memory(0x20000100, b"\xde\xad\xbe\xef")
    assert session.read_memory(0x20000100, 4) == b"\xde\xad\xbe\xef"  # nosec B101
    assert session.board.read(0x20000100, 4) == 0xEFBEADDE  # nosec B101


def test_write_watchpoint_stops_on_gpio_write(session):
    session.add_watchpoint(GPIOF_DATA, 4, "write")
    stop = session.run(max_steps=100_000)
    assert stop.reason == "watchpoint"  # nosec B101
    assert stop.watch_kind == "write"  # nosec B101
    assert stop.address is not None  # nosec B101
    assert GPIOF_DATA <= stop.address < GPIOF_DATA + 4  # nosec B101


def test_read_watchpoint_ignores_writes_and_removal_stops_hook(session):
    session.add_watchpoint(GPIOF_DATA, 4, "read")
    first = session.run(max_steps=100_000)
    assert first.reason == "watchpoint"  # nosec B101
    assert first.watch_kind == "read"  # nosec B101
    assert session.remove_watchpoint(GPIOF_DATA, 4, "read")  # nosec B101
    assert (
        session.board.cpu._watch_hook is None
    )  # pylint: disable=protected-access  # nosec B101
    assert session.run(max_steps=2000).reason == "limit"  # nosec B101
    assert not session.remove_watchpoint(GPIOF_DATA, 4, "read")  # nosec B101


def test_watchpoint_json_commands(session):
    reply = session.handle_request(
        {"cmd": "set_wp", "address": GPIOF_DATA, "size": 4, "access": "write"}
    )
    assert reply["ok"]  # nosec B101
    run = session.handle_request({"cmd": "run", "max_steps": 100_000})
    assert run["result"]["reason"] == "watchpoint"  # nosec B101
    cleared = session.handle_request(
        {"cmd": "clear_wp", "address": GPIOF_DATA, "size": 4, "access": "write"}
    )
    assert cleared["result"]["removed"]  # nosec B101


def test_invalid_watchpoint_rejected(session):
    assert not session.handle_request({"cmd": "set_wp", "address": 0, "size": 0})[
        "ok"
    ]  # nosec B101
    assert not session.handle_request(
        {"cmd": "set_wp", "address": 0, "size": 4, "access": "bogus"}
    )[
        "ok"
    ]  # nosec B101


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class _Client:
    def __init__(self, port: int):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=10)

    def send(self, payload: str) -> None:
        checksum = sum(payload.encode()) & 0xFF
        self.sock.sendall(f"${payload}#{checksum:02x}".encode())

    def recv_packet(self) -> str:
        data = b""
        while True:
            data += self.sock.recv(4096)
            text = data.decode(errors="replace")
            if "$" in text and "#" in text.split("$", 1)[1]:
                body = text.split("$", 1)[1]
                if len(body.split("#", 1)[1]) >= 2:
                    return body.split("#", 1)[0]

    def request(self, payload: str) -> str:
        self.send(payload)
        return self.recv_packet()


def test_ctrl_c_interrupts_continue_and_watch_packets_work():
    board = create_board("tm4c123")
    firmware = FIRMWARE.read_bytes()
    port = _free_port()
    server = GdbRemoteServer(GdbTarget(board=board), port=port)
    stop = threading.Event()
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"stop_event": stop}, daemon=True
    )
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while True:
            try:
                client = _Client(port)
                break
            except OSError:
                assert time.monotonic() < deadline  # nosec B101
                time.sleep(0.05)

        assert (
            client.request(f"M0,{len(firmware):x}:{firmware.hex()}") == "OK"
        )  # nosec B101
        assert client.request("qRcmd," + b"reset".hex()) == "OK"  # nosec B101

        # Watchpoint packets: set, hit, clear.
        assert client.request(f"Z2,{GPIOF_DATA:x},4") == "OK"  # nosec B101
        reply = client.request("c")
        assert reply.startswith("T05watch:4002"), reply  # nosec B101
        assert client.request(f"z2,{GPIOF_DATA:x},4") == "OK"  # nosec B101

        # Ctrl+C while running free in the blink loop.
        client.send("c")
        time.sleep(0.5)
        started = time.monotonic()
        client.sock.sendall(b"\x03")
        assert client.recv_packet() == "T02thread:1;"  # nosec B101
        assert time.monotonic() - started < 2  # nosec B101

        # The target is usable again afterwards.
        assert client.request("s") == "S05"  # nosec B101
    finally:
        stop.set()
        thread.join(timeout=3)


def test_debugger_reads_and_writes_stm32_peripheral_registers_by_bytes():
    board = create_board("stm32f4")
    session = DebugSession(board)
    odr = 0x40020C14  # GPIOD ODR: the model only decodes 32-bit accesses
    session.write_memory(odr, (0x2000).to_bytes(4, "little"))
    assert board.read(odr, 4) == 0x2000  # nosec B101
    assert session.read_memory(odr, 4) == (0x2000).to_bytes(4, "little")  # nosec B101
    assert (
        session.read_memory(odr + 1, 1) == b"\x20"
    )  # nosec B101  (single byte inside the word)
    session.write_memory(odr + 1, b"\x40")  # partial word: read-modify-write
    assert board.read(odr, 4) == 0x4000  # nosec B101
