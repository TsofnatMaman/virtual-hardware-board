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


def test_gpio_reset_and_data_mask_validation(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    initial = 0x00FF
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=initial)
    gpio.reset()
    assert gpio.get_port_state() == initial

    with pytest.raises(ValueError):
        STM32GPIO(gpio_cfg, data_mask=0)


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

    # second set_pin should use external inputs branch
    gpio.set_pin(3, PinLevel.LOW)
    assert gpio.read(gpio_cfg.offsets.idr, 4) & (1 << 3) == 0


def test_idr_defaults_to_odr_when_no_external_inputs(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0000)
    gpio.write(gpio_cfg.offsets.odr, 4, 0x00F0)
    assert gpio.read(gpio_cfg.offsets.idr, 4) == 0x00F0


def test_bsrr_requires_word_access(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0000)
    with pytest.raises(ValueError):
        gpio.write(gpio_cfg.offsets.bsrr, 2, 0xFFFF)


def test_invalid_pin_raises(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0000)
    with pytest.raises(ValueError):
        gpio.set_pin(32, PinLevel.HIGH)
    with pytest.raises(ValueError):
        gpio.get_pin(32)


def test_get_pin_valid(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0001)
    assert gpio.get_pin(0) == PinLevel.HIGH


def test_get_port_state_returns_odr(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = STM32GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x0000)
    gpio.write(gpio_cfg.offsets.odr, 4, 0x00AA)
    assert gpio.get_port_state() == 0x00AA
