"""Abstract GPIO (General Purpose Input/Output) interface and implementation."""

from abc import abstractmethod
from enum import IntEnum
from typing import override

from simulator.interfaces.peripheral import BasePeripherals
from simulator.utils.config_loader import GPIO_Config


class PinMode(IntEnum):
    """GPIO pin mode enumeration."""

    INPUT = 0
    OUTPUT = 1
    INPUT_PULLUP = 2
    INPUT_PULLDOWN = 3
    ALTERNATE = 4


class PinLevel(IntEnum):
    """GPIO pin logic level enumeration."""

    LOW = 0
    HIGH = 1


class BaseGPIO(BasePeripherals):
    """Abstract GPIO peripheral with common register and pin operations.

    Provides both the interface contract and common implementation shared across
    different microcontroller GPIO implementations (TM4C123, STM32, etc).

    Subclasses must only define:
    - NUM_PINS: Number of pins in the GPIO port
    - set_port_state(): Device-specific port state masking
    - get_port_state(): Device-specific port state masking

    Attributes:
        _registers: Dictionary storing register values at their offsets.
        _pin_modes: Array storing the mode of each pin.
        _interrupt_config: Array storing interrupt configuration for each pin.
        _interrupt_flags: Array storing interrupt flag state for each pin.
        _gpio_config: GPIO configuration from config file.
    """

    # Subclasses must define these
    NUM_PINS: int
    MAX_PIN: int

    def __init__(
        self, gpio_config: GPIO_Config, initial_value: int = 0x00
    ) -> None:
        """Initialize GPIO peripheral.

        Args:
            gpio_config: GPIO configuration with register offsets and pin count.
            initial_value: Initial value for GPIO DATA register.
        """
        self._gpio_config = gpio_config
        self._initial_value = initial_value
        self._registers: dict[int, int] = {}

        self._pin_modes = [PinMode.INPUT] * self.NUM_PINS
        self._interrupt_config: dict[int, dict[str, bool]] = {
            i: {"edge_triggered": False} for i in range(self.NUM_PINS)
        }
        self._interrupt_flags = [False] * self.NUM_PINS

        # Initialize registers to default values
        self._registers[self._gpio_config.offsets.data] = initial_value
        self._registers[self._gpio_config.offsets.dir] = 0x00
        self._registers[self._gpio_config.offsets.is_] = 0x00
        self._registers[self._gpio_config.offsets.ibe] = 0x00
        self._registers[self._gpio_config.offsets.iev] = 0x00
        self._registers[self._gpio_config.offsets.im] = 0x00

    # ==========================================================
    # BasePeripherals Implementation (Common for all GPIO)
    # ==========================================================

    @override
    def write_register(self, offset: int, value: int) -> None:
        """Write a 32-bit value to a register.

        Args:
            offset: Register offset in bytes.
            value: 32-bit value to write.
        """
        value = value & 0xFFFFFFFF

        if offset == self._gpio_config.offsets.icr:
            # Clear interrupt flags
            for pin in range(self.NUM_PINS):
                if value & (1 << pin):
                    self._interrupt_flags[pin] = False
        else:
            self._registers[offset] = value

    @override
    def read_register(self, offset: int) -> int:
        """Read a 32-bit value from a register.

        Args:
            offset: Register offset in bytes.

        Returns:
            32-bit register value, or initial value if not yet written.
        """
        if offset == self._gpio_config.offsets.ris:
            value = 0
            for pin in range(self.NUM_PINS):
                if self._interrupt_flags[pin]:
                    value |= 1 << pin
            return value

        if offset == self._gpio_config.offsets.mis:
            raw = self.read_register(self._gpio_config.offsets.ris)
            mask = self._registers.get(self._gpio_config.offsets.im, 0)
            return raw & mask

        return self._registers.get(offset, self._initial_value)

    @override
    def write_data_masked(self, offset: int, value: int, mask: int) -> None:
        """Write value to masked bits in a register."""
        current = self.read_register(offset)
        modified = (current & ~mask) | (value & mask)
        self.write_register(offset, modified)

    @override
    def read_data_masked(self, offset: int, mask: int) -> int:
        """Read masked bits from a register."""
        return self.read_register(offset) & mask

    @override
    def reset(self) -> None:
        """Reset peripheral to power-on state."""
        self._registers.clear()
        self._pin_modes = [PinMode.INPUT] * self.NUM_PINS
        self._interrupt_flags = [False] * self.NUM_PINS
        for i in range(self.NUM_PINS):
            self._interrupt_config[i]["edge_triggered"] = False

        self._registers[self._gpio_config.offsets.data] = self._initial_value
        self._registers[self._gpio_config.offsets.dir] = 0x00

    # ==========================================================
    # GPIO-specific Pin Operations (Common Implementation)
    # ==========================================================

    @override
    def set_pin_mode(self, pin: int, mode: PinMode) -> None:
        """Configure the mode of a GPIO pin.

        Args:
            pin: Pin number (0 to NUM_PINS-1).
            mode: Pin mode (input, output, alternate function, etc).

        Raises:
            ValueError: If pin number is invalid.
        """
        if not 0 <= pin <= self.MAX_PIN:
            raise ValueError(f"Pin {pin} is out of range [0-{self.MAX_PIN}]")

        self._pin_modes[pin] = mode

        if mode in (PinMode.INPUT, PinMode.INPUT_PULLUP, PinMode.INPUT_PULLDOWN):
            gpio_dir = self.read_register(self._gpio_config.offsets.dir)
            gpio_dir &= ~(1 << pin)
            self.write_register(self._gpio_config.offsets.dir, gpio_dir)
        elif mode == PinMode.OUTPUT:
            gpio_dir = self.read_register(self._gpio_config.offsets.dir)
            gpio_dir |= 1 << pin
            self.write_register(self._gpio_config.offsets.dir, gpio_dir)
        elif mode == PinMode.ALTERNATE:
            afsel = self.read_register(self._gpio_config.offsets.afsel)
            afsel |= 1 << pin
            self.write_register(self._gpio_config.offsets.afsel, afsel)

    @override
    def get_pin_mode(self, pin: int) -> PinMode:
        """Get the current mode of a GPIO pin."""
        if not 0 <= pin <= self.MAX_PIN:
            raise ValueError(f"Pin {pin} is out of range [0-{self.MAX_PIN}]")
        return self._pin_modes[pin]

    @override
    def set_pin_value(self, pin: int, level: PinLevel) -> None:
        """Set the output level of a GPIO pin."""
        if not 0 <= pin <= self.MAX_PIN:
            raise ValueError(f"Pin {pin} is out of range [0-{self.MAX_PIN}]")

        gpio_data = self.read_register(self._gpio_config.offsets.data)
        if level == PinLevel.HIGH:
            gpio_data |= 1 << pin
        else:
            gpio_data &= ~(1 << pin)
        self.write_register(self._gpio_config.offsets.data, gpio_data)

    @override
    def get_pin_value(self, pin: int) -> PinLevel:
        """Read the current level of a GPIO pin."""
        if not 0 <= pin <= self.MAX_PIN:
            raise ValueError(f"Pin {pin} is out of range [0-{self.MAX_PIN}]")

        gpio_data = self.read_register(self._gpio_config.offsets.data)
        return PinLevel.HIGH if (gpio_data & (1 << pin)) else PinLevel.LOW

    @abstractmethod
    def set_port_state(self, value: int) -> None:
        """Set the state of all pins in the port at once.

        Abstract method - subclass must implement with appropriate bit masking.

        Args:
            value: Bitmask where each bit represents a pin level.
        """
        raise NotImplementedError

    @abstractmethod
    def get_port_state(self) -> int:
        """Read the current state of all pins in the port.

        Abstract method - subclass must implement with appropriate bit masking.

        Returns:
            Bitmask where each bit represents a pin level.
        """
        raise NotImplementedError

    @override
    def configure_interrupt(self, pin: int, edge_triggered: bool = True) -> None:
        """Configure interrupt for a GPIO pin."""
        if not 0 <= pin <= self.MAX_PIN:
            raise ValueError(f"Pin {pin} is out of range [0-{self.MAX_PIN}]")

        self._interrupt_config[pin]["edge_triggered"] = edge_triggered

        is_reg = self.read_register(self._gpio_config.offsets.is_)
        if edge_triggered:
            is_reg &= ~(1 << pin)
        else:
            is_reg |= 1 << pin
        self.write_register(self._gpio_config.offsets.is_, is_reg)

        im_reg = self.read_register(self._gpio_config.offsets.im)
        im_reg |= 1 << pin
        self.write_register(self._gpio_config.offsets.im, im_reg)

    @override
    def clear_interrupt_flag(self, pin: int) -> None:
        """Clear the interrupt flag for a GPIO pin."""
        if not 0 <= pin <= self.MAX_PIN:
            raise ValueError(f"Pin {pin} is out of range [0-{self.MAX_PIN}]")

        self._interrupt_flags[pin] = False
