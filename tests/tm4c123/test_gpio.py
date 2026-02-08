import pytest

from simulator.tm4c import TM4C123GPIO
from simulator.core.gpio_enums import PinMode
from simulator.utils.config_loader import load_config


@pytest.fixture
def gpio_cfg_with_mask():
    config_path = "simulator/tm4c/config.yaml"
    cfg = load_config("tm4c123", path=config_path)
    data_mask = 0
    for value in cfg.pins.pin_masks.values():
        data_mask |= value
    return cfg.gpio, data_mask


def test_masked_data_write_and_read(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask, initial_value=0x00)
    data_base = gpio_cfg.offsets.data
    # Mask bit 1 (offset = data + (mask<<2))
    offset = data_base + (0b00000010 << 2)
    gpio.write(offset, 4, 0xFF)  # should only affect bit1
    assert gpio.read(data_base, 4) == 0b10
    # Reading masked returns only masked bits
    assert gpio.read(offset, 4) == 0b10


def test_dir_and_afsel_update_pin_modes(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask)
    gpio.write(gpio_cfg.offsets.dir, 4, 0b00000001)  # pin0 output
    assert gpio.get_pin_mode(0) == PinMode.OUTPUT
    # Set alternate on pin1
    gpio.write(gpio_cfg.offsets.afsel, 4, 0b00000010)
    assert gpio.get_pin_mode(1) == PinMode.ALTERNATE
    # clear alt and dir -> back to input
    gpio.write(gpio_cfg.offsets.afsel, 4, 0)
    gpio.write(gpio_cfg.offsets.dir, 4, 0)
    assert gpio.get_pin_mode(1) == PinMode.INPUT


def test_interrupt_masking(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask)
    gpio._ris_reg.value = 0b00001111  # Set raw interrupt flags
    gpio.write(gpio_cfg.offsets.im, 4, 0b00000101)  # Set interrupt mask
    assert gpio.read(gpio_cfg.offsets.mis, 4) == 0b00000101  # Masked = RIS & IM
