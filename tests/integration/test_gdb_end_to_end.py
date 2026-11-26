"""A real gdb session against the in-process GDB server, as VS Code (Cortex-Debug) drives it."""

from __future__ import annotations

import socket
import subprocess
import sys
import threading
from pathlib import Path

import pytest

pytest.importorskip("unicorn")

from simulator import create_board  # noqa: E402
from simulator.debug import GdbRemoteServer, GdbTarget  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from conftest import GDB, needs_gdb, needs_toolchain  # noqa: E402

pytestmark = [pytest.mark.integration, needs_toolchain, needs_gdb]

PROGRAM = """
#include "tm4c.h"

volatile unsigned int ticks;

static void delay(int n) { volatile int i = 0; while (i < n) { ++i; } }

int main(void)
{
    SYSCTL_RCGCGPIO_R |= (1U << 5);
    GPIO_PORTF_DIR_R |= 0x0E;
    GPIO_PORTF_DEN_R |= 0x0E;
    while (1) {
        GPIO_PORTF_DATA_R = 0x02;
        ticks++;
        delay(100);
        GPIO_PORTF_DATA_R = 0x00;
        delay(100);
    }
}
"""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(name="gdb_session")
def fixture_gdb_session(build_project, tmp_path):
    elf, _ = build_project("tm4c123", PROGRAM)
    board = create_board("tm4c123")
    port = _free_port()
    server = GdbRemoteServer(GdbTarget(board=board, lock=threading.RLock()), port=port)
    stop = threading.Event()
    threading.Thread(
        target=server.serve_forever, kwargs={"stop_event": stop}, daemon=True
    ).start()

    def run(commands: str, timeout: int = 90) -> str:
        script = tmp_path / "cmds.gdb"
        script.write_text(
            f"set pagination off\ntarget remote 127.0.0.1:{port}\n{commands}\n",
            encoding="utf-8",
        )
        for _ in range(40):  # the server thread needs a moment to listen
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                threading.Event().wait(0.05)
        proc = subprocess.run(
            [GDB, "-q", "-batch", "-x", str(script), str(elf)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.stdout + proc.stderr

    yield run, board
    stop.set()


def test_download_break_at_main_and_step(gdb_session):
    run, board = gdb_session
    out = run(
        "monitor reset\nload\nmonitor reset\ntbreak main\ncontinue\nnext\nnext\ninfo registers pc"
    )
    assert "Load failed" not in out, out  # nosec B101
    assert "Temporary breakpoint 1, main ()" in out, out  # nosec B101
    assert "src/main.c:" in out, out  # nosec B101  (source level information)


def test_breakpoint_hits_repeatedly_and_variables_are_live(gdb_session):
    run, _ = gdb_session
    out = run(
        "load\nmonitor reset\nbreak delay\ncontinue\nprint ticks\ncontinue\nprint ticks\ncontinue\nprint ticks"
    )
    values = [
        int(line.split("=")[1])
        for line in out.splitlines()
        if line.startswith("$") and "= " in line
    ]
    # stops: first delay() of iteration 1, second delay() of iteration 1, first delay() of iteration 2
    assert values == [1, 1, 2], out  # nosec B101


def test_watchpoint_stops_when_the_variable_changes(gdb_session):
    run, _ = gdb_session
    out = run(
        "load\nmonitor reset\ntbreak main\ncontinue\nwatch ticks\ncontinue\nprint ticks"
    )
    assert "Hardware watchpoint 2: ticks" in out, out  # nosec B101
    assert "Old value = 0" in out and "New value = 1" in out, out  # nosec B101


def test_peripheral_registers_are_readable_and_the_led_follows_the_code(gdb_session):
    run, board = gdb_session
    out = run(
        "load\nmonitor reset\nbreak delay\ncontinue\nprint/x *(unsigned int*)0x400253FC"
    )
    assert (
        "= 0x2" in out
    ), out  # nosec B101  (the red LED bit is set when we stop in delay)
    assert (
        board.read(0x400253FC, 4) == 0x02
    )  # nosec B101  (same value the simulator GUI would show)


def test_reset_before_download_does_not_break_the_connection(gdb_session):
    # Cortex-Debug issues 'monitor reset' while flash is still blank.
    run, _ = gdb_session
    out = run("monitor halt\nmonitor reset\nload\nmonitor reset\ntbreak main\ncontinue")
    assert (
        "Remote connection closed" not in out
        and "Temporary breakpoint 1, main ()" in out
    ), out  # nosec B101
