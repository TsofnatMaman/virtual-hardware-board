import pytest

from simulator.core.gpio_enums import PinLevel, PinMode
from simulator.tm4c import TM4C123GPIO
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


def test_masked_data_direct_access_and_invalid_size(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask, initial_value=0xAA)
    data_base = gpio_cfg.offsets.data

    # Direct data access (diff == 0)
    assert gpio.read(data_base, 4) == 0xAA

    # Masked writes must be 32-bit
    offset = data_base + (0b00000001 << 2)
    with pytest.raises(ValueError):
        gpio.write(offset, 2, 0xFF)

    # Invalid masked write offset
    with pytest.raises(ValueError):
        gpio._data_reg.write_masked(data_base, 0xFF)

    # Out-of-range read returns 0
    assert gpio._data_reg.read_masked(data_base - 4) == 0


def test_icr_clears_ris(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask)
    gpio._ris_reg.value = 0b00001111
    gpio.write(gpio_cfg.offsets.icr, 4, 0b00000011)
    assert gpio._ris_reg.value == 0b00001100


def test_gpio_reset_and_data_mask_validation(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask, initial_value=0xFF)
    gpio.reset()
    assert gpio.read(gpio_cfg.offsets.data, 4) == 0

    with pytest.raises(ValueError):
        TM4C123GPIO(gpio_cfg, data_mask=0)


def test_invalid_pin_raises(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask)
    with pytest.raises(ValueError):
        gpio.set_pin(32, gpio.get_pin(0))
    with pytest.raises(ValueError):
        gpio.get_pin(32)
    with pytest.raises(ValueError):
        gpio.get_pin_mode(32)
    with pytest.raises(ValueError):
        gpio.set_pin_mode(32, gpio.get_pin_mode(0))


def test_direct_data_write_and_other_register_read(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask)
    data_base = gpio_cfg.offsets.data
    gpio.write(data_base, 4, 0x0F)
    assert gpio.read(data_base, 4) == 0x0F

    # read a non-masked register (DIR)
    assert gpio.read(gpio_cfg.offsets.dir, 4) == 0


def test_set_pin_low_and_set_pin_mode_branches(gpio_cfg_with_mask):
    gpio_cfg, data_mask = gpio_cfg_with_mask
    gpio = TM4C123GPIO(gpio_cfg, data_mask=data_mask)

    gpio.set_pin(0, PinLevel.HIGH)
    gpio.set_pin(0, PinLevel.LOW)
    assert gpio.get_pin(0) == PinLevel.LOW

    gpio.set_pin_mode(0, PinMode.OUTPUT)
    assert gpio.get_pin_mode(0) == PinMode.OUTPUT
    gpio.set_pin_mode(0, PinMode.ALTERNATE)
    assert gpio.get_pin_mode(0) == PinMode.ALTERNATE
    gpio.set_pin_mode(0, PinMode.INPUT)
    assert gpio.get_pin_mode(0) == PinMode.INPUT
