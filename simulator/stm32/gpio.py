"""STM32 GPIO peripheral implementation."""

from typing import override

from simulator.interfaces.gpio import BaseGPIO
from simulator.utils.config_loader import GPIO_Config
from simulator.utils.consts import ConstUtils


class STM32_GPIO(BaseGPIO):
    """STM32 GPIO peripheral implementation.
    
    Manages GPIO registers for an STM32 microcontroller with 16 pins per port.
    
    STM32 GPIO features:
    - 16-pin ports for comprehensive I/O capabilities
    - BSRR (Bit Set/Reset Register) for atomic pin operations
    - BRR (Bit Reset Register) for atomic pin resets
    - Port-wide operations via the ODR (Output Data Register)
    
    Inherits common register operations and pin management from BaseGPIO.
    For STM32-specific register behaviors (BSRR, BRR), subclasses may
    override write_register() to handle these special cases.
    """

    NUM_PINS: int = 16
    """Number of GPIO pins per port on STM32."""

    MAX_PIN: int = 15
    """Maximum GPIO pin index (0-15)."""

    def __init__(self, gpio_config: GPIO_Config, initial_value: int = 0x0000) -> None:
        """Initialize STM32 GPIO peripheral with 16 pins.
        
        Args:
            gpio_config: GPIO configuration with register offsets.
            initial_value: Initial value for GPIO DATA register. Defaults to 0x0000.
        """
        super().__init__(gpio_config=gpio_config, initial_value=initial_value)

    @override
    def set_port_state(self, value: int) -> None:
        """Set the state of all 16 pins in the port.
        
        Args:
            value: Bitmask where each bit represents a pin level.
                   Only lower 16 bits are used.
        """
        value = value & ConstUtils.MASK_16_BITS
        self.write_register(self._gpio_config.offsets.data, value)

    @override
    def get_port_state(self) -> int:
        """Get the current state of all 16 pins in the port.
        
        Returns:
            Bitmask where each bit represents the current pin level (16 bits).
        """
        return self.read_register(self._gpio_config.offsets.data) & ConstUtils.MASK_16_BITS

