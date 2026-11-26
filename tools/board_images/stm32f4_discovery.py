"""Generate the STM32F4 Discovery board illustration used by the GUI.

A stylised drawing (not a photo): PCB, MCU, USB connectors, pin headers, buttons and the
four user LEDs. Re-run after editing, then adjust LED positions in
``simulator_gui/boards/stm32f4.yaml`` (see LED_CENTERS below). Requires Pillow.

    python tools/board_images/stm32f4_discovery.py
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, S = 800, 480, 3  # canvas size, supersampling factor
OUT = Path(__file__).resolve().parents[2] / "simulator_gui" / "assets" / "stm32f4_discovery.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

# Centres of the four user LEDs in canvas coordinates (used by stm32f4.yaml).
LED_CENTERS = {"LD3": (610, 250), "LD4": (560, 300), "LD5": (660, 300), "LD6": (610, 350)}
USER_BUTTON = (610, 300)

PCB, PCB_EDGE, TRACE = "#101923", "#2a3a4c", "#1a2837"
GOLD, SILK, SILVER = "#d9b44a", "#e8eef5", "#b9c2cc"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, int(size * S))


def main() -> None:
    random.seed(4)
    img = Image.new("RGB", (W * S, H * S), "#080b10")
    d = ImageDraw.Draw(img)
    sc = lambda *v: [int(x * S) for x in v]  # noqa: E731

    def text(xy, s, size=11, fill=SILK, path=FONT, anchor="mm"):
        d.text((xy[0] * S, xy[1] * S), s, font=font(path, size), fill=fill, anchor=anchor)

    # --- PCB with soft edge highlight and mounting holes
    d.rounded_rectangle(sc(12, 12, W - 12, H - 12), radius=22 * S, fill=PCB, outline=PCB_EDGE, width=2 * S)
    for x, y in ((34, 34), (W - 34, 34), (34, H - 34), (W - 34, H - 34)):
        d.ellipse(sc(x - 9, y - 9, x + 9, y + 9), fill="#06090d", outline=GOLD, width=2 * S)

    # --- decorative traces
    for _ in range(46):
        x, y = random.randint(110, 700), random.randint(80, 400)
        dx = random.choice((-1, 1)) * random.randint(30, 120)
        dy = random.choice((-1, 1)) * random.randint(0, 60)
        d.line(sc(x, y, x + dx, y, x + dx, y + dy), fill=TRACE, width=2 * S)

    # --- pin headers P1 / P2 (two rows of 25 pins on top and bottom)
    def header(y0, label):
        for row in (0, 1):
            for i in range(25):
                x, y = 136 + i * 22.4, y0 + row * 16
                d.rectangle(sc(x - 5, y - 5, x + 5, y + 5), fill=GOLD)
                d.ellipse(sc(x - 2, y - 2, x + 2, y + 2), fill="#05080c")
        d.rectangle(sc(124, y0 - 12, 700, y0 + 28), outline=SILK, width=1 * S)
        text((100, y0 + 8), label, 14, SILK, BOLD)
    header(44, "P2")
    header(424, "P1")

    # --- MCU (LQFP100) with pins and marking
    cx, cy, half = 380, 232, 70
    for i in range(25):
        o = -half + 6 + i * (2 * half - 12) / 24
        for (x1, y1, x2, y2) in ((cx + o, cy - half - 8, cx + o, cy - half), (cx + o, cy + half, cx + o, cy + half + 8),
                                 (cx - half - 8, cy + o, cx - half, cy + o), (cx + half, cy + o, cx + half + 8, cy + o)):
            d.line(sc(x1, y1, x2, y2), fill=SILVER, width=2 * S)
    d.rectangle(sc(cx - half, cy - half, cx + half, cy + half), fill="#14171c", outline="#2c333d", width=2 * S)
    d.ellipse(sc(cx - half + 10, cy + half - 20, cx - half + 20, cy + half - 10), outline="#4a5563", width=2 * S)
    text((cx, cy - 18), "STM32F407", 17, "#9aa6b4", MONO)
    text((cx, cy + 4), "VGT6", 17, "#9aa6b4", MONO)
    text((cx, cy + 30), "ARM Cortex-M4", 9, "#6c7886")

    # --- ST-LINK section (left): mini-USB, ST-LINK chip, label
    d.rounded_rectangle(sc(12, 196, 70, 268), radius=6 * S, fill="#c9d1d9", outline="#7b8794", width=2 * S)
    d.rectangle(sc(20, 214, 62, 250), fill="#0a0d12")
    text((106, 188), "ST-LINK/V2", 11, SILK, BOLD)
    d.rectangle(sc(110, 205, 154, 249), fill="#14171c", outline="#2c333d", width=2 * S)
    text((132, 227), "ST-LINK", 7, "#8794a2")
    # --- USB OTG (right)
    d.rounded_rectangle(sc(W - 66, 196, W - 12, 262), radius=6 * S, fill="#c9d1d9", outline="#7b8794", width=2 * S)
    d.rectangle(sc(W - 58, 216, W - 20, 242), fill="#0a0d12")
    text((W - 108, 188), "USB OTG", 10, SILK, BOLD)

    # --- crystal, small SMD parts
    d.rounded_rectangle(sc(250, 318, 292, 338), radius=4 * S, fill=SILVER, outline="#7b8794", width=1 * S)
    text((271, 348), "8 MHz", 8, "#8794a2")
    for _ in range(40):
        x, y = random.randint(130, 700), random.randint(95, 395)
        if abs(x - cx) < 90 and abs(y - cy) < 90 or abs(x - 610) < 80 and abs(y - 300) < 80:
            continue
        w, h = random.choice(((7, 4), (4, 7)))
        d.rectangle(sc(x, y, x + w, y + h), fill=random.choice(("#c7a54a", "#3a4452", "#5a4a2a")))

    # --- title block
    text((380, 110), "STM32F4 DISCOVERY", 22, SILK, BOLD)
    text((380, 134), "illustration - STM32F407 board layout (stylised)", 9, "#6c7886")

    # --- user LEDs around the blue USER button
    d.ellipse(sc(*(USER_BUTTON[0] - 40, USER_BUTTON[1] - 40, USER_BUTTON[0] + 40, USER_BUTTON[1] + 40)), outline="#26384b", width=2 * S)
    for name, (x, y) in LED_CENTERS.items():
        d.ellipse(sc(x - 17, y - 17, x + 17, y + 17), fill="#0a0d12", outline=SILVER, width=2 * S)
    pins = {"LD3": ("PD13", 0, -34), "LD4": ("PD12", -42, 0), "LD5": ("PD14", 42, 0), "LD6": ("PD15", 0, 36)}
    for name, (x, y) in LED_CENTERS.items():
        pin, dx, dy = pins[name]
        text((x + dx * 1.0, y + dy * 1.0 - (3 if dy else 0)), name, 10, SILK, BOLD)
        text((x + dx * 1.0, y + dy * 1.0 + 9), pin, 7, "#8794a2")
    bx, by = USER_BUTTON
    d.ellipse(sc(bx - 14, by - 14, bx + 14, by + 14), fill="#1d4ed8", outline="#93c5fd", width=2 * S)
    text((bx, by), "USER", 7, "#dbeafe", BOLD)
    text((bx + 78, by + 52), "B1  (PA0)", 8, "#8794a2")
    # --- reset button
    d.ellipse(sc(176, 336, 206, 366), fill="#050709", outline="#7b8794", width=2 * S)
    text((191, 382), "RESET", 8, SILK, BOLD)

    img = img.resize((W, H), Image.LANCZOS)
    glow = img.filter(ImageFilter.GaussianBlur(0.4))
    glow.save(OUT)
    print("wrote", OUT, glow.size)


if __name__ == "__main__":
    main()
