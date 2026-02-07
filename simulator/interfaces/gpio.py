"""GPIO peripheral interface and base implementation."""

from abc import ABC, abstractmethod
from typing import override

from simulator.interfaces.peripheral import BasePeripherals
from simulator.interfaces.gpio_enums import PinMode
from simulator.utils.config_loader import GPIO_Config
from simulator.utils.consts import ConstUtils


class BaseGPIO(BasePeripherals, ABC):
    """Abstract base class for GPIO peripherals.
    
    Provides common register management, pin mode tracking, and interrupt
    handling for microcontroller GPIO ports. Subclasses implement
    MCU-specific behaviors like masked DATA register access (Tiva-C)
    or BSRR/BRR registers (STM32).
    
    Attributes:
        NUM_PINS: Number of pins in this GPIO port (e.g., 8 for TM4C123, 16 for STM32).
        MAX_PIN: Maximum pin index (NUM_PINS - 1).
    """

    NUM_PINS: int
    MAX_PIN: int

    def __init__(self, gpio_config: GPIO_Config, initial_value: int = 0x00) -> None:
        """Initialize the GPIO peripheral.
        
        Args:
            gpio_config: Configuration object containing register offsets and settings.
            initial_value: Initial value for the DATA register. Defaults to 0x00.
        """
        self._gpio_config = gpio_config
        self._initial_value = initial_value
        self._registers: dict[int, int] = {}
        self._pin_modes: list[int] = [PinMode.INPUT] * self.NUM_PINS
        self._interrupt_flags: int = 0
        self._interrupt_config: dict[int, dict[str, bool]] = {
            i: {"edge_triggered": False} for i in range(self.NUM_PINS)
        }
        # Initialize DATA register
        self._registers[self._gpio_config.offsets.data] = initial_value

    @abstractmethod
    def set_port_state(self, value: int) -> None:
        """Set the state of all pins in the port.
        
        Args:
            value: Bitmask where each bit represents a pin level.
        
        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError

    @abstractmethod
    def get_port_state(self) -> int:
        """Get the current state of all pins in the port.
        
        Returns:
            Bitmask where each bit represents the current pin level.
        
        Raises:
            NotImplementedError: Subclasses must implement this method.
        """
        raise NotImplementedError

    @override
    def write_register(self, offset: int, value: int) -> None:
        """Write a 32-bit value to a register.
        
        Masks the value to 32 bits and stores in the register dictionary.
        Subclasses may override to handle special register behavior
        (e.g., masked DATA access, BSRR/BRR registers).
        
        Args:
            offset: Register offset in bytes.
            value: 32-bit value to write.
        """
        value &= ConstUtils.MASK_32_BITS
        self._registers[offset] = value

    @override
    def read_register(self, offset: int) -> int:
        """Read a 32-bit value from a register.
        
        Returns the register value, or the initial value if register
        has not been written yet.
        Subclasses may override for special register behaviors.
        
        Args:
            offset: Register offset in bytes.
        
        Returns:
            32-bit register value.
        """
        return self._registers.get(offset, self._initial_value)

    @override
    def reset(self) -> None:
        """Reset the GPIO peripheral to power-on state.
        
        Clears all registers, resets pin modes to INPUT, clears interrupt
        flags, and restores the DATA register to its initial value.
        """
        self._registers.clear()
        self._registers[self._gpio_config.offsets.data] = self._initial_value
        self._pin_modes = [PinMode.INPUT] * self.NUM_PINS
        self._interrupt_flags = 0
        self._interrupt_config = {
            i: {"edge_triggered": False} for i in range(self.NUM_PINS)
        }

