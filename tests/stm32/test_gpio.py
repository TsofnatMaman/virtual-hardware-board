import pytest

from simulator.core.gpio_enums import PinLevel
from simulator.stm32 import STM32GPIO
from simulator.utils.config_loader import load_config


@pytest.fixture
def gpio_cfg_with_mask():
    config_path = "simulator/stm32/config.yaml"
    cfg = load_config("stm32f4", path=config_path)
    data_mask = 0
    for value in cfg.pins.pin_masks.values():
        data_mask |= value
    return cfg.gpio, data_mask


def test_bsrr_sets_and_resets_bits(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0000)
    # Set pin 0 and 2
    gpio.write(gpio_cfg.offsets.bsrr, 4, 0b00000101)
    assert gpio.get_port_state() == 0b00000101
    # Reset pin 2 via upper halfword
    gpio.write(gpio_cfg.offsets.bsrr, 4, 0b00000100 << 16)
    assert gpio.get_port_state() == 0b00000001


def test_odr_write_and_read(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0000)
    gpio.write(gpio_cfg.offsets.odr, 4, 0x00F0)
    assert gpio.read(gpio_cfg.offsets.odr, 4) == 0x00F0


def test_idr_reflects_input_pins(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0000)
    gpio.set_pin(3, PinLevel.HIGH)
    assert gpio.read(gpio_cfg.offsets.idr, 4) & (1 << 3)
