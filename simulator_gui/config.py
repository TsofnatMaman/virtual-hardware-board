"""GUI configuration loader and data models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class CanvasConfig:
    width: int
    height: int
    scale_mode: Literal["fit", "stretch", "none"] = "fit"


@dataclass(frozen=True)
class FallbackLayoutConfig:
    area: Rect | None
    spacing: int = 12
    item_size: tuple[int, int] = (24, 24)


@dataclass(frozen=True)
class HardwareBinding:
    address: int
    mask: int
    size: int = 4
    invert: bool = False
    direction: Literal["input", "output", "bidirectional"] = "output"


@dataclass(frozen=True)
class ComponentConfig:
    id: str
    type: str
    position: Rect | None
    visual: dict[str, Any]
    binding: HardwareBinding


@dataclass(frozen=True)
class GuiBoardConfig:
    board_name: str
    background_image: str
    canvas: CanvasConfig
    components: list[ComponentConfig]
    fallback_layout: FallbackLayoutConfig


def _parse_rect(value: Any) -> Rect | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) == 4:
        return Rect(float(value[0]), float(value[1]), float(value[2]), float(value[3]))
    raise ValueError(f"Invalid rect value: {value}")


def _parse_canvas(value: dict[str, Any]) -> CanvasConfig:
    return CanvasConfig(
        width=int(value["width"]),
        height=int(value["height"]),
        scale_mode=str(value.get("scale_mode", "fit")),
    )


def _parse_fallback(value: dict[str, Any] | None) -> FallbackLayoutConfig:
    if value is None:
        return FallbackLayoutConfig(area=None)
    area = _parse_rect(value.get("area"))
    spacing = int(value.get("spacing", 12))
    item_size = value.get("item_size", [24, 24])
    return FallbackLayoutConfig(
        area=area,
        spacing=spacing,
        item_size=(int(item_size[0]), int(item_size[1])),
    )


def _parse_binding(value: dict[str, Any]) -> HardwareBinding:
    return HardwareBinding(
        address=int(value["address"]),
        mask=int(value.get("mask", 0)),
        size=int(value.get("size", 4)),
        invert=bool(value.get("invert", False)),
        direction=str(value.get("direction", "output")),
    )


def _parse_component(value: dict[str, Any]) -> ComponentConfig:
    return ComponentConfig(
        id=str(value["id"]),
        type=str(value["type"]).upper(),
        position=_parse_rect(value.get("position")),
        visual=dict(value.get("visual", {})),
        binding=_parse_binding(value.get("binding", {})),
    )


def load_gui_config(path: str | Path) -> GuiBoardConfig:
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    canvas = _parse_canvas(raw.get("canvas", {}))
    fallback = _parse_fallback(raw.get("fallback_layout"))
    components = [_parse_component(item) for item in raw.get("components", [])]

    background = str(raw.get("background_image", ""))
    if background:
        background = str((path.parent / background).resolve())

    return GuiBoardConfig(
        board_name=str(raw.get("board_name", "Unknown Board")),
        background_image=background,
        canvas=canvas,
        components=components,
        fallback_layout=fallback,
    )
