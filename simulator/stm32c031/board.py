"""STM32C031 board implementation.

Wires together:
- CortexM CPU
- Address space (Flash, SRAM, MMIO)
- STM32 GPIO peripherals
"""

from pathlib import Path
from typing import Any

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
from simulator.stm32.gpio import STM32GPIO
from simulator.stm32.memory_access import STM32F4DirectAccessModel
from simulator.utils.config_loader import load_config


class STM32C031Board(Board):
    """STM32C031 micro board with ARM Cortex-M0+."""

    def __init__(self, **_kwargs: Any):
        # Load board configuration from variant's local config file
        config_path = Path(__file__).parent / "config.yaml"
        config = load_config("stm32c031", path=str(config_path))
        self.config = config

        # Use factory to create address space
        self._address_space = create_address_space_from_config(config.memory)

        # Use factory to create and initialize CPU
        self._cpu = create_cpu_for_address_space(self._address_space)

        # Memory access model for this board's peripherals
        gpio_base = (
            list(config.gpio.ports.values())[0] if config.gpio.ports else 0x50000000
        )
        self._memory_access_model = STM32F4DirectAccessModel(gpio_base)

        # Core timing + interrupt infrastructure
        self._clock = Clock()
        self._interrupt_ctrl = InterruptController(self._clock)
        self._interrupt_ctrl.attach_cpu(self._cpu)

        # Initialize peripherals
        self._peripherals: dict[str, Peripheral] = {}
        self._init_sysctl()
        self._init_gpio()
        self._wire_clock_and_interrupts()

    def _pin_data_mask(self) -> int:
        """Compute GPIO data mask from config pin masks."""
        mask = 0
        for value in self.config.pins.pin_masks.values():
            mask |= value
        if mask == 0:
            raise ValueError("GPIO pin mask is empty; check config.pins.pin_masks")
        return mask

    def _init_sysctl(self) -> None:
        """Initialize system control (RCC/SYSCTL) registers."""
        sysctl_cfg = self.config.sysctl
        sysctl = SysCtl(sysctl_cfg, base_addr=sysctl_cfg.base, name="SYSCTL")
        self._peripherals["SYSCTL"] = sysctl
        self._address_space.register_peripheral(
            sysctl_cfg.base,
            sysctl.size,
            sysctl,
        )

    def _init_gpio(self) -> None:
        """Initialize GPIO ports."""
        gpio_config = self.config.gpio
        if gpio_config.kind != "stm32":
            raise ValueError(f"Expected stm32 GPIO config, got {gpio_config.kind}")
        data_mask = self._pin_data_mask()

        for port_name, base_address in gpio_config.ports.items():
            gpio = STM32GPIO(
                gpio_config,
                data_mask=data_mask,
                initial_value=0x0000,
                base_addr=base_address,
                name=f"GPIO_{port_name}",
            )

            # Register in peripheral dict and address space
            self._peripherals[f"GPIO_{port_name}"] = gpio
            self._address_space.register_peripheral(
                base_address,
                gpio_config.port_size,
                gpio,
            )

    def _wire_clock_and_interrupts(self) -> None:
        """Wire CPU/peripherals to the clock and interrupt controller."""
        self._clock.subscribe(self._cpu)
        for periph in self._peripherals.values():
            # Clock subscription (if supported)
            if hasattr(periph, "tick"):
                self._clock.subscribe(periph)
            # Interrupt registration
            if hasattr(periph, "attach_interrupt_controller"):
                periph.attach_interrupt_controller(self._interrupt_ctrl)
            self._interrupt_ctrl.subscribe(periph)

    @property
    def name(self) -> str:
        return "STM32C031"

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
        """Reset the entire board."""
        self._address_space.reset()
        self._cpu.reset()
        self._interrupt_ctrl.reset()
        self._clock.reset()

    def step(self, cycles: int = 1) -> None:
        """Advance the board by a number of cycles."""
        self._clock.tick(cycles)

    def read(self, address: int, size: int = 4) -> int:
        """Read from the board address space."""
        return self._address_space.read(address, size)

    def write(self, address: int, size: int, value: int) -> None:
        """Write to the board address space."""
        self._address_space.write(address, size, value)
