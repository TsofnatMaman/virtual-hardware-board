"""STM32 GPIO peripheral implementation."""

from typing import Callable, override

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
        
        # Map offsets to read handlers to avoid if/else chains
        self._read_handlers: dict[int, Callable[[], int]] = {}
        if hasattr(self._gpio_config.offsets, 'mis'):
            self._read_handlers[self._gpio_config.offsets.mis] = self._read_mis

    @override
    def set_port_state(self, value: int) -> None:
        """Set the state of all 16 pins in the port.
        
        Args:
            value: Bitmask where each bit represents a pin level.
                   Only lower 16 bits are used.
        """
        value = value & ConstUtils.MASK_16_BITS
        self.write(self._gpio_config.offsets.data, 4, value)

    @override
    def get_port_state(self) -> int:
        """Get the current state of all 16 pins in the port.
        
        Returns:
            Bitmask where each bit represents the current pin level (16 bits).
        """
        return self.read(self._gpio_config.offsets.data, 4) & ConstUtils.MASK_16_BITS

    @override
    def read_register(self, offset: int) -> int:
        """Read from an STM32 GPIO register.
        Uses handler mapping for special registers (like MIS).
        
        Args:
            offset: Register offset in bytes.
        
        Returns:
            Register value.
        """
        if handler := self._read_handlers.get(offset):
            return handler()

        return super().read(offset, 4)

    def _read_mis(self) -> int:
        """Handler for Masked Interrupt Status register."""
        im_value = self._registers.get(self._gpio_config.offsets.im, 0)
        return self._interrupt_flags & im_value

    @override
    def configure_interrupt(self, pin: int, edge_triggered: bool = True) -> None:
        """Configure interrupt for a specific pin on STM32.
        
        Calls base implementation and also updates the IM (Interrupt Mask) register.
        
        Args:
            pin: Pin index (0 to 15).
            edge_triggered: True for edge-triggered, False for level-triggered.
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        
        # Call base implementation to update interrupt config
        super().configure_interrupt(pin, edge_triggered)
        
        # Update IM register to enable interrupt for this pin
        im_value = self._registers.get(self._gpio_config.offsets.im, 0)
        im_value |= (1 << pin)
        self._registers[self._gpio_config.offsets.im] = im_value & ConstUtils.MASK_16_BITS