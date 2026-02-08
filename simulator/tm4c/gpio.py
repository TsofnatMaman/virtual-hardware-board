"""TM4C123GH6PM GPIO peripheral with bit-banded addressing.

MEMORY ACCESS PATTERN: Bit-Banded Addressing (Hardware Feature)
===============================================================
TM4C123 uses a unique "masked data window" where the address itself
encodes which bits of the GPIO data register are accessible:

  mask = 1 << ((address_offset >> 2) & 0x7)

This allows atomic single-bit or multi-bit operations without RMW cycles.

Register Layout:
  DATA @ 0x3FC (8-bit I/O register)
  DIR @ 0x400 (pin direction: 1=output, 0=input)  
  DEN @ 0x51C (digital enable)
  AFSEL @ 0x420 (alternate function select)
  
Interrupt Registers:
  RIS @ 0x414 (raw interrupt status)
  MIS @ 0x418 (masked interrupt status, read-only)
  ICR @ 0x41C (interrupt clear, write-only)
  IS, IBE, IEV, IM control interrupt behavior
  
MASKED DATA WINDOW:
  The DATA register is accessed through a 1024-byte window (0x00-0x3FC):
  
  - Address DATA+0x000: Full I/O register access (all 8 bits)
  - Address DATA+0x004: Select only bit 0 (mask = 0x01)
  - Address DATA+0x008: Select only bit 1 (mask = 0x02)
  - Address DATA+0x00C: Select only bit 2 (mask = 0x04)
  - ...
  - Address DATA+0x3E0: Select only bit 7 (mask = 0x80)
  - Address DATA+0x3FC: Full I/O register access (all 8 bits, same as +0x000)
  
Example:
  Reading address (base + 0x008) returns 0 or 1 (only bit 1 visible)
  Writing 0xFF to address (base + 0x008) sets only bit 1 (others unchanged)
  
BOARD-SPECIFIC CONTEXT:
To understand how CPU addresses map to these registers, see:
  board = create_board("tm4c123")
  print(board.memory_access_model.description)
  
This shows that TM4C123 uses TM4C123BitBandedAccessModel, which decodes
addresses to extract bit masks from the address itself.

CONTRAST WITH STM32F4:
STM32F4 uses simple offset-based register selection (address directly
indicates which register). See stm32/gpio.py. That's much simpler
but requires software bit manipulation for atomic operations.
"""

from __future__ import annotations

from simulator.core.gpio_enums import PinLevel, PinMode
from simulator.core.peripheral import BasePeripheral
from simulator.core.register import (
    ReadOnlyRegister,
    RegisterFile,
    SimpleRegister,
    WriteOnlyRegister,
)
from simulator.utils.config_loader import Tm4cGpioConfig


class TM4CMaskedDataRegister(SimpleRegister):
    """Special TM4C feature: masked data access.

    Writing to DATA+4, DATA+8, ..., DATA+0x3FC applies only to selected pins.
    The address itself encodes the mask: address [11:2] becomes the pin mask.

    Example: write to (DATA + 0x0C) -> mask = 0x0C >> 2 = 3 -> affects pins 0,1
    """

    def __init__(self, offset: int, data_mask: int):
        super().__init__(offset, 4, 0)
        self.data_offset = offset
        self._data_mask = data_mask

    def write_masked(self, address: int, value: int) -> None:
        """Write with mask applied from address bits."""
        # Address bits [11:2] become the mask
        diff = address - self.data_offset
        if diff <= 0 or diff > 0x3FC:
            raise ValueError(f"Invalid masked write offset {diff:X}")

        mask = (diff >> 2) & self._data_mask
        current = self.value & self._data_mask
        new_value = (current & ~mask) | (value & mask)
        self.value = new_value

    def read_masked(self, address: int) -> int:
        """Read with mask applied."""
        diff = address - self.data_offset
        if diff < 0 or diff > 0x3FC:
            return 0

        if diff == 0:
            return self.value & self._data_mask

        mask = (diff >> 2) & self._data_mask
        return self.value & mask


class TM4CRawInterruptStatus(ReadOnlyRegister):
    """RIS: raw interrupt flags before masking."""


class TM4CInterruptClear(WriteOnlyRegister):
    """ICR: write 1 to clear interrupt flags."""

    def __init__(self, offset: int, ris_register: TM4CRawInterruptStatus):
        super().__init__(offset, 4, 0)
        self.ris = ris_register

    def write(self, _size: int, val: int) -> None:
        # Clear flags: RIS &= ~ICR_value
        self.ris.value &= ~val


class TM4C123GPIO(BasePeripheral):
    """TM4C123GH6PM GPIO port (8-bit).

    This is a complete, self-contained GPIO implementation specific to TM4C.
    No shared base classes; everything is explicit.

    Key features:
    - 8 pins per port
    - Masked DATA window for atomic single-pin updates
    - Interrupt support (RIS, MIS, ICR)
    - Pin modes (input, output, alternate)
    """

    def __init__(
        self,
        cfg: Tm4cGpioConfig,
        data_mask: int,
        initial_value: int = 0,
        base_addr: int = 0,
        name: str | None = None,
    ):
        super().__init__(
            name=name or "TM4C123GPIO", size=cfg.port_size, base_addr=base_addr
        )
        self.cfg = cfg
        if data_mask <= 0:
            raise ValueError("data_mask must be positive")
        self._data_mask = data_mask
        self._pin_count = data_mask.bit_length()
        self._registers = RegisterFile()

        # Initialize registers
        data_reg = TM4CMaskedDataRegister(cfg.offsets.data, self._data_mask)
        data_reg.value = initial_value & self._data_mask

        ris_reg = TM4CRawInterruptStatus(cfg.offsets.ris, 4, 0)
        icr_reg = TM4CInterruptClear(cfg.offsets.icr, ris_reg)

        dir_reg = SimpleRegister(cfg.offsets.dir, 4, 0)
        den_reg = SimpleRegister(cfg.offsets.den, 4, 0)
        afsel_reg = SimpleRegister(cfg.offsets.afsel, 4, 0)
        is_reg = SimpleRegister(cfg.offsets.is_, 4, 0)
        ibe_reg = SimpleRegister(cfg.offsets.ibe, 4, 0)
        iev_reg = SimpleRegister(cfg.offsets.iev, 4, 0)
        im_reg = SimpleRegister(cfg.offsets.im, 4, 0)

        self._registers.add(data_reg)
        self._registers.add(ris_reg)
        self._registers.add(icr_reg)
        self._registers.add(dir_reg)
        self._registers.add(den_reg)
        self._registers.add(afsel_reg)
        self._registers.add(is_reg)
        self._registers.add(ibe_reg)
        self._registers.add(iev_reg)
        self._registers.add(im_reg)

        self._data_reg = data_reg
        self._ris_reg = ris_reg
        self._icr_reg = icr_reg
        self._dir_reg = dir_reg
        self._den_reg = den_reg
        self._afsel_reg = afsel_reg
        self._is_reg = is_reg
        self._im_reg = im_reg

    def read(self, offset: int, size: int) -> int:
        """Read from a GPIO register."""
        # Handle masked DATA reads
        data_base = self.cfg.offsets.data
        diff = offset - data_base

        if 0 <= diff <= 0x3FC:
            return self._data_reg.read_masked(offset)

        # Masked interrupt status (MIS = RIS & IM)
        if offset == self.cfg.offsets.mis:
            ris = self._registers.read(self.cfg.offsets.ris, 4, 0)
            im = self._registers.read(self.cfg.offsets.im, 4, 0)
            return ris & im

        return self._registers.read(offset, size, default_reset=0)

    def write(self, offset: int, size: int, value: int) -> None:
        """Write to a GPIO register."""
        # Handle masked DATA writes
        data_base = self.cfg.offsets.data
        diff = offset - data_base

        if 0 < diff <= 0x3FC:
            if size != 4:
                raise ValueError("Masked DATA accesses must be 32-bit")
            self._data_reg.write_masked(offset, value)
            return

        if diff == 0:
            # Direct DATA write
            self._registers.write(offset, size, value & self._data_mask)
            return

        # Interrupt clear
        if offset == self.cfg.offsets.icr:
            self._registers.write(offset, size, value)
            return

        # All other registers
        self._registers.write(offset, size, value & self._data_mask)

    def reset(self) -> None:
        """Reset all registers."""
        self._registers.reset()

    # Convenience methods for testing/debugging
    def set_pin(self, pin: int, level: PinLevel) -> None:
        """Set a pin directly (simulate external input)."""
        if not 0 <= pin < self._pin_count:
            raise ValueError(f"Invalid pin {pin}; must be 0-{self._pin_count - 1}")

        current = self._data_reg.value
        if level == PinLevel.HIGH:
            current |= 1 << pin
        else:
            current &= ~(1 << pin)
        self._data_reg.value = current

    def get_pin(self, pin: int) -> PinLevel:
        """Get the state of a pin."""
        if not 0 <= pin < self._pin_count:
            raise ValueError(f"Invalid pin {pin}; must be 0-{self._pin_count - 1}")

        value = self._data_reg.value
        return PinLevel((value >> pin) & 1)

    def get_pin_mode(self, pin: int) -> PinMode:
        """Determine pin mode from DIR and AFSEL."""
        if not 0 <= pin < 8:
            raise ValueError(f"Invalid pin {pin}; must be 0-7")

        dir_val = self._dir_reg.value & self._data_mask
        afsel_val = self._afsel_reg.value & self._data_mask
        bit = 1 << pin

        if dir_val & bit:
            return PinMode.OUTPUT
        if afsel_val & bit:
            return PinMode.ALTERNATE
        return PinMode.INPUT

    def set_pin_mode(self, pin: int, mode: PinMode) -> None:
        """Set pin mode by updating DIR and AFSEL."""
        if not 0 <= pin < self._pin_count:
            raise ValueError(f"Invalid pin {pin}; must be 0-{self._pin_count - 1}")

        dir_val = self._dir_reg.value & self._data_mask
        afsel_val = self._afsel_reg.value & self._data_mask
        bit = 1 << pin

        if mode == PinMode.OUTPUT:
            dir_val |= bit
            afsel_val &= ~bit
        elif mode == PinMode.ALTERNATE:
            dir_val &= ~bit
            afsel_val |= bit
        else:  # INPUT
            dir_val &= ~bit
            afsel_val &= ~bit

        self._dir_reg.value = dir_val
        self._afsel_reg.value = afsel_val
