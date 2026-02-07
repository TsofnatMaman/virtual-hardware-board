"""Unit tests for TM4C123 GPIO Peripheral class (fixed interrupt flags)."""

import pytest
from simulator.interfaces.gpio_enums import PinLevel, PinMode
from simulator.tm4c123.gpio import TM4C123_GPIO
from simulator.utils.config_loader import load_config


@pytest.fixture
def gpio_config():
    config = load_config("tm4c123")
    return config.gpio


@pytest.fixture
def gpio(gpio_config):
    return TM4C123_GPIO(gpio_config=gpio_config, initial_value=0x00)


# Helper functions to manipulate interrupt flags as bitfield
def set_flag(gpio, pin):
    gpio._interrupt_flags |= (1 << pin)

def clear_flag(gpio, pin):
    gpio._interrupt_flags &= ~(1 << pin)

def check_flag(gpio, pin):
    return (gpio._interrupt_flags & (1 << pin)) != 0


class TestGPIOInitialization:

    def test_init_with_default_value(self, gpio_config):
        gpio = TM4C123_GPIO(gpio_config=gpio_config)
        assert gpio.read_register(gpio_config.offsets.data) == 0x00

    def test_init_with_custom_value(self, gpio_config):
        gpio = TM4C123_GPIO(gpio_config=gpio_config, initial_value=0xFF)
        assert gpio.read_register(gpio_config.offsets.data) == 0xFF

    def test_init_all_pins_as_input(self, gpio):
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_init_no_interrupts(self, gpio, gpio_config):
        assert gpio.read_register(gpio_config.offsets.ris) == 0x00


class TestRegisterOperations:

    def test_write_and_read_register(self, gpio, gpio_config):
        gpio.write_register(gpio_config.offsets.data, 0xAA)
        assert gpio.read_register(gpio_config.offsets.data) == 0xAA

    def test_write_register_masks_to_32bit(self, gpio, gpio_config):
        gpio.write_register(gpio_config.offsets.data, 0x1FFFFFFFF)
        assert gpio.read_register(gpio_config.offsets.data) == 0xFFFFFFFF

    def test_read_unwritten_register_returns_initial_value(self, gpio):
        assert gpio.read_register(0x999) == gpio._initial_value


class TestPinModeConfiguration:

    def test_set_pin_mode_output(self, gpio, gpio_config):
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        assert gpio.get_pin_mode(0) == PinMode.OUTPUT
        assert gpio.read_register(gpio_config.offsets.dir) & (1 << 0)

    def test_set_pin_mode_input(self, gpio, gpio_config):
        gpio.set_pin_mode(3, PinMode.INPUT)
        assert gpio.get_pin_mode(3) == PinMode.INPUT
        assert not (gpio.read_register(gpio_config.offsets.dir) & (1 << 3))

    def test_set_pin_mode_alternate(self, gpio, gpio_config):
        gpio.set_pin_mode(5, PinMode.ALTERNATE)
        assert gpio.get_pin_mode(5) == PinMode.ALTERNATE
        assert gpio.read_register(gpio_config.offsets.afsel) & (1 << 5)

    def test_set_pin_mode_invalid_pin_low(self, gpio):
        with pytest.raises(ValueError, match="out of range"):
            gpio.set_pin_mode(-1, PinMode.OUTPUT)

    def test_set_pin_mode_invalid_pin_high(self, gpio):
        with pytest.raises(ValueError, match="out of range"):
            gpio.set_pin_mode(8, PinMode.OUTPUT)

    def test_get_pin_mode_invalid_pin(self, gpio):
        with pytest.raises(ValueError, match="out of range"):
            gpio.get_pin_mode(10)


class TestPinValueControl:

    def test_set_pin_high(self, gpio):
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH

    def test_set_pin_low(self, gpio):
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(0, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_set_multiple_pins(self, gpio):
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(1, PinLevel.HIGH)
        gpio.set_pin_value(2, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.HIGH
        assert gpio.get_pin_value(1) == PinLevel.HIGH
        assert gpio.get_pin_value(2) == PinLevel.LOW

    def test_set_pin_value_invalid_pin(self, gpio):
        with pytest.raises(ValueError, match="out of range"):
            gpio.set_pin_value(9, PinLevel.HIGH)

    def test_get_pin_value_invalid_pin(self, gpio):
        with pytest.raises(ValueError, match="out of range"):
            gpio.get_pin_value(-1)

    def test_pin_value_persistence(self, gpio):
        gpio.set_pin_value(5, PinLevel.HIGH)
        assert gpio.get_pin_value(5) == PinLevel.HIGH
        assert gpio.get_pin_value(5) == PinLevel.HIGH


class TestPortStateControl:

    def test_set_port_state_all_high(self, gpio):
        gpio.set_port_state(0xFF)
        assert gpio.get_port_state() == 0xFF

    def test_set_port_state_all_low(self, gpio):
        gpio.set_port_state(0x00)
        assert gpio.get_port_state() == 0x00

    def test_set_port_state_mixed(self, gpio):
        gpio.set_port_state(0xAA)
        assert gpio.get_port_state() == 0xAA

    def test_set_port_state_masks_to_8bits(self, gpio):
        gpio.set_port_state(0x1FF)
        assert gpio.get_port_state() == 0xFF

    def test_port_state_individual_consistency(self, gpio):
        gpio.set_port_state(0xC3)
        assert gpio.get_pin_value(0) == PinLevel.HIGH
        assert gpio.get_pin_value(1) == PinLevel.HIGH
        assert gpio.get_pin_value(2) == PinLevel.LOW
        assert gpio.get_pin_value(7) == PinLevel.HIGH


class TestInterruptConfiguration:

    def test_configure_interrupt_edge_triggered(self, gpio, gpio_config):
        gpio.configure_interrupt(2, edge_triggered=True)
        assert not (gpio.read_register(gpio_config.offsets.is_) & (1 << 2))
        assert gpio.read_register(gpio_config.offsets.im) & (1 << 2)

    def test_configure_interrupt_level_triggered(self, gpio, gpio_config):
        gpio.configure_interrupt(3, edge_triggered=False)
        assert gpio.read_register(gpio_config.offsets.is_) & (1 << 3)
        assert gpio.read_register(gpio_config.offsets.im) & (1 << 3)

    def test_clear_interrupt_flag(self, gpio, gpio_config):
        set_flag(gpio, 4)
        assert check_flag(gpio, 4)
        gpio.clear_interrupt_flag(4)
        assert not check_flag(gpio, 4)

    def test_masked_interrupt_status(self, gpio, gpio_config):
        set_flag(gpio, 1)
        set_flag(gpio, 3)
        gpio.write_register(gpio_config.offsets.im, 0x02)
        masked_status = gpio.read_register(gpio_config.offsets.mis)
        assert masked_status == 0x02

    def test_configure_interrupt_invalid_pin(self, gpio):
        with pytest.raises(ValueError, match="out of range"):
            gpio.configure_interrupt(8)

    def test_clear_interrupt_flag_invalid_pin(self, gpio):
        with pytest.raises(ValueError, match="out of range"):
            gpio.clear_interrupt_flag(-1)


class TestReset:

    def test_reset_clears_registers(self, gpio, gpio_config):
        gpio.write_register(gpio_config.offsets.data, 0xFF)
        gpio.write_register(gpio_config.offsets.dir, 0xAA)
        gpio.reset()
        assert gpio.read_register(gpio_config.offsets.data) == gpio._initial_value
        assert gpio.read_register(gpio_config.offsets.dir) == 0x00

    def test_reset_restores_pin_modes(self, gpio):
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.ALTERNATE)
        gpio.reset()
        assert gpio.get_pin_mode(0) == PinMode.INPUT
        assert gpio.get_pin_mode(1) == PinMode.INPUT

    def test_reset_clears_interrupts(self, gpio, gpio_config):
        set_flag(gpio, 3)
        gpio.reset()
        assert gpio.read_register(gpio_config.offsets.ris) == 0x00

    def test_reset_clears_interrupt_config(self, gpio):
        gpio.configure_interrupt(5, edge_triggered=True)
        gpio.reset()
        assert not gpio._interrupt_config[5]["edge_triggered"]


class TestIntegration:

    def test_gpio_direction_and_value_workflow(self, gpio):
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH
        gpio.set_pin_value(0, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_mixed_pin_modes(self, gpio):
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.INPUT)
        gpio.set_pin_mode(2, PinMode.ALTERNATE)
        gpio.set_pin_mode(3, PinMode.INPUT_PULLUP)
        assert gpio.get_pin_mode(0) == PinMode.OUTPUT
        assert gpio.get_pin_mode(1) == PinMode.INPUT
        assert gpio.get_pin_mode(2) == PinMode.ALTERNATE
        assert gpio.get_pin_mode(3) == PinMode.INPUT_PULLUP

    def test_port_state_after_reset(self, gpio):
        gpio.set_port_state(0xFF)
        gpio.reset()
        assert gpio.get_port_state() == 0x00
