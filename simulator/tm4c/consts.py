"""TM4C vendor-level constants (Texas Instruments Tiva C series).

Configuration for TM4C microcontroller variants.
Includes TM4C123GH6PM variant-specific constants (merged from variant subdirectory).
"""

# ============================================================================
# TM4C123GH6PM variant-specific constants (merged from tm4c123gh6pm/consts.py)
# ============================================================================

# GPIO Base Addresses (ARM Cortex-M4F, TM4C123GH6PM)
# Each port (A-F) has a dedicated base address
GPIO_PORT_BASE_ADDRESSES = {
    "A": 0x40004000,
    "B": 0x40005000,
    "C": 0x40006000,
    "D": 0x40007000,
    "E": 0x40024000,
    "F": 0x40025000,
}

GPIO_PORT_BASE_DEFAULT = GPIO_PORT_BASE_ADDRESSES["A"]
"""Default GPIO port base address (GPIOA) when none specified."""

# PIN configuration
GPIO_PINS_PER_PORT = 8
"""TM4C123 has 8 pins per GPIO port (PA0-PA7)."""

GPIO_PIN_MASK_ALL = 0xFF
"""Mask for all 8 pins."""

# Register offsets (explicit variant access)
REG_DATA_MASKED_BASE = 0x000
REG_DATA_MASKED_MAX = 0x3FC

REG_DIR = 0x400
REG_IS = 0x404
REG_IBE = 0x408
REG_IEV = 0x40C
REG_IM = 0x410
REG_RIS = 0x414
REG_MIS = 0x418
REG_ICR = 0x41C
REG_AFSEL = 0x420
REG_DEN = 0x500

# Interrupt configuration
IS_EDGE_TRIGGERED = 0x00
"""Interrupt Sense: 0 = edge-triggered"""
IS_LEVEL_TRIGGERED = 0x01
"""Interrupt Sense: 1 = level-triggered"""

IBE_SINGLE_EDGE = 0x00
"""Interrupt Both Edges: 0 = single edge"""
IBE_BOTH_EDGES = 0x01
"""Interrupt Both Edges: 1 = both edges"""

IEV_FALLING_EDGE = 0x00
"""Interrupt Event: 0 = falling edge / low level"""
IEV_RISING_EDGE = 0x01
"""Interrupt Event: 1 = rising edge / high level"""

# ============================================================================
# Common TM4C configuration
# ============================================================================

# Memory Access
GPIO_PORT_SIZE_TM4C = 0x1000
"""TM4C GPIO port occupies 0x1000 bytes in memory."""

GPIO_PORT_ADDRESS_RANGE_SIZE = 0x600
"""Valid address range within a TM4C GPIO port: 0x000-0x5FF."""

GPIO_DATA_PORT_WIDTH = 8
"""TM4C GPIO data ports are 8-bit (8 pins per port)."""

GPIO_DATA_MASK_8BIT = 0xFF
"""8-bit mask for GPIO data register access."""

# Bit-banded addressing - masked DATA window
# TM4C uses address encoding for atomic bit access
BITBAND_DATA_WINDOW_MAX = 0x3FC
"""Maximum offset for masked DATA window access."""

BITBAND_DATA_WINDOW_SIZE = 0x400
"""Size of the masked DATA window (0x000-0x3FC)."""

BITBAND_ADDRESS_SHIFT = 2
"""Right shift for address to bit-number conversion: bit = (offset >> 2) & mask."""

# Register offset names (common across TM4C family)
REGISTER_OFFSETS = {
    # Masked DATA window (0x000-0x3FC) - address encodes bit mask
    # Not a single offset, handled specially
    
    # Control registers
    0x400: "DIR",      # Direction register
    0x404: "IS",       # Interrupt Sense register
    0x408: "IBE",      # Interrupt Both Edges register
    0x40C: "IEV",      # Interrupt Event register
    0x410: "IM",       # Interrupt Mask register
    0x414: "RIS",      # Raw Interrupt Status register
    0x418: "MIS",      # Masked Interrupt Status register (read-only)
    0x41C: "ICR",      # Interrupt Clear register (write-only)
    0x420: "AFSEL",    # Alternate Function Select register
    0x500: "DEN",      # Digital Enable register
}

# Pin modes (GPIO_MODE)
MODE_INPUT = 0x00
MODE_OUTPUT = 0x01
MODE_ALTERNATE = 0x02
