"""STM32 GPIO peripheral implementation."""

from typing import override

from simulator.interfaces.gpio import BaseGPIO
from simulator.utils.config_loader import GPIO_Config


class STM32_GPIO(BaseGPIO):
    """STM32 GPIO peripheral implementation.

    Manages GPIO registers for an STM32 microcontroller with 16 pins.

    Inherits common register operations and pin management from
    BaseGPIOPeripheral, providing only device-specific implementation
    of port state operations.
    """

    NUM_PINS = 16
    MAX_PIN = 15

    def __init__(
        self, gpio_config: GPIO_Config, initial_value: int = 0x0000
    ) -> None:
        """Initialize STM32 GPIO peripheral with 16 pins.

        Args:
            gpio_config: GPIO configuration with register offsets.
            initial_value: Initial value for GPIO DATA register (default: 0x0000).
        """
        super().__init__(gpio_config=gpio_config, initial_value=initial_value)

    @override
    def set_port_state(self, value: int) -> None:
        """Set the state of all 16 pins in the port at once.

        Args:
            value: Bitmask where each bit represents a pin level.
                   Only lower 16 bits are used.
        """
        value = value & 0xFFFF
        self.write_register(self._gpio_config.offsets.data, value)

    @override
    def get_port_state(self) -> int:
        """Read the current state of all 16 pins in the port.

        Returns:
            Bitmask where each bit represents a pin level (16 bits).
        """
        return self.read_register(self._gpio_config.offsets.data) & 0xFFFF
