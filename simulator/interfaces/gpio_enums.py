"""GPIO enumeration types."""

from enum import IntEnum


class PinMode(IntEnum):
    """GPIO pin mode enumeration.
    
    Defines the operational mode for a GPIO pin, such as input, output,
    or alternative function modes.
    """

    INPUT = 0
    """GPIO pin configured as digital input."""

    OUTPUT = 1
    """GPIO pin configured as digital output."""

    INPUT_PULLUP = 2
    """GPIO pin configured as input with internal pull-up resistor."""

    INPUT_PULLDOWN = 3
    """GPIO pin configured as input with internal pull-down resistor."""

    ALTERNATE = 4
    """GPIO pin configured for alternate function (e.g., SPI, UART)."""


class PinLevel(IntEnum):
    """GPIO pin logic level enumeration.
    
    Represents the digital logic level on a GPIO pin.
    """

    LOW = 0
    """Logic level LOW (0V, digital 0)."""

    HIGH = 1
    """Logic level HIGH (typically 3.3V or 5V, digital 1)."""
