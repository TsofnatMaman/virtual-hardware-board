"""Tests for STM32 GPIO peripheral implementation."""

import pytest
from simulator.interfaces.gpio_enums import PinLevel, PinMode
from simulator.stm32.gpio import STM32_GPIO
from simulator.utils.config_loader import load_config


# ----------------- Fixtures -----------------

@pytest.fixture
def gpio_config():
    """Load STM32 GPIO configuration."""
    config = load_config("stm32")
    return config.gpio


@pytest.fixture
def gpio(gpio_config):
    """Create an STM32 GPIO peripheral instance."""
    return STM32_GPIO(gpio_config=gpio_config, initial_value=0x0000)


# ----------------- Helpers for interrupt flags -----------------

def set_flag(gpio, pin):
    gpio._interrupt_flags |= (1 << pin)

def clear_flag_bitwise(gpio, pin):
    gpio._interrupt_flags &= ~(1 << pin)

def check_flag(gpio, pin):
    return (gpio._interrupt_flags & (1 << pin)) != 0


# ----------------- Test Classes -----------------

class TestSTM32GPIOInitialization:
    def test_init_with_default_value(self, gpio_config):
        gpio = STM32_GPIO(gpio_config=gpio_config)
        assert gpio.read_register(gpio_config.offsets.data) == 0x0000

    def test_init_with_custom_value(self, gpio_config):
        gpio = STM32_GPIO(gpio_config=gpio_config, initial_value=0xFFFF)
        assert gpio.read_register(gpio_config.offsets.data) == 0xFFFF

    def test_init_all_pins_as_input(self, gpio):
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_init_no_interrupts(self, gpio):
        im_value = gpio.read_register(gpio._gpio_config.offsets.im)
        assert im_value == 0x0000

    def test_stm32_has_16_pins(self, gpio):
        assert gpio.NUM_PINS == 16
        assert gpio.MAX_PIN == 15


class TestSTM32RegisterOperations:
    def test_write_and_read_register(self, gpio):
        offset = gpio._gpio_config.offsets.data
        gpio.write_register(offset, 0xABCD)
        assert gpio.read_register(offset) == 0xABCD

    def test_write_register_masks_to_32bit(self, gpio):
        offset = gpio._gpio_config.offsets.data
        gpio.write_register(offset, 0x1FFFFFFFF)
        assert gpio.read_register(offset) == 0xFFFFFFFF

    def test_read_unwritten_register_returns_initial_value(self, gpio):
        offset = gpio._gpio_config.offsets.dir
        assert gpio.read_register(offset) == 0x0000


class TestSTM32PinModeConfiguration:
    def test_set_pin_mode_output(self, gpio):
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        assert gpio.get_pin_mode(0) == PinMode.OUTPUT

    def test_set_pin_mode_input(self, gpio):
        gpio.set_pin_mode(5, PinMode.INPUT)
        assert gpio.get_pin_mode(5) == PinMode.INPUT

    def test_set_pin_mode_alternate(self, gpio):
        gpio.set_pin_mode(3, PinMode.ALTERNATE)
        assert gpio.get_pin_mode(3) == PinMode.ALTERNATE

    def test_set_pin_mode_invalid_pin_low(self, gpio):
        with pytest.raises(ValueError):
            gpio.set_pin_mode(-1, PinMode.OUTPUT)

    def test_set_pin_mode_invalid_pin_high(self, gpio):
        with pytest.raises(ValueError):
            gpio.set_pin_mode(16, PinMode.OUTPUT)

    def test_get_pin_mode_invalid_pin(self, gpio):
        with pytest.raises(ValueError):
            gpio.get_pin_mode(20)

    def test_stm32_supports_all_16_pins(self, gpio):
        for pin in range(16):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
            assert gpio.get_pin_mode(pin) == PinMode.OUTPUT


class TestSTM32PinValueControl:
    def test_set_pin_high(self, gpio):
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH

    def test_set_pin_low(self, gpio):
        gpio.set_pin_value(0, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_set_multiple_pins(self, gpio):
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(1, PinLevel.LOW)
        gpio.set_pin_value(2, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH
        assert gpio.get_pin_value(1) == PinLevel.LOW
        assert gpio.get_pin_value(2) == PinLevel.HIGH

    def test_set_pin_value_invalid_pin(self, gpio):
        with pytest.raises(ValueError):
            gpio.set_pin_value(20, PinLevel.HIGH)

    def test_get_pin_value_invalid_pin(self, gpio):
        with pytest.raises(ValueError):
            gpio.get_pin_value(20)

    def test_pin_value_persistence(self, gpio):
        gpio.set_pin_value(5, PinLevel.HIGH)
        for _ in range(10):
            assert gpio.get_pin_value(5) == PinLevel.HIGH


class TestSTM32PortStateControl:
    def test_set_port_state_all_high(self, gpio):
        gpio.set_port_state(0xFFFF)
        assert gpio.get_port_state() == 0xFFFF

    def test_set_port_state_all_low(self, gpio):
        gpio.set_port_state(0x0000)
        assert gpio.get_port_state() == 0x0000

    def test_set_port_state_mixed(self, gpio):
        pattern = 0xAAAA
        gpio.set_port_state(pattern)
        assert gpio.get_port_state() == pattern

    def test_set_port_state_masks_to_16bits(self, gpio):
        gpio.set_port_state(0x1FFFF)
        assert gpio.get_port_state() == 0xFFFF

    def test_port_state_individual_consistency(self, gpio):
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(1, PinLevel.LOW)
        gpio.set_pin_value(2, PinLevel.HIGH)
        expected = (1 << 0) | (0 << 1) | (1 << 2)
        assert gpio.get_port_state() == expected


class TestSTM32InterruptConfiguration:
    def test_configure_interrupt_edge_triggered(self, gpio):
        gpio.configure_interrupt(0, edge_triggered=True)
        assert gpio._interrupt_config[0]["edge_triggered"] is True

    def test_configure_interrupt_level_triggered(self, gpio):
        gpio.configure_interrupt(5, edge_triggered=False)
        assert gpio._interrupt_config[5]["edge_triggered"] is False

    def test_clear_interrupt_flag(self, gpio):
        set_flag(gpio, 3)
        gpio.clear_interrupt_flag(3)
        assert not check_flag(gpio, 3)

    def test_masked_interrupt_status(self, gpio):
        set_flag(gpio, 2)
        set_flag(gpio, 5)
        gpio.configure_interrupt(2)
        gpio.configure_interrupt(5)
        mis = gpio.read_register(gpio._gpio_config.offsets.mis)
        assert (mis & (1 << 2)) != 0
        assert (mis & (1 << 5)) != 0

    def test_configure_interrupt_invalid_pin(self, gpio):
        with pytest.raises(ValueError):
            gpio.configure_interrupt(20)

    def test_clear_interrupt_flag_invalid_pin(self, gpio):
        with pytest.raises(ValueError):
            gpio.clear_interrupt_flag(20)


class TestSTM32Reset:
    def test_reset_clears_registers(self, gpio):
        gpio.write_register(gpio._gpio_config.offsets.data, 0xFFFF)
        gpio.reset()
        assert gpio.read_register(gpio._gpio_config.offsets.data) == 0x0000

    def test_reset_restores_pin_modes(self, gpio):
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.ALTERNATE)
        gpio.reset()
        assert gpio.get_pin_mode(0) == PinMode.INPUT
        assert gpio.get_pin_mode(1) == PinMode.INPUT

    def test_reset_clears_interrupts(self, gpio):
        set_flag(gpio, 0)
        set_flag(gpio, 5)
        gpio.reset()
        for pin in range(gpio.NUM_PINS):
            assert not check_flag(gpio, pin)

    def test_reset_clears_interrupt_config(self, gpio):
        gpio.configure_interrupt(3, edge_triggered=True)
        gpio.reset()
        assert gpio._interrupt_config[3]["edge_triggered"] is False


class TestSTM32Integration:
    def test_gpio_direction_and_value_workflow(self, gpio):
        for pin in range(8):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
        for pin in range(8, 16):
            gpio.set_pin_mode(pin, PinMode.INPUT)

        for pin in range(8):
            gpio.set_pin_value(pin, PinLevel.HIGH)

        for pin in range(8):
            assert gpio.get_pin_mode(pin) == PinMode.OUTPUT
            assert gpio.get_pin_value(pin) == PinLevel.HIGH
        for pin in range(8, 16):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_mixed_pin_modes(self, gpio):
        modes = [PinMode.OUTPUT, PinMode.INPUT, PinMode.ALTERNATE]
        for pin in range(min(3, gpio.NUM_PINS)):
            gpio.set_pin_mode(pin, modes[pin % len(modes)])
        for pin in range(min(3, gpio.NUM_PINS)):
            assert gpio.get_pin_mode(pin) == modes[pin % len(modes)]

    def test_port_state_after_reset(self, gpio):
        gpio.set_port_state(0xABCD)
        gpio.reset()
        assert gpio.get_port_state() == 0x0000
