"""A board assembled from its configuration.

Every supported chip is the same machine: CPU, address space, clock, interrupt
controller, a system-control block and a set of GPIO ports, all described by the
board's `config.yaml`. What differs per chip is only named by a `BoardSpec`: the
config file, the GPIO implementation and the memory-access model.
A new board is therefore a `BoardSpec` and a one-line subclass, not a copy of this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from simulator.core.builders import (
    create_address_space_from_config,
    create_cpu_for_address_space,
)
from simulator.core.clock import Clock
from simulator.core.cpu import CortexM
from simulator.core.interrupt_controller import InterruptController
from simulator.core.memmap import AddressSpace
from simulator.core.sysctl import SysCtl
from simulator.interfaces.board import Board
from simulator.interfaces.memory_access import MemoryAccessModel
from simulator.interfaces.peripheral import Peripheral
from simulator.utils.config_loader import load_config

SYSCTL_NAME = "SYSCTL"
GPIO_PREFIX = "GPIO_"


@dataclass(frozen=True)
class BoardSpec:
    """What makes one chip different from another."""

    key: str  # registry key and config key, e.g. "stm32f4"
    name: str  # human readable name
    config_path: Path
    gpio_kind: str  # the `gpio.kind` its config must declare
    gpio_class: Callable[..., Peripheral]  # one GPIO port implementation
    access_model: Callable[[int], MemoryAccessModel]  # built from the first port base


class ConfiguredBoard(Board):
    """A complete board built from `spec` (set it in the subclass)."""

    spec: BoardSpec

    def __init__(self, **_kwargs: Any):
        self.config = load_config(self.spec.key, path=str(self.spec.config_path))
        self._address_space = create_address_space_from_config(self.config.memory)
        self._cpu = create_cpu_for_address_space(self._address_space)
        first_port = next(iter(self.config.gpio.ports.values()), 0)
        self._memory_access_model = self.spec.access_model(first_port)
        self._clock = Clock()
        self._interrupt_ctrl = InterruptController(self._clock)
        self._interrupt_ctrl.attach_cpu(self._cpu)
        self._peripherals: dict[str, Peripheral] = {}
        self._init_sysctl()
        self._init_gpio()
        self._wire_clock_and_interrupts()

    def _pin_data_mask(self) -> int:
        """Union of the configured pin masks."""
        mask = 0
        for value in self.config.pins.pin_masks.values():
            mask |= value
        if mask == 0:
            raise ValueError("GPIO pin mask is empty; check config.pins.pin_masks")
        return mask

    def _register(
        self, name: str, base: int, size: int, peripheral: Peripheral
    ) -> None:
        self._peripherals[name] = peripheral
        self._address_space.register_peripheral(base, size, peripheral)

    def _init_sysctl(self) -> None:
        cfg = self.config.sysctl
        sysctl = SysCtl(cfg, base_addr=cfg.base, name=SYSCTL_NAME)
        self._register(SYSCTL_NAME, cfg.base, sysctl.size, sysctl)

    def _init_gpio(self) -> None:
        cfg = self.config.gpio
        if cfg.kind != self.spec.gpio_kind:
            raise ValueError(
                f"Expected {self.spec.gpio_kind} GPIO config, got {cfg.kind}"
            )
        data_mask = self._pin_data_mask()
        for port, base in cfg.ports.items():
            name = f"{GPIO_PREFIX}{port}"
            gpio = self.spec.gpio_class(
                cfg, data_mask=data_mask, initial_value=0, base_addr=base, name=name
            )
            self._register(name, base, cfg.port_size, gpio)

    def _wire_clock_and_interrupts(self) -> None:
        """Subscribe the CPU and every peripheral to the clock and interrupt controller."""
        self._clock.subscribe(self._cpu)
        for periph in self._peripherals.values():
            if hasattr(periph, "tick"):
                self._clock.subscribe(periph)
            if hasattr(periph, "attach_interrupt_controller"):
                periph.attach_interrupt_controller(self._interrupt_ctrl)
            self._interrupt_ctrl.subscribe(periph)

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def cpu(self) -> CortexM:
        return self._cpu

    @property
    def address_space(self) -> AddressSpace:
        return self._address_space

    @property
    def memory_map(self) -> AddressSpace:
        return self._address_space

    @property
    def peripherals(self) -> dict[str, Peripheral]:
        return self._peripherals

    @property
    def clock(self) -> Clock:
        return self._clock

    @property
    def interrupt_ctrl(self) -> InterruptController:
        return self._interrupt_ctrl

    @property
    def memory_access_model(self) -> MemoryAccessModel:
        return self._memory_access_model

    def reset(self) -> None:
        self._address_space.reset()
        self._cpu.reset()
        self._interrupt_ctrl.reset()
        self._clock.reset()

    def step(self, cycles: int = 1) -> None:
        self._clock.tick(cycles)

    def read(self, address: int, size: int = 4) -> int:
        return self._address_space.read(address, size)

    def write(self, address: int, size: int, value: int) -> None:
        self._address_space.write(address, size, value)
