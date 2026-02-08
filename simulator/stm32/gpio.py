"""STM32 GPIO peripheral with direct register offset mapping.

MEMORY ACCESS PATTERN: Direct Register Offset Mapping
======================================================
The STM32F4 uses straightforward offset-based register selection. Each
memory address directly corresponds to a specific hardware register:

  IDR (Input Data)      @ offset 0x10
  ODR (Output Data)     @ offset 0x14
  BSRR (Bit Set/Reset)  @ offset 0x18

Register Behavior:
- IDR is read-only: reflects input pin state (or ODR if not externally driven)
- ODR is read-write: software controls output state
- BSRR is write-only: provides atomic bit-level control without RMW cycles

BOARD-SPECIFIC CONTEXT:
To understand how CPU addresses map to these registers, see:
  board = create_board("stm32f4")
  print(board.memory_access_model.description)
  
This shows that STM32F4 uses STM32F4DirectAccessModel, which maps
addresses directly to registers by offset.

CONTRAST WITH TM4C123:
TM4C123 uses completely different semantics (bit-banded addressing) where
the address itself encodes which bits are accessible. See tm4c/gpio.py.
"""

from __future__ import annotations

from simulator.core.register import (
    ReadOnlyRegister,
    Register,
    RegisterFile,
    SimpleRegister,
    WriteOnlyRegister,
)
from simulator.core.gpio_enums import PinLevel
from simulator.core.peripheral import BasePeripheral
from simulator.utils.config_loader import Stm32GpioConfig
from simulator.utils.consts import ConstUtils
from .consts import (
    GPIO_PORT_BASE_DEFAULT,
    GPIO_DATA_MASK_16BIT,
    REG_IDR,
    REG_ODR,
    REG_BSRR,
)


class STM32OutputDataRegister(SimpleRegister):
    """ODR register: software-controlled output state."""
    pass


class STM32InputDataRegister(ReadOnlyRegister):
    """IDR register: read-only input state.
    
    In real hardware, IDR reflects the actual pin state from external sources.
    In simulation, we allow setting external input via set_pin(), or default to ODR.
    """
    
    def __init__(self, offset: int, odr_register: Register):
        super().__init__(offset, 4, 0)
        self.odr = odr_register
        self._external_inputs = None  # None means "follow ODR", otherwise use this value
    
    def read(self, size: int) -> int:
        # If external inputs are set (simulating external pin state), return those
        # Otherwise, reflect the output state
        if self._external_inputs is not None:
            return self._external_inputs & GPIO_DATA_MASK_16BIT
        return self.odr.read(size)
    
    def set_external_input(self, value: int) -> None:
        """Set external input state (simulates pins being driven externally)."""
        self._external_inputs = value & GPIO_DATA_MASK_16BIT


class STM32BitSetResetRegister(WriteOnlyRegister):
    """BSRR: atomic set/reset register.
    
    Write format: [31:16] = reset bits, [15:0] = set bits.
    Writing to BSRR atomically modifies ODR.
    """
    
    def __init__(self, offset: int, odr_register: Register):
        super().__init__(offset, 4, 0)
        self.odr = odr_register
    
    def write(self, size: int, val: int) -> None:
        if size != 4:
            raise ValueError("BSRR must be accessed as 32-bit word")
        
        set_mask = val & GPIO_DATA_MASK_16BIT
        reset_mask = (val >> 16) & GPIO_DATA_MASK_16BIT
        
        current = self.odr.read(4)
        current |= set_mask
        current &= ~reset_mask
        self.odr.write(4, current & GPIO_DATA_MASK_16BIT)


class STM32GPIO(BasePeripheral):
    """STM32 GPIO port (16-bit).
    
    This is a complete, self-contained GPIO implementation. No inheritance
    tricks, no abstract base classes to confuse the issue.
    
    Registers:
    - MODER, OTYPER, OSPEEDR, PUPDR, etc. (configuration, unimplemented)
    - IDR @ 0x10 (input data, read-only, mirrors ODR)
    - ODR @ 0x14 (output data, read-write)
    - BSRR @ 0x18 (bit set/reset, write-only atomic updates)
    """
    
    def __init__(
        self,
        cfg: Stm32GpioConfig,
        initial_value: int = 0,
        base_addr: int = 0,
        name: str | None = None,
    ):
        super().__init__(name=name or "STM32GPIO", size=0x400, base_addr=base_addr)
        self.cfg = cfg
        self._registers = RegisterFile()
        
        # Create the actual register objects using config offsets
        odr = STM32OutputDataRegister(
            cfg.offsets.odr, 4, initial_value & GPIO_DATA_MASK_16BIT
        )
        idr = STM32InputDataRegister(cfg.offsets.idr, odr)
        bsrr = STM32BitSetResetRegister(cfg.offsets.bsrr, odr)
        
        self._registers.add(odr)
        self._registers.add(idr)
        self._registers.add(bsrr)
        
        self._odr = odr
        self._idr = idr
    
    def read(self, offset: int, size: int) -> int:
        """Read from a GPIO register."""
        return self._registers.read(offset, size, default_reset=0)
    
    def write(self, offset: int, size: int, value: int) -> None:
        """Write to a GPIO register."""
        # BSRR needs the full 32-bit value (bits 31:16 for reset, 15:0 for set)
        if offset == self.cfg.offsets.bsrr:
            self._registers.write(offset, size, value)
        else:
            # Other registers use only lower 16 bits for 16-bit port
            self._registers.write(offset, size, value & GPIO_DATA_MASK_16BIT)
    
    def reset(self) -> None:
        """Reset all registers."""
        self._registers.reset()
    
    # Convenience methods for testing/debugging
    def set_pin(self, pin: int, level: PinLevel) -> None:
        """Set a single pin via IDR (simulating external input)."""
        if not (0 <= pin < 16):
            raise ValueError(f"Invalid pin {pin}; must be 0-15")
        
        # Get current external input state (or start from ODR if none set)
        if self._idr._external_inputs is not None:
            current = self._idr._external_inputs
        else:
            current = self._odr.read(4)
        
        if level == PinLevel.HIGH:
            current |= 1 << pin
        else:
            current &= ~(1 << pin)
        self._idr.set_external_input(current)
    
    def get_pin(self, pin: int) -> PinLevel:
        """Get the state of a pin (output)."""
        if not (0 <= pin < 16):
            raise ValueError(f"Invalid pin {pin}; must be 0-15")
        
        odr_val = self._odr.read(4)
        return PinLevel((odr_val >> pin) & 1)
    
    def get_port_state(self) -> int:
        """Get the entire port state (ODR value)."""
        return self._odr.read(4)

