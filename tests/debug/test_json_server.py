"""The line-delimited JSON debug server (used by the CMSIS-DAP proxy / Keil)."""

from __future__ import annotations

import json
import socket
import struct
import sys
import threading
import types

import pytest

pytest.importorskip("unicorn")

from simulator import create_board  # noqa: E402
from simulator.debug import server as json_server  # noqa: E402
from simulator.debug.session import DebugSession  # noqa: E402


def _booted(key="tm4c123"):
    board = create_board(key)
    base = board.address_space.flash.base
    image = (
        struct.pack("<II", board.address_space.sram.base + 0x1000, base + 9)
        + b"\x00" * 64
    )
    board.address_space.flash.load_image(image)
    board.reset()
    return board


@pytest.fixture(name="server")
def fixture_server():
    board = _booted()
    srv = json_server.DebugServer("127.0.0.1", 0, DebugSession(board))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv, board
    srv.shutdown()
    srv.server_close()


class Client:
    def __init__(self, port):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.file = self.sock.makefile("rwb")

    def raw(self, line: bytes) -> dict:
        self.file.write(line + b"\n")
        self.file.flush()
        return json.loads(self.file.readline())

    def call(self, cmd, **kw) -> dict:
        return self.raw(json.dumps({"id": 1, "cmd": cmd, **kw}).encode())


def test_requests_roundtrip_over_tcp(server):
    srv, board = server
    c = Client(srv.server_address[1])
    assert c.call("hello")["result"]["board"] == "TM4C123"  # nosec B101
    assert c.call("write_mem", address=0x20000100, data="deadbeef")["ok"]  # nosec B101
    assert (
        c.call("read_mem", address=0x20000100, size=4)["result"]["data"] == "deadbeef"
    )  # nosec B101
    assert c.call("write_reg", index=0, value=0x1234)["ok"]  # nosec B101
    assert c.call("read_reg", index=0)["result"]["value"] == 0x1234  # nosec B101
    assert c.call("step")["result"]["reason"] == "step"  # nosec B101
    pc = c.call("read_reg", index=15)["result"]["value"]
    assert c.call("set_bp", address=pc + 4)["ok"]  # nosec B101
    run = c.call("run", max_steps=100)["result"]
    assert (run["reason"], run["address"]) == ("breakpoint", pc + 4)  # nosec B101
    assert c.call("clear_bp", address=pc + 4)["ok"]  # nosec B101
    assert c.call("halt")["ok"]  # nosec B101
    assert c.call("reset")["result"]["status"] == "ok"  # nosec B101


def test_errors_are_reported_without_closing_the_connection(server):
    srv, _ = server
    c = Client(srv.server_address[1])
    bad = c.raw(b"this is not json")
    assert bad["ok"] is False and "Invalid JSON" in bad["error"]  # nosec B101
    assert c.call("no_such_command")["ok"] is False  # nosec B101
    assert (
        c.call("read_mem", address=0x70000000, size=4)["ok"] is False
    )  # nosec B101  (unmapped)
    assert c.call("hello")["ok"] is True  # nosec B101  (still usable)


def test_two_clients_share_one_session(server):
    srv, board = server
    a, b = Client(srv.server_address[1]), Client(srv.server_address[1])
    a.call("write_mem", address=0x20000200, data="01020304")
    assert (
        b.call("read_mem", address=0x20000200, size=4)["result"]["data"] == "01020304"
    )  # nosec B101


def test_load_firmware_writes_flash_and_none_is_a_noop(tmp_path):
    board = create_board("tm4c123")
    json_server._load_firmware(board, None)  # nothing happens
    image = tmp_path / "fw.bin"
    image.write_bytes(b"\x11\x22\x33\x44")
    json_server._load_firmware(board, str(image))
    assert board.read(board.address_space.flash.base, 4) == 0x44332211  # nosec B101


class _StubServer:
    instances: list = []

    def __init__(self, host, port, session):
        self.args = (host, port, session)
        _StubServer.instances.append(self)

    def serve_forever(self):
        self.served = True

    def shutdown(self):
        pass

    def server_close(self):
        pass


def _run_main(monkeypatch, argv):
    _StubServer.instances = []
    monkeypatch.setattr(sys, "argv", ["server", *argv])
    monkeypatch.setattr(json_server, "DebugServer", _StubServer)
    return json_server.main()


def test_main_headless_without_firmware_does_not_reset_blank_flash(monkeypatch):
    # Regression: the Keil flow starts with an empty flash and lets the debugger download.
    assert (
        _run_main(monkeypatch, ["--board", "tm4c123", "--no-gui", "--port", "4567"])
        == 0
    )  # nosec B101
    server = _StubServer.instances[0]
    assert server.args[:2] == ("127.0.0.1", 4567)  # nosec B101
    assert server.served  # nosec B101


def test_main_headless_with_firmware_boots_it(monkeypatch, tmp_path):
    board = create_board("stm32f4")
    image = tmp_path / "fw.bin"
    base = board.address_space.flash.base
    image.write_bytes(
        struct.pack("<II", board.address_space.sram.base + 0x1000, base + 9)
        + b"\x00" * 16
    )
    assert (
        _run_main(
            monkeypatch, ["--board", "stm32f4", "--firmware", str(image), "--no-gui"]
        )
        == 0
    )  # nosec B101
    session = _StubServer.instances[0].args[2]
    assert (
        session.read_register(13) == board.address_space.sram.base + 0x1000
    )  # nosec B101  (SP from the vector table)


def test_main_rejects_unknown_board(monkeypatch):
    with pytest.raises(SystemExit):
        _run_main(monkeypatch, ["--board", "nope", "--no-gui"])


def test_main_with_gui_hands_the_shared_board_lock_and_clock_to_the_gui(monkeypatch):
    seen = {}
    fake_app = types.ModuleType("simulator_gui.app")

    def run_gui(argv, **kw):
        seen.update(argv=argv, **kw)
        return 3

    fake_app.run_gui = run_gui
    monkeypatch.setitem(sys.modules, "simulator_gui.app", fake_app)
    assert _run_main(monkeypatch, ["--board", "tm4c123"]) == 3  # nosec B101
    assert seen["argv"] == ["--board", "tm4c123"]  # nosec B101
    assert (
        seen["external_clock"] is True and seen["board_key"] == "tm4c123"
    )  # nosec B101
    assert seen["lock"] is not None and seen["board"].name == "TM4C123"  # nosec B101


def test_main_falls_back_to_headless_when_the_gui_is_unavailable(monkeypatch, capsys):
    monkeypatch.setitem(
        sys.modules, "simulator_gui.app", None
    )  # import raises ImportError
    assert _run_main(monkeypatch, ["--board", "tm4c123"]) == 0  # nosec B101
    assert "GUI unavailable" in capsys.readouterr().out  # nosec B101
    assert _StubServer.instances[0].served  # nosec B101
