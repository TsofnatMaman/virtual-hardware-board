"""TM4C123 (Tiva-C) GPIO peripheral implementation."""

from typing import override

from simulator.interfaces.gpio import BaseGPIO
from simulator.utils.config_loader import GPIO_Config
from simulator.utils.consts import ConstUtils


class TM4C123_GPIO(BaseGPIO):
    """TM4C123 (Tiva-C Launchpad) GPIO peripheral implementation.
    
    Manages GPIO registers for a Tiva-C TM4C123 microcontroller with 8 pins
    per port. Implements Tiva-C specific features:
    
    - Masked DATA register: Bits [9:2] of the DATA register address act as
      a mask for selective read/write operations, allowing atomic access
      to subsets of pins without affecting others.
    - Port-wide I/O: Supports setting/getting all 8 pins at once.
    - Interrupt handling: Interrupt status via RIS and clearing via ICR.
    
    Inherits common register operations and pin management from BaseGPIO.
    """

    NUM_PINS: int = 8
    """Number of GPIO pins per port on TM4C123."""

    MAX_PIN: int = 7
    """Maximum GPIO pin index (0-7)."""

    def __init__(self, gpio_config: GPIO_Config, initial_value: int = 0x00) -> None:
        """Initialize TM4C123 GPIO peripheral with 8 pins.
        
        Args:
            gpio_config: GPIO configuration with register offsets.
            initial_value: Initial value for GPIO DATA register. Defaults to 0x00.
        """
        super().__init__(gpio_config=gpio_config, initial_value=initial_value)

    @override
    def write_register(self, offset: int, value: int) -> None:
        """Write to a TM4C123 GPIO register.
        
        Implements Tiva-C masked DATA register behavior:
        - Addresses from (DATA + 0x000) to (DATA + 0x3FC) perform masked writes
        - The offset difference >> 2 becomes the write mask
        - Interrupt status register (ICR) handles interrupt flag clearing
        
        Args:
            offset: Register offset in bytes.
            value: Value to write.
        """
        # Masked DATA register access
        if (
            self._gpio_config.offsets.data
            <= offset
            <= self._gpio_config.offsets.data + ConstUtils.DATA_MASKED_MAX_OFFSET
        ):
            # Calculate the mask from the offset
            mask = (offset - self._gpio_config.offsets.data) >> 2
            current = self._registers.get(self._gpio_config.offsets.data, 0)
            self._registers[self._gpio_config.offsets.data] = (current & ~mask) | (
                value & mask
            )
            return

        # Interrupt Clear Register (ICR)
        if offset == self._gpio_config.offsets.icr:
            self._interrupt_flags &= ~value
            return

        # All other registers
        super().write_register(offset, value)

    @override
    def read_register(self, offset: int) -> int:
        """Read from a TM4C123 GPIO register.
        
        Implements Tiva-C masked DATA register behavior:
        - Addresses from (DATA + 0x000) to (DATA + 0x3FC) perform masked reads
        - Returns only the masked bits of the DATA register
        - Raw Interrupt Status (RIS) returns current interrupt flags
        
        Args:
            offset: Register offset in bytes.
        
        Returns:
            Register value.
        """
        # Masked DATA register access
        if (
            self._gpio_config.offsets.data
            <= offset
            <= self._gpio_config.offsets.data + ConstUtils.DATA_MASKED_MAX_OFFSET
        ):
            mask = (offset - self._gpio_config.offsets.data) >> 2
            return self._registers.get(self._gpio_config.offsets.data, 0) & mask

        # Raw Interrupt Status Register (RIS)
        if offset == self._gpio_config.offsets.ris:
            return self._interrupt_flags & ((1 << self.NUM_PINS) - 1)

        # All other registers
        return super().read_register(offset)

    @override
    def set_port_state(self, value: int) -> None:
        """Set the state of all 8 pins in the port.
        
        Args:
            value: Bitmask where each bit represents a pin level.
                   Only lower 8 bits are used.
        """
        value &= ConstUtils.MASK_8_BITS
        self.write_register(self._gpio_config.offsets.data, value)

    @override
    def get_port_state(self) -> int:
        """Get the current state of all 8 pins in the port.
        
        Returns:
            Bitmask where each bit represents the current pin level (8 bits).
        """
        return self.read_register(self._gpio_config.offsets.data) & ConstUtils.MASK_8_BITS
