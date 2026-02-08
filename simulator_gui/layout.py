"""Fallback layout engines for GUI components."""

from __future__ import annotations

from abc import ABC, abstractmethod

from simulator_gui.config import ComponentConfig, Rect


class LayoutEngine(ABC):
    """Compute positions for components without explicit coordinates."""

    @abstractmethod
    def layout(
        self,
        components: list[ComponentConfig],
        bounds: Rect,
        item_size: tuple[int, int],
        spacing: int,
    ) -> dict[str, Rect]:
        ...


class FlowLayoutEngine(LayoutEngine):
    """Simple left-to-right flow layout with row wrapping."""

    def layout(
        self,
        components: list[ComponentConfig],
        bounds: Rect,
        item_size: tuple[int, int],
        spacing: int,
    ) -> dict[str, Rect]:
        ordered = sorted(components, key=lambda c: c.id)
        positions: dict[str, Rect] = {}

        x = bounds.x
        y = bounds.y
        max_x = bounds.x + bounds.width
        max_y = bounds.y + bounds.height
        item_w, item_h = item_size

        for comp in ordered:
            if x + item_w > max_x and x != bounds.x:
                x = bounds.x
                y += item_h + spacing

            if y + item_h > max_y:
                # No more space; place remaining off-canvas but deterministic.
                positions[comp.id] = Rect(max_x + spacing, max_y + spacing, item_w, item_h)
                continue

            positions[comp.id] = Rect(x, y, item_w, item_h)
            x += item_w + spacing

        return positions
