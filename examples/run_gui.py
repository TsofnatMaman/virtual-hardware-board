"""Run the GUI with the TM4C123 LED blink firmware."""

from examples import TM4C_FIRMWARE
from simulator_gui import run_gui

if __name__ == "__main__":
    run_gui(["--board", "tm4c123", "--firmware", str(TM4C_FIRMWARE)])
