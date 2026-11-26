"""STM32C031 board: Cortex-M0+, the STM32 family's GPIO and register model."""

from pathlib import Path

from simulator.core.configured_board import BoardSpec, ConfiguredBoard
from simulator.stm32.gpio import STM32GPIO
from simulator.stm32.memory_access import STM32F4DirectAccessModel


class STM32C031Board(ConfiguredBoard):
    """STM32C031 micro board with ARM Cortex-M0+."""

    spec = BoardSpec(
        key="stm32c031",
        name="STM32C031",
        config_path=Path(__file__).parent / "config.yaml",
        gpio_kind="stm32",
        gpio_class=STM32GPIO,
        access_model=STM32F4DirectAccessModel,
    )
