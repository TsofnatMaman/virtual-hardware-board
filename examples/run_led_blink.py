import argparse
import sys
from pathlib import Path

# Ensure local repo package is used even if another "simulator" is on PYTHONPATH.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator import TM4C123Board


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TM4C123 LED blink firmware.")
    parser.add_argument(
        "--firmware",
        default="examples/led_blink/tm4c/firmware.bin",
        help="Path to firmware.bin",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=10,
        help="Number of sample points to print",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=50_000,
        help="CPU cycles per sample (increase if LEDs never change)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    board = TM4C123Board()
    firmware = Path(args.firmware).read_bytes()
    board.address_space.flash.load_image(firmware)
    board.reset()

    cfg = board.config
    gpio_f_base = cfg.gpio.ports["F"]
    data_addr = gpio_f_base + 0x3FC  # full mask access
    leds = cfg.pins.leds

    for _ in range(args.steps):
        board.step(args.cycles)
        data = board.read(data_addr, 4)
        print(
            "RED", bool(data & leds["RED"]),
            "BLUE", bool(data & leds["BLUE"]),
            "GREEN", bool(data & leds["GREEN"]),
        )


if __name__ == "__main__":
    main()
