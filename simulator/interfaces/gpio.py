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
    def write(self, offset: int, size: int, value: int) -> None:
        """Write a value to a register or register field.

        Stores register values in a 32-bit backing map. Smaller writes
        update the low-order bytes. Subclasses may override for special
        behavior.
        """
        if size not in (1, 2, 4):
            raise ValueError("unsupported write size")
        mask = (1 << (size * 8)) - 1
        current = self._registers.get(offset, self._initial_value)
        new = (current & ~mask) | (value & mask)
        self._registers[offset] = new & ConstUtils.MASK_32_BITS

    @override
    def read(self, offset: int, size: int) -> int:
        """Read a value from a register.

        Returns the low-order `size` bytes of the stored 32-bit register
        value.
        """
        if size not in (1, 2, 4):
            raise ValueError("unsupported read size")
        mask = (1 << (size * 8)) - 1
        return self._registers.get(offset, self._initial_value) & mask

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

    def set_pin_mode(self, pin: int, mode: int) -> None:
        """Set the mode (direction/function) of a specific pin.
        
        Args:
            pin: Pin index (0 to NUM_PINS-1).
            mode: Pin mode from PinMode enum (INPUT, OUTPUT, ALTERNATE).
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        self._pin_modes[pin] = mode

    def get_pin_mode(self, pin: int) -> int:
        """Get the mode (direction/function) of a specific pin.
        
        Args:
            pin: Pin index (0 to NUM_PINS-1).
        
        Returns:
            Pin mode from PinMode enum.
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        return self._pin_modes[pin]

    def set_pin_value(self, pin: int, level: int) -> None:
        """Set the value (HIGH/LOW) of a specific pin.
        
        Args:
            pin: Pin index (0 to NUM_PINS-1).
            level: Pin level from PinLevel enum (LOW=0 or HIGH=1).
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        current_state = self.get_port_state()
        if level:
            current_state |= (1 << pin)
        else:
            current_state &= ~(1 << pin)
        self.set_port_state(current_state)

    def get_pin_value(self, pin: int) -> int:
        """Get the value (HIGH/LOW) of a specific pin.
        
        Args:
            pin: Pin index (0 to NUM_PINS-1).
        
        Returns:
            Pin level (0 for LOW, 1 for HIGH).
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        port_state = self.get_port_state()
        return (port_state >> pin) & 1

    def configure_interrupt(self, pin: int, edge_triggered: bool = True) -> None:
        """Configure interrupt for a specific pin.
        
        Args:
            pin: Pin index (0 to NUM_PINS-1).
            edge_triggered: True for edge-triggered, False for level-triggered.
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        self._interrupt_config[pin]["edge_triggered"] = edge_triggered

    def clear_interrupt_flag(self, pin: int) -> None:
        """Clear the interrupt flag for a specific pin.
        
        Args:
            pin: Pin index (0 to NUM_PINS-1).
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        self._interrupt_flags &= ~(1 << pin)

    def set_interrupt_flag(self, pin: int) -> None:
        """Set the interrupt flag for a specific pin."""
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        self._interrupt_flags |= (1 << pin)

    def get_interrupt_flag(self, pin: int) -> bool:
        """Return True if the interrupt flag for `pin` is set."""
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        return bool((self._interrupt_flags >> pin) & 1)

