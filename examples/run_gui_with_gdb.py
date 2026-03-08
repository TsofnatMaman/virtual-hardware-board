"""Run simulator GUI and GDB server together (shared board instance).

This launcher starts with an empty board and expects IDE/GDB to upload program
bytes at runtime (e.g. `load` command).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator_gui import run_gui


if __name__ == "__main__":
    run_gui(
        [
            "--board",
            "tm4c123",
            "--gdb-port",
            "3333",
            "--gdb-host",
            "127.0.0.1",
        ]
    )
