import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator_gui import run_gui


if __name__ == "__main__":
    firmware = ROOT / "firmware" / "led_blink" / "tm4c" / "firmware.bin"
    run_gui(
        [
            "--board",
            "tm4c123",
            "--firmware",
            str(firmware),
        ]
    )
