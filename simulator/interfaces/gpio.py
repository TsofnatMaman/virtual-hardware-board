from abc import abstractmethod

from peripheral import BasePeripherals
from simulator.utils.config_loader import GPIO_Config
from simulator.utils.consts import ConstUtils, PinMode

class BaseGPIO(BasePeripherals):
    NUM_PINS: int
    MAX_PIN: int

    def __init__(self, gpio_config: GPIO_Config, initial_value: int = 0x00):
        self._gpio_config = gpio_config
        self._initial_value = initial_value
        self._registers: dict[int, int] = {}
        self._pin_modes = [PinMode.INPUT] * self.NUM_PINS
        self._interrupt_flags: int = 0
        self._interrupt_config = {i: {"edge_triggered": False} for i in range(self.NUM_PINS)}
        self._registers[self._gpio_config.offsets.data] = initial_value

    @abstractmethod
    def set_port_state(self, value: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_port_state(self) -> int:
        raise NotImplementedError

    def write_register(self, offset: int, value: int) -> None:
        value &= ConstUtils.MASK_32_BITS
        self._registers[offset] = value

    def read_register(self, offset: int) -> int:
        return self._registers.get(offset, self._initial_value)
