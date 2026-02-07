from simulator.interfaces.gpio import BaseGPIO
from simulator.utils.consts import ConstUtils

class TM4C123_GPIO(BaseGPIO):
    NUM_PINS = 8
    MAX_PIN = 7

    def write_register(self, offset: int, value: int) -> None:
        if self._gpio_config.offsets.data <= offset <= self._gpio_config.offsets.data + ConstUtils.DATA_MASKED_MAX_OFFSET:
            mask = (offset - self._gpio_config.offsets.data) >> 2
            current = self._registers.get(self._gpio_config.offsets.data, 0)
            self._registers[self._gpio_config.offsets.data] = (current & ~mask) | (value & mask)
            return
        if offset == self._gpio_config.offsets.icr:
            self._interrupt_flags &= ~value
            return
        super().write_register(offset, value)

    def read_register(self, offset: int) -> int:
        if self._gpio_config.offsets.data <= offset <= self._gpio_config.offsets.data + ConstUtils.DATA_MASKED_MAX_OFFSET:
            mask = (offset - self._gpio_config.offsets.data) >> 2
            return self._registers.get(self._gpio_config.offsets.data, 0) & mask
        if offset == self._gpio_config.offsets.ris:
            return self._interrupt_flags & ((1 << self.NUM_PINS) - 1)
        return super().read_register(offset)

    def set_port_state(self, value: int) -> None:
        value &= 0xFF
        self.write_register(self._gpio_config.offsets.data, value)

    def get_port_state(self) -> int:
        return self.read_register(self._gpio_config.offsets.data) & ConstUtils.MASK_8_BITS
