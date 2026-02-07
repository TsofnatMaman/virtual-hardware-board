"""Constants and utility values for the simulator."""


class ConstUtils:
    """Bitwise masks and register constants."""

    # Bitwise masks for different data widths
    MASK_8_BITS = 0xFF
    """8-bit mask: 0xFF"""

    MASK_16_BITS = 0xFFFF
    """16-bit mask: 0xFFFF"""

    MASK_32_BITS = 0xFFFFFFFF
    """32-bit mask: 0xFFFFFFFF"""

    # Tiva-C (TM4C123) specific constants
    DATA_MASKED_MAX_OFFSET = 0x3FC
    """Maximum offset for masked DATA register access on Tiva-C (TM4C123).
    
    Tiva-C supports masked read/write operations on the DATA register
    using offsets from 0x000 to 0x3FC for selective bit access.
    """


class RegisterOffsets:
    """Register offset constants for GPIO peripherals.
    
    Note: Offsets may vary between MCU vendors (Tiva-C vs STM32).
    Use MCU-specific configuration (GPIO_Config) for actual offsets.
    """

    pass

