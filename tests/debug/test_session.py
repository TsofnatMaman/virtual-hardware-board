from __future__ import annotations

import threading
import time

from simulator.core.exceptions import SimulatorError
from simulator.debug import DebugSession
from tests.debug.test_gdb_server import DummyBoard


class FaultyBoard(DummyBoard):
    def step(self, cycles: int = 1) -> None:
        raise SimulatorError("boom")


def test_step_advances_one_instruction():
    session = DebugSession(DummyBoard())
    stop = session.step()
    assert stop.reason == "step"  # nosec B101
    assert stop.address == 0x1002  # nosec B101


def test_run_stops_at_breakpoint_and_moves_past_it_on_resume():
    session = DebugSession(DummyBoard())
    session.add_breakpoint(0x1006)
    first = session.run(max_steps=100)
    assert (first.reason, first.address) == ("breakpoint", 0x1006)  # nosec B101
    second = session.run(max_steps=1)
    assert second.address == 0x1008  # nosec B101


def test_run_reports_limit_and_fault():
    assert DebugSession(DummyBoard()).run(max_steps=3).reason == "limit"  # nosec B101
    fault = DebugSession(FaultyBoard()).run()
    assert fault.reason == "fault"  # nosec B101
    assert fault.detail == "boom"  # nosec B101


def test_halt_request_stops_run_from_another_thread():
    session = DebugSession(DummyBoard())
    threading.Timer(0.05, session.request_halt).start()
    deadline = time.monotonic() + 2
    stop = session.run()
    assert stop.reason == "halt"  # nosec B101
    assert time.monotonic() < deadline  # nosec B101


def test_flash_write_triggers_reset_before_next_run():
    board = DummyBoard()
    session = DebugSession(board)
    session.write_memory(0x0, b"\x01\x02")
    assert session.needs_reset  # nosec B101
    session.step()
    assert board.reset_calls == 1  # nosec B101
    assert not session.needs_reset  # nosec B101


def test_json_requests_roundtrip():
    board = DummyBoard()
    board.name = "dummy"
    session = DebugSession(board)
    assert session.handle_request({"id": 1, "cmd": "hello"})["ok"]  # nosec B101
    session.handle_request({"cmd": "write_mem", "address": 0x2000, "data": "aabb"})
    read = session.handle_request({"cmd": "read_mem", "address": 0x2000, "size": 2})
    assert read["result"]["data"] == "aabb"  # nosec B101
    session.handle_request({"cmd": "set_bp", "address": 0x1004})
    run = session.handle_request({"cmd": "run", "max_steps": 10})
    assert run["result"]["reason"] == "breakpoint"  # nosec B101
    session.handle_request({"cmd": "clear_bp", "address": 0x1004})
    assert not session.breakpoints  # nosec B101


def test_json_errors_are_reported_not_raised():
    session = DebugSession(DummyBoard())
    assert not session.handle_request({"cmd": "nope"})["ok"]  # nosec B101
    assert not session.handle_request({"cmd": "read_reg"})["ok"]  # nosec B101
    assert not session.handle_request({})["ok"]  # nosec B101


def test_reset_on_unbootable_board_is_deferred_not_fatal():
    class BlankFlashBoard(DummyBoard):
        def reset(self) -> None:
            raise RuntimeError("Invalid boot MSP")

    session = DebugSession(BlankFlashBoard())
    assert session.reset() is False  # nosec B101
    assert session.needs_reset  # nosec B101
    assert (
        session.handle_request({"cmd": "reset"})["result"]["status"] == "deferred"
    )  # nosec B101
    assert session.step().reason == "fault"  # nosec B101
