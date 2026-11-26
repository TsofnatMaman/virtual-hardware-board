"""Run the TM4C123 LED blink firmware headless and print the LED states."""

import argparse
from pathlib import Path

from examples import TM4C_FIRMWARE
from simulator import TM4C123Board

GPIO_DATA_FULL_MASK = 0x3FC  # TM4C data register offset that accesses all eight pins
GPIO_REGISTER_BYTES = 4
DEFAULT_SAMPLES = 10
DEFAULT_CYCLES_PER_SAMPLE = 50_000


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run TM4C123 LED blink firmware.")
    parser.add_argument(
        "--firmware",
        default=str(TM4C_FIRMWARE),
        help="Path to firmware.bin",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_SAMPLES,
        help="Number of sample points to print",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=DEFAULT_CYCLES_PER_SAMPLE,
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
    data_addr = gpio_f_base + GPIO_DATA_FULL_MASK
    leds = cfg.pins.leds

    for _ in range(args.steps):
        board.step(args.cycles)
        data = board.read(data_addr, GPIO_REGISTER_BYTES)
        print(
            "RED",
            bool(data & leds["RED"]),
            "BLUE",
            bool(data & leds["BLUE"]),
            "GREEN",
            bool(data & leds["GREEN"]),
        )


if __name__ == "__main__":
    main()
