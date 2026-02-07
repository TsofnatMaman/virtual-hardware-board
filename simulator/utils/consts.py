from enum import IntEnum

class ConstUtils:
    MASK_32_BITS = 0xFFFFFFFF
    MASK_8_BITS = 0xFF
    DATA_MASKED_MAX_OFFSET = 0x3FC


class PinMode(IntEnum):
    """GPIO pin mode enumeration."""

    INPUT = 0
    OUTPUT = 1
    INPUT_PULLUP = 2
    INPUT_PULLDOWN = 3
    ALTERNATE = 4

class PinLevel(IntEnum):
    """GPIO pin logic level enumeration."""

    LOW = 0
    HIGH = 1
