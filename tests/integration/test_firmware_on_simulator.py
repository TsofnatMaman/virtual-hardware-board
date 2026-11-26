"""Build firmware for every board and watch it drive the simulated GPIO."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("unicorn")

from simulator import create_board  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from conftest import ROOT, load_and_reset, needs_toolchain, watch_register  # noqa: E402

pytestmark = [pytest.mark.integration, needs_toolchain]

TM4C_BLINK = """
#include "tm4c.h"
static void wait(void) { for (volatile int i = 0; i < 150; ++i) { } }
int main(void)
{
    SYSCTL_RCGCGPIO_R |= (1U << 5);
    GPIO_PORTF_DIR_R |= 0x0E;
    GPIO_PORTF_DEN_R |= 0x0E;
    while (1) {
        GPIO_PORTF_DATA_R = 0x02; wait();   /* red   */
        GPIO_PORTF_DATA_R = 0x08; wait();   /* green */
        GPIO_PORTF_DATA_R = 0x04; wait();   /* blue  */
    }
}
"""

C031_BLINK = """
#include "stm32c031.h"
static void wait(void) { for (volatile int i = 0; i < 150; ++i) { } }
int main(void)
{
    RCC_IOPENR_R |= 1U;
    GPIOA_MODER_R = (GPIOA_MODER_R & ~(3U << 10)) | (1U << 10);
    while (1) {
        GPIOA_BSRR_R = 1U << 5;          wait();   /* LD4 on  */
        GPIOA_BSRR_R = 1U << (5 + 16);   wait();   /* LD4 off */
    }
}
"""

# Sets and clears the same pin in one write: the reference manual says "set" wins.
F4_RUNNING_LIGHT = """
#include "stm32f4.h"
static void wait(void) { for (volatile int i = 0; i < 150; ++i) { } }
int main(void)
{
    unsigned int led = 0;
    RCC_AHB1ENR_R |= RCC_AHB1ENR_GPIODEN;
    while (1) {
        GPIOD_BSRR_R = (0xFU << 28) | (1U << (12 + led));
        wait();
        led = (led + 1U) % 4U;
    }
}
"""

CASES = [
    # board, source, observed register, values expected in this order, then again (a loop)
    ("tm4c123", TM4C_BLINK, 0x400253FC, [0x02, 0x08, 0x04]),
    ("stm32c031", C031_BLINK, 0x50000014, [0x20, 0x00]),
    ("stm32f4", F4_RUNNING_LIGHT, 0x40020C14, [0x1000, 0x2000, 0x4000, 0x8000]),
]


def _contains_twice(seq, pattern):
    hits = [
        i
        for i in range(len(seq) - len(pattern) + 1)
        if seq[i : i + len(pattern)] == pattern
    ]
    return len(hits) >= 2


@pytest.mark.parametrize(
    "board_key,source,address,pattern", CASES, ids=[c[0] for c in CASES]
)
def test_template_firmware_blinks_the_expected_pins(
    build_project, board_key, source, address, pattern
):
    _, bin_path = build_project(board_key, source)
    board = create_board(board_key)
    load_and_reset(board, bin_path)
    seen = watch_register(board, address, steps=40_000)
    assert _contains_twice(
        seen, pattern
    ), f"{board_key}: expected {pattern} twice in order, saw {seen[:24]}"  # nosec B101


def test_template_default_main_builds_for_tm4c123(build_project):
    elf, bin_path = build_project(
        "tm4c123"
    )  # the shipped src/main.c (blue on, then red blinks)
    assert elf.stat().st_size > 0 and bin_path.stat().st_size > 0  # nosec B101
    board = create_board("tm4c123")
    load_and_reset(board, bin_path)
    seen = watch_register(board, 0x400253FC, steps=20_000)
    assert seen[:3] == [
        0x00,
        0x04,
        0x06,
    ]  # nosec B101  (LEDs off, blue on, then red on as well)


@pytest.mark.parametrize(
    "board_key,example",
    [
        ("tm4c123", "led_blink/tm4c/main.c"),
        ("stm32c031", "led_blink/stm32/main.c"),
        ("stm32f4", "led_blink/stm32f4/main.c"),
    ],
)
def test_bundled_examples_build_and_boot(tmp_path, board_key, example):
    out = tmp_path / "app.bin"
    cmd = [
        "make",
        "-f",
        str(ROOT / "firmware" / "Makefile"),
        f"BOARD={board_key}",
        f"MAIN={ROOT / 'firmware' / example}",
        f"OUT={out}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    board = create_board(board_key)
    load_and_reset(board, out)
    sram = board.address_space.sram
    assert sram.contains(
        board.cpu.get_register(13)
    ), "SP must start inside SRAM"  # nosec B101
    board.step(5_000)  # runs without faulting
    assert board.address_space.flash.contains(board.cpu.get_register(15))  # nosec B101


def test_build_fails_loudly_for_an_unknown_board(tmp_path):
    result = subprocess.run(
        ["make", "-f", str(ROOT / "firmware" / "Makefile"), "BOARD=nope", "MAIN=x.c"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0 and "Unknown BOARD" in result.stderr  # nosec B101
