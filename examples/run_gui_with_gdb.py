"""Run the simulator GUI and a GDB server together (shared board instance).

Starts with an empty board; the IDE or gdb uploads the program (`load`).
"""

from simulator.debug.defaults import DEFAULT_HOST, DEFAULT_PORT
from simulator_gui import run_gui

if __name__ == "__main__":
    run_gui(
        [
            "--board",
            "tm4c123",
            "--gdb-host",
            DEFAULT_HOST,
            "--gdb-port",
            str(DEFAULT_PORT),
        ]
    )
