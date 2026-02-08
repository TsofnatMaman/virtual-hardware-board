"""STM32 vendor-level constants.

Common configuration shared across all STM32 variants.
"""

# SCU Architecture
GPIO_PORT_SIZE_STM32 = 0x400
"""STM32 GPIO port occupies 0x400 bytes in memory."""

GPIO_REGISTER_OFFSET_MASK = 0xFF
"""Mask to extract register offset within a GPIO port."""

GPIO_DATA_PORT_WIDTH = 16
"""STM32 GPIO data ports are 16-bit (16 pins per port: PA0-PA15)."""

GPIO_DATA_MASK_16BIT = 0xFFFF
"""16-bit mask for GPIO data register access."""

# Register offset names (common across STM32 family)
REGISTER_OFFSETS = {
    0x00: "MODER",    # Mode register
    0x04: "OTYPER",   # Output type register  
    0x08: "OSPEEDR",  # Output speed register
    0x0C: "PUPDR",    # Pull-up/Pull-down register
    0x10: "IDR",      # Input data register
    0x14: "ODR",      # Output data register
    0x18: "BSRR",     # Bit set/reset register
    0x1C: "LCKR",     # Lock register
    0x20: "AFRL",     # Alternate function register low
    0x24: "AFRH",     # Alternate function register high
}

# BSRR register structure
BSRR_SET_BITS_SHIFT = 0
"""BSRR bits [15:0] - set bits (write 1 to set corresponding ODR bit)."""
BSRR_RESET_BITS_SHIFT = 16
"""BSRR bits [31:16] - reset bits (write 1 to clear corresponding ODR bit)."""

# ============================================================================
# STM32F4 variant-specific constants (merged from f4/consts.py)
# ============================================================================

# GPIO Base Addresses (ARM Cortex-M4F, STM32F407xx)
# Each port (A-H) has a dedicated base address
GPIO_PORT_BASE_ADDRESSES = {
    "A": 0x40020000,
    "B": 0x40020400,
    "C": 0x40020800,
    "D": 0x40020C00,
    "E": 0x40021000,
    "F": 0x40021400,
    "G": 0x40021800,
    "H": 0x40021C00,
}

GPIO_PORT_BASE_DEFAULT = GPIO_PORT_BASE_ADDRESSES["A"]
"""Default GPIO port base address (GPIOA) when none specified."""

# Memory address ranges
GPIO_PORT_ADDRESS_RANGE_SIZE = 0x100
"""Each GPIO port spans 0x100 bytes (0x00-0xFF)."""

# Register offsets for STM32F4
REG_MODER = 0x00
REG_OTYPER = 0x04
REG_OSPEEDR = 0x08
REG_PUPDR = 0x0C
REG_IDR = 0x10
REG_ODR = 0x14
REG_BSRR = 0x18
REG_LCKR = 0x1C
REG_AFRL = 0x20
REG_AFRH = 0x24

# Pin configuration
GPIO_PINS_PER_PORT = 16
"""STM32F4 has 16 pins per GPIO port (PA0-PA15)."""

GPIO_PIN_MASK_ALL = 0xFFFF
"""Mask for all 16 pins."""

# Input/Output modes (for MODE register)
MODE_INPUT = 0x00
MODE_OUTPUT = 0x01
MODE_ALTERNATE = 0x02
MODE_ANALOG = 0x03

# Output types (for OTYPER register)
OTYPE_PUSH_PULL = 0x00
OTYPE_OPEN_DRAIN = 0x01

# Pull-up / Pull-down (for PUPDR register)
PUPD_NONE = 0x00
PUPD_PULLUP = 0x01
PUPD_PULLDOWN = 0x02
