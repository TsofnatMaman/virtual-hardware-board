"""TM4C123 GPIO peripheral implementation."""

from typing import override

from simulator.interfaces.gpio import BaseGPIO
from simulator.utils.config_loader import GPIO_Config


class TM4C123GPIO(BaseGPIO):
    """TM4C123 GPIO peripheral implementation.

    Manages GPIO registers for a TM4C123 microcontroller with 8 pins.

    Inherits common register operations and pin management from
    BaseGPIOPeripheral, providing only device-specific implementation
    of port state operations.
    """

    NUM_PINS = 8
    MAX_PIN = 7

    def __init__(
        self, gpio_config: GPIO_Config, initial_value: int = 0x00
    ) -> None:
        """Initialize TM4C123 GPIO peripheral with 8 pins.

        Args:
            gpio_config: GPIO configuration with register offsets.
            initial_value: Initial value for GPIO DATA register (default: 0x00).
        """
        super().__init__(gpio_config=gpio_config, initial_value=initial_value)

    @override
    def set_port_state(self, value: int) -> None:
        """Set the state of all 8 pins in the port at once.

        Args:
            value: Bitmask where each bit represents a pin level.
                   Only lower 8 bits are used.
        """
        value = value & 0xFF
        self.write_register(self._gpio_config.offsets.data, value)

    @override
    def get_port_state(self) -> int:
        """Read the current state of all 8 pins in the port.

        Returns:
            Bitmask where each bit represents a pin level (8 bits).
        """
        return self.read_register(self._gpio_config.offsets.data) & 0xFF


