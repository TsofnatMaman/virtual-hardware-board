"""Every GUI board layout must load and agree with the simulated board."""

from __future__ import annotations

from pathlib import Path

import pytest

from simulator import create_board, list_available_boards, verify_boards_registered
from simulator_gui.config import load_gui_config
from simulator_gui.registry import default_registry

BOARDS_DIR = Path(__file__).resolve().parents[2] / "simulator_gui" / "boards"
YAMLS = sorted(BOARDS_DIR.glob("*.yaml"))


def test_every_registered_board_has_a_gui_layout():
    verify_boards_registered()
    missing = [
        b for b in list_available_boards() if not (BOARDS_DIR / f"{b}.yaml").exists()
    ]
    assert (
        not missing
    ), f"boards without simulator_gui/boards/<key>.yaml: {missing}"  # nosec B101


@pytest.mark.parametrize("path", YAMLS, ids=lambda p: p.stem)
class TestBoardLayout:
    def test_loads_and_matches_the_board(self, path):
        cfg = load_gui_config(path)
        board = create_board(path.stem)
        assert (
            cfg.board_name == board.name
        )  # nosec B101  (window title / GUI key mapping)
        assert cfg.components, "layout has no components"  # nosec B101

    def test_background_image_exists_and_matches_the_canvas(self, path, qapp):
        from PySide6 import QtGui

        cfg = load_gui_config(path)
        assert Path(cfg.background_image).is_file(), cfg.background_image  # nosec B101
        size = QtGui.QImage(cfg.background_image).size()
        assert (size.width(), size.height()) == (
            cfg.canvas.width,
            cfg.canvas.height,
        )  # nosec B101

    def test_component_ids_are_unique_and_types_known(self, path, qapp):
        cfg = load_gui_config(path)
        ids = [c.id for c in cfg.components]
        assert len(ids) == len(set(ids)), f"duplicate ids in {ids}"  # nosec B101
        registry = default_registry()
        for comp in cfg.components:
            assert (
                registry.create(comp) is not None
            )  # nosec B101  (raises on unknown type)

    def test_components_lie_inside_the_canvas(self, path):
        cfg = load_gui_config(path)
        for comp in cfg.components:
            if comp.position is None:
                continue
            p = comp.position
            assert p.x >= 0 and p.y >= 0, comp.id  # nosec B101
            assert p.x + p.width <= cfg.canvas.width, comp.id  # nosec B101
            assert p.y + p.height <= cfg.canvas.height, comp.id  # nosec B101

    def test_bindings_point_at_real_peripheral_registers(self, path):
        cfg = load_gui_config(path)
        board = create_board(path.stem)
        space = board.address_space
        for comp in cfg.components:
            b = comp.binding
            assert b.mask != 0, f"{comp.id}: empty mask"  # nosec B101
            assert space.mmio.contains(
                b.address
            ), f"{comp.id}: 0x{b.address:08X} is not peripheral memory"  # nosec B101
            board.read(b.address, b.size)  # must be readable by the GUI backend

    def test_leds_are_outputs_and_inputs_are_inputs(self, path):
        cfg = load_gui_config(path)
        for comp in cfg.components:
            if comp.type == "LED":
                assert comp.binding.direction == "output", comp.id  # nosec B101
            if comp.type in ("SWITCH", "BUTTON"):
                assert comp.binding.direction in (
                    "input",
                    "bidirectional",
                ), comp.id  # nosec B101


def test_stm32f4_discovery_leds_are_on_gpiod_pins_12_to_15():
    cfg = load_gui_config(BOARDS_DIR / "stm32f4.yaml")
    leds = {
        c.id: (c.binding.address, c.binding.mask)
        for c in cfg.components
        if c.type == "LED"
    }
    assert leds == {  # nosec B101
        "led_ld4": (0x40020C14, 1 << 12),
        "led_ld3": (0x40020C14, 1 << 13),
        "led_ld5": (0x40020C14, 1 << 14),
        "led_ld6": (0x40020C14, 1 << 15),
    }


def test_stm32f4_leds_form_the_diamond_around_the_accelerometer():
    # On the photo: LD3 top, LD4 left, LD5 right, LD6 bottom (LD4/LD5 level, LD3/LD6 aligned).
    cfg = load_gui_config(BOARDS_DIR / "stm32f4.yaml")
    pos = {c.id: c.position for c in cfg.components}
    ld3, ld4, ld5, ld6 = (pos[f"led_ld{n}"] for n in (3, 4, 5, 6))
    assert ld3.y < ld4.y == ld5.y < ld6.y  # nosec B101
    assert ld4.x < ld3.x == ld6.x < ld5.x  # nosec B101
