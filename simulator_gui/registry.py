"""Component registry and factory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from simulator_gui.components.button import ButtonController, ButtonView
from simulator_gui.components.led import LedController, LedView
from simulator_gui.components.switch import SwitchController, SwitchView
from simulator_gui.config import ComponentConfig


@dataclass(frozen=True)
class ComponentInstance:
    view: object
    controller: object
    config: ComponentConfig


ComponentFactory = Callable[[ComponentConfig], ComponentInstance]


class ComponentRegistry:
    def __init__(self):
        self._factories: Dict[str, ComponentFactory] = {}

    def register(self, component_type: str, factory: ComponentFactory) -> None:
        self._factories[component_type.upper()] = factory

    def create(self, config: ComponentConfig) -> ComponentInstance:
        ctype = config.type.upper()
        if ctype not in self._factories:
            raise ValueError(f"Unknown component type: {ctype}")
        return self._factories[ctype](config)


def _create_led(config: ComponentConfig) -> ComponentInstance:
    size = config.visual.get("size", [20, 20])
    view = LedView(
        size=(int(size[0]), int(size[1])),
        on_color=str(config.visual.get("on_color", "#ff3b30")),
        off_color=str(config.visual.get("off_color", "#3a0f0f")),
        border_color=str(config.visual.get("border_color", "#111111")),
    )
    controller = LedController(config.id, config.binding, view)
    return ComponentInstance(view=view, controller=controller, config=config)


def _create_button(config: ComponentConfig) -> ComponentInstance:
    size = config.visual.get("size", [26, 26])
    view = ButtonView(
        size=(int(size[0]), int(size[1])),
        on_color=str(config.visual.get("on_color", "#f59e0b")),
        off_color=str(config.visual.get("off_color", "#2f2f2f")),
        border_color=str(config.visual.get("border_color", "#111111")),
    )
    controller = ButtonController(config.id, config.binding, view)
    return ComponentInstance(view=view, controller=controller, config=config)


def _create_switch(config: ComponentConfig) -> ComponentInstance:
    size = config.visual.get("size", [26, 26])
    view = SwitchView(
        size=(int(size[0]), int(size[1])),
        on_color=str(config.visual.get("on_color", "#10b981")),
        off_color=str(config.visual.get("off_color", "#2f2f2f")),
        border_color=str(config.visual.get("border_color", "#111111")),
    )
    controller = SwitchController(config.id, config.binding, view)
    return ComponentInstance(view=view, controller=controller, config=config)


def default_registry() -> ComponentRegistry:
    registry = ComponentRegistry()
    registry.register("LED", _create_led)
    registry.register("BUTTON", _create_button)
    registry.register("SWITCH", _create_switch)
    return registry
