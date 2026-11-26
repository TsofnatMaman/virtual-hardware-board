"""Runnable examples. Run from the repository root: `python -m examples.<name>`."""

from pathlib import Path

TM4C_FIRMWARE = (
    Path(__file__).resolve().parents[1]
    / "firmware"
    / "led_blink"
    / "tm4c"
    / "firmware.bin"
)
