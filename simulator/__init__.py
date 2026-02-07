"""
Virtual Hardware Board Simulator package.

This package provides simulation capabilities for microcontroller boards including:
- TM4C123 (Texas Instruments Tiva C Series) - 8-pin GPIO
- STM32 (STMicroelectronics ARM Cortex-M) - 16-pin GPIO

Architecture:
- BaseGPIO: GPIO interface + common register and pin operations
  ├─ TM4C123GPIO: 8-pin device-specific implementation
  └─ STM32GPIO: 16-pin device-specific implementation
"""

from simulator.stm32.gpio import STM32_GPIO
from simulator.tm4c123.gpio import TM4C123_GPIO

__all__ = ["TM4C123GPIO", "STM32GPIO"]

