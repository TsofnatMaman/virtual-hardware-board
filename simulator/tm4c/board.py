"""TM4C123GH6PM board: Cortex-M4F, GPIO data register with bit-banded addressing."""

from functools import partial
from pathlib import Path

from simulator.core.configured_board import BoardSpec, ConfiguredBoard

from .gpio import TM4C123GPIO
from .memory_access import TM4C123BitBandedAccessModel

PINS_PER_PORT = 8


class TM4C123Board(ConfiguredBoard):
    """TM4C123GH6PM development board."""

    spec = BoardSpec(
        key="tm4c123",
        name="TM4C123",
        config_path=Path(__file__).parent / "config.yaml",
        gpio_kind="tm4c123",
        gpio_class=TM4C123GPIO,
        access_model=partial(TM4C123BitBandedAccessModel, num_pins=PINS_PER_PORT),
    )
