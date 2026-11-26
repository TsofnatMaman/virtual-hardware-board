"""STM32F4 board: Cortex-M4, GPIO registers at direct offsets."""

from pathlib import Path

from simulator.core.configured_board import BoardSpec, ConfiguredBoard

from .gpio import STM32GPIO
from .memory_access import STM32F4DirectAccessModel


class STM32F4Board(ConfiguredBoard):
    """STM32F4 micro board with ARM Cortex-M4."""

    spec = BoardSpec(
        key="stm32f4",
        name="STM32F4",
        config_path=Path(__file__).parent / "config.yaml",
        gpio_kind="stm32",
        gpio_class=STM32GPIO,
        access_model=STM32F4DirectAccessModel,
    )
