"""TM4C123 (Tiva-C) GPIO peripheral implementation."""

from typing import override

from simulator.interfaces.gpio import BaseGPIO
from simulator.interfaces.gpio_enums import PinMode
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
    
    Uses BaseGPIO's _pin_modes list and _interrupt_config dict for tracking
    pin modes and interrupt configurations. Tiva-C specific register behavior
    (DIR, AFSEL, IS, IM, masked DATA) is implemented in write_register and
    read_register overrides.
    
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
    def write(self, offset: int, size: int, value: int) -> None:
        """Write to a TM4C123 GPIO register.
        
        Implements Tiva-C masked DATA register behavior:
        - Direct writes to the DATA register (exact offset match) bypass masking
        - Addresses from (DATA + 0x004) to (DATA + 0x3FC) perform masked writes
        - The offset difference >> 2 becomes the write mask
        - Interrupt status register (ICR) handles interrupt flag clearing
        - DIR and AFSEL registers update _pin_modes array from BaseGPIO
        - IS register updates _interrupt_config dict from BaseGPIO
        
        Args:
            offset: Register offset in bytes.
            value: Value to write.
        """
        # Masked DATA register access (only for offset > data base, not equal)
        if (
            self._gpio_config.offsets.data < offset
            <= self._gpio_config.offsets.data + ConstUtils.DATA_MASKED_MAX_OFFSET
        ):
            # Calculate the mask from the offset (mask is derived from address bits)
            mask = (offset - self._gpio_config.offsets.data) >> 2
            # We expect 32-bit writes for masked DATA areas; ensure size is 4
            if size != 4:
                raise ValueError("masked DATA writes must be 4 bytes")
            current = self._registers.get(self._gpio_config.offsets.data, 0)
            self._registers[self._gpio_config.offsets.data] = (current & ~mask) | (
                value & mask
            )
            return

        # Interrupt Clear Register (ICR)
        if offset == self._gpio_config.offsets.icr:
            # ICR is written with a mask of bits to clear
            if size != 4:
                raise ValueError("ICR writes must be 4 bytes")
            self._interrupt_flags &= ~value
            return

        # Direction register - controls pin modes (OUTPUT when set)
        # Update _pin_modes array based on DIR and AFSEL values
        if offset == self._gpio_config.offsets.dir:
            # DIR is an 8-bit register
            if size not in (1, 4):
                raise ValueError("DIR writes must be 1 or 4 bytes")
            value &= ConstUtils.MASK_8_BITS
            afsel = self._registers.get(self._gpio_config.offsets.afsel, 0)
            for pin in range(self.NUM_PINS):
                if value & (1 << pin):
                    self._pin_modes[pin] = PinMode.OUTPUT
                elif not (afsel & (1 << pin)):
                    self._pin_modes[pin] = PinMode.INPUT
            self._registers[offset] = value
            return

        # Alternate Function Select register - controls pin modes (ALTERNATE when set)
        # Update _pin_modes array based on AFSEL and DIR values
        if offset == self._gpio_config.offsets.afsel:
            if size not in (1, 4):
                raise ValueError("AFSEL writes must be 1 or 4 bytes")
            value &= ConstUtils.MASK_8_BITS
            dir_val = self._registers.get(self._gpio_config.offsets.dir, 0)
            for pin in range(self.NUM_PINS):
                if value & (1 << pin):
                    self._pin_modes[pin] = PinMode.ALTERNATE
                elif not (dir_val & (1 << pin)):
                    self._pin_modes[pin] = PinMode.INPUT
            self._registers[offset] = value
            return

        # Interrupt Sense register (IS) - controls edge vs level triggered
        # Update _interrupt_config dict from BaseGPIO
        if offset == self._gpio_config.offsets.is_:
            if size not in (1, 4):
                raise ValueError("IS writes must be 1 or 4 bytes")
            value &= ConstUtils.MASK_8_BITS
            for pin in range(self.NUM_PINS):
                # IS register: 0 = edge-triggered, 1 = level-triggered
                self._interrupt_config[pin]["edge_triggered"] = not (value & (1 << pin))
            self._registers[offset] = value
            return

        # Interrupt Mask register (IM)
        if offset == self._gpio_config.offsets.im:
            self._registers[offset] = value & ConstUtils.MASK_8_BITS
            return

        # All other registers
        super().write(offset, size, value)

    @override
    def read(self, offset: int, size: int) -> int:
        """Read from a TM4C123 GPIO register.
        
        Implements Tiva-C masked DATA register behavior:
        - Direct reads from DATA register return full 8-bit value
        - Addresses from (DATA + 0x004) to (DATA + 0x3FC) perform masked reads
        - Returns only the masked bits of the DATA register
        - Raw Interrupt Status (RIS) returns current interrupt flags
        - Masked Interrupt Status (MIS) applies interrupt mask
        
        Args:
            offset: Register offset in bytes.
        
        Returns:
            Register value.
        """
        # Direct DATA register read (return full value)
        if offset == self._gpio_config.offsets.data:
            return self._registers.get(offset, self._initial_value) & ((1 << (size * 8)) - 1)

        # Masked DATA register access (only for offset > data base)
        if (
            self._gpio_config.offsets.data < offset
            <= self._gpio_config.offsets.data + ConstUtils.DATA_MASKED_MAX_OFFSET
        ):
            mask = (offset - self._gpio_config.offsets.data) >> 2
            return self._registers.get(self._gpio_config.offsets.data, self._initial_value) & mask

        # Raw Interrupt Status Register (RIS)
        if offset == self._gpio_config.offsets.ris:
            return self._interrupt_flags & ((1 << self.NUM_PINS) - 1)

        # Masked Interrupt Status Register (MIS)
        if offset == self._gpio_config.offsets.mis:
            im_value = self._registers.get(self._gpio_config.offsets.im, 0)
            return self._interrupt_flags & im_value

        # All other registers
        return super().read(offset, size)

    @override
    def set_port_state(self, value: int) -> None:
        """Set the state of all 8 pins in the port.
        
        Args:
            value: Bitmask where each bit represents a pin level.
                   Only lower 8 bits are used.
        """
        value &= ConstUtils.MASK_8_BITS
        self.write(self._gpio_config.offsets.data, 4, value)

    @override
    def get_port_state(self) -> int:
        """Get the current state of all 8 pins in the port.
        
        Returns:
            Bitmask where each bit represents the current pin level (8 bits).
        """
        return self.read(self._gpio_config.offsets.data, 4) & ConstUtils.MASK_8_BITS

    @override
    def set_pin_mode(self, pin: int, mode: int) -> None:
        """Set the mode (direction) of a specific pin for TM4C123.
        
        Updates DIR and AFSEL registers and _pin_modes array from BaseGPIO.
        
        Args:
            pin: Pin index (0 to 7).
            mode: Pin mode from PinMode enum (INPUT, OUTPUT, ALTERNATE).
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        
        # Call base class to update _pin_modes array
        super().set_pin_mode(pin, mode)
        
        # Update DIR and AFSEL registers to match pin mode
        pin_mask = 1 << pin
        dir_value = self._registers.get(self._gpio_config.offsets.dir, 0)
        afsel_value = self._registers.get(self._gpio_config.offsets.afsel, 0)
        
        if mode == PinMode.OUTPUT:
            # Set DIR bit, clear AFSEL bit
            dir_value |= pin_mask
            afsel_value &= ~pin_mask
        elif mode == PinMode.ALTERNATE:
            # Set AFSEL bit, clear DIR bit
            afsel_value |= pin_mask
            dir_value &= ~pin_mask
        else:  # INPUT
            # Clear both DIR and AFSEL bits
            dir_value &= ~pin_mask
            afsel_value &= ~pin_mask
        
        self._registers[self._gpio_config.offsets.dir] = dir_value & ConstUtils.MASK_8_BITS
        self._registers[self._gpio_config.offsets.afsel] = afsel_value & ConstUtils.MASK_8_BITS

    @override
    def configure_interrupt(self, pin: int, edge_triggered: bool = True) -> None:
        """Configure interrupt for a specific pin on TM4C123.
        
        Updates IS register (0 for edge-triggered, 1 for level-triggered)
        and IM register, also updates _interrupt_config from BaseGPIO.
        
        Args:
            pin: Pin index (0 to 7).
            edge_triggered: True for edge-triggered, False for level-triggered.
        
        Raises:
            ValueError: If pin is out of range.
        """
        if not (0 <= pin < self.NUM_PINS):
            raise ValueError(f"Pin {pin} out of range [0, {self.NUM_PINS-1}]")
        
        # Call base class to update _interrupt_config dict
        super().configure_interrupt(pin, edge_triggered)
        
        # Update IS register: 0 = edge-triggered, 1 = level-triggered
        is_value = self._registers.get(self._gpio_config.offsets.is_, 0)
        pin_mask = 1 << pin
        if edge_triggered:
            is_value &= ~pin_mask
        else:
            is_value |= pin_mask
        self._registers[self._gpio_config.offsets.is_] = is_value & ConstUtils.MASK_8_BITS
        
        # Update IM register to enable interrupt for this pin
        im_value = self._registers.get(self._gpio_config.offsets.im, 0)
        im_value |= pin_mask
        self._registers[self._gpio_config.offsets.im] = im_value & ConstUtils.MASK_8_BITS

    @override
    def reset(self) -> None:
        """Reset the GPIO peripheral to power-on state.
        
        Clears all registers and resets inherited structures. All pins return to INPUT mode.
        """
        super().reset()
        self._registers.clear()
        self._registers[self._gpio_config.offsets.data] = self._initial_value
        self._interrupt_flags = 0
