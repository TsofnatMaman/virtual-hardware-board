"""TM4C123 GPIO peripheral implementation."""

from typing import override

from simulator.interfaces.peripheral import BasePeripherals


class Peripheral(BasePeripherals):
    """GPIO peripheral for TM4C123."""

    @override
    def reset(self) -> None:
        """Reset peripheral to power-on state."""
