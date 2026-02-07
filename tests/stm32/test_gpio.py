"""Tests for STM32 GPIO peripheral implementation."""

import pytest

from simulator.interfaces.gpio_enums import PinLevel, PinMode
from simulator.stm32.gpio import STM32GPIO
from simulator.utils.config_loader import load_config


@pytest.fixture
def gpio_config():
    """Load STM32 GPIO configuration."""
    config = load_config("stm32")
    return config.gpio


@pytest.fixture
def gpio(gpio_config):
    """Create an STM32 GPIO peripheral instance."""
    return STM32GPIO(gpio_config=gpio_config, initial_value=0x0000)


class TestSTM32GPIOInitialization:
    """Test STM32 GPIO peripheral initialization."""

    def test_init_with_default_value(self, gpio_config):
        """Test initialization with default initial value."""
        gpio = STM32GPIO(gpio_config=gpio_config)
        assert gpio.read_register(gpio_config.offsets.data) == 0x0000

    def test_init_with_custom_value(self, gpio_config):
        """Test initialization with custom initial value."""
        gpio = STM32GPIO(gpio_config=gpio_config, initial_value=0xFFFF)
        assert gpio.read_register(gpio_config.offsets.data) == 0xFFFF

    def test_init_all_pins_as_input(self, gpio):
        """Test that all pins start as inputs."""
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_init_no_interrupts(self, gpio):
        """Test that no interrupts are enabled initially."""
        im_value = gpio.read_register(gpio._gpio_config.offsets.im)
        assert im_value == 0x0000

    def test_stm32_has_16_pins(self, gpio):
        """Test that STM32 GPIO has 16 pins."""
        assert gpio.NUM_PINS == 16
        assert gpio.MAX_PIN == 15


class TestSTM32RegisterOperations:
    """Test STM32 register read/write operations."""

    def test_write_and_read_register(self, gpio):
        """Test writing and reading a register."""
        offset = gpio._gpio_config.offsets.data
        gpio.write_register(offset, 0xABCD)
        assert gpio.read_register(offset) == 0xABCD

    def test_write_register_masks_to_32bit(self, gpio):
        """Test that register writes are masked to 32-bit."""
        offset = gpio._gpio_config.offsets.data
        gpio.write_register(offset, 0x1FFFFFFFF)
        assert gpio.read_register(offset) == 0xFFFFFFFF

    def test_read_unwritten_register_returns_initial_value(self, gpio):
        """Test reading a register that hasn't been written returns initial value."""
        offset = gpio._gpio_config.offsets.dir
        # Only data register has special initial value
        assert gpio.read_register(offset) == 0x0000

    def test_write_data_masked(self, gpio):
        """Test masked register write."""
        offset = gpio._gpio_config.offsets.data
        gpio.write_register(offset, 0x00FF)
        gpio.write_data_masked(offset, 0xFF00, 0xFF00)
        assert gpio.read_register(offset) == 0xFFFF

    def test_read_data_masked(self, gpio):
        """Test masked register read."""
        offset = gpio._gpio_config.offsets.data
        gpio.write_register(offset, 0xABCD)
        assert gpio.read_data_masked(offset, 0x00FF) == 0x00CD


class TestSTM32PinModeConfiguration:
    """Test STM32 GPIO pin mode configuration."""

    def test_set_pin_mode_output(self, gpio):
        """Test setting pin to output mode."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        assert gpio.get_pin_mode(0) == PinMode.OUTPUT

    def test_set_pin_mode_input(self, gpio):
        """Test setting pin to input mode."""
        gpio.set_pin_mode(5, PinMode.INPUT)
        assert gpio.get_pin_mode(5) == PinMode.INPUT

    def test_set_pin_mode_alternate(self, gpio):
        """Test setting pin to alternate function mode."""
        gpio.set_pin_mode(3, PinMode.ALTERNATE)
        assert gpio.get_pin_mode(3) == PinMode.ALTERNATE

    def test_set_pin_mode_invalid_pin_low(self, gpio):
        """Test that setting mode on invalid pin (too low) raises error."""
        with pytest.raises(ValueError):
            gpio.set_pin_mode(-1, PinMode.OUTPUT)

    def test_set_pin_mode_invalid_pin_high(self, gpio):
        """Test that setting mode on invalid pin (too high) raises error."""
        with pytest.raises(ValueError):
            gpio.set_pin_mode(16, PinMode.OUTPUT)

    def test_get_pin_mode_invalid_pin(self, gpio):
        """Test that reading mode from invalid pin raises error."""
        with pytest.raises(ValueError):
            gpio.get_pin_mode(20)

    def test_stm32_supports_all_16_pins(self, gpio):
        """Test that all 16 pins can be configured."""
        for pin in range(16):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
            assert gpio.get_pin_mode(pin) == PinMode.OUTPUT


class TestSTM32PinValueControl:
    """Test STM32 GPIO pin value control."""

    def test_set_pin_high(self, gpio):
        """Test setting a pin high."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH

    def test_set_pin_low(self, gpio):
        """Test setting a pin low."""
        gpio.set_pin_value(0, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_set_multiple_pins(self, gpio):
        """Test setting multiple pins independently."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(1, PinLevel.LOW)
        gpio.set_pin_value(2, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH
        assert gpio.get_pin_value(1) == PinLevel.LOW
        assert gpio.get_pin_value(2) == PinLevel.HIGH

    def test_set_pin_value_invalid_pin(self, gpio):
        """Test that setting value on invalid pin raises error."""
        with pytest.raises(ValueError):
            gpio.set_pin_value(20, PinLevel.HIGH)

    def test_get_pin_value_invalid_pin(self, gpio):
        """Test that reading value from invalid pin raises error."""
        with pytest.raises(ValueError):
            gpio.get_pin_value(20)

    def test_pin_value_persistence(self, gpio):
        """Test that pin values persist across reads."""
        gpio.set_pin_value(5, PinLevel.HIGH)
        for _ in range(10):
            assert gpio.get_pin_value(5) == PinLevel.HIGH


class TestSTM32PortStateControl:
    """Test STM32 GPIO port-wide state control."""

    def test_set_port_state_all_high(self, gpio):
        """Test setting entire port to all high."""
        gpio.set_port_state(0xFFFF)
        assert gpio.get_port_state() == 0xFFFF

    def test_set_port_state_all_low(self, gpio):
        """Test setting entire port to all low."""
        gpio.set_port_state(0x0000)
        assert gpio.get_port_state() == 0x0000

    def test_set_port_state_mixed(self, gpio):
        """Test setting port to mixed pattern."""
        pattern = 0xAAAA  # Alternating 1010...
        gpio.set_port_state(pattern)
        assert gpio.get_port_state() == pattern

    def test_set_port_state_masks_to_16bits(self, gpio):
        """Test that port state is masked to 16 bits for STM32."""
        gpio.set_port_state(0x1FFFF)
        assert gpio.get_port_state() == 0xFFFF

    def test_port_state_individual_consistency(self, gpio):
        """Test that port state matches individual pin states."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(1, PinLevel.LOW)
        gpio.set_pin_value(2, PinLevel.HIGH)
        expected = (1 << 0) | (0 << 1) | (1 << 2)
        assert gpio.get_port_state() == expected


class TestSTM32InterruptConfiguration:
    """Test STM32 interrupt/EXTI configuration."""

    def test_configure_interrupt_edge_triggered(self, gpio):
        """Test configuring edge-triggered interrupt."""
        gpio.configure_interrupt(0, edge_triggered=True)
        assert gpio._interrupt_config[0]["edge_triggered"] is True

    def test_configure_interrupt_level_triggered(self, gpio):
        """Test configuring level-triggered interrupt."""
        gpio.configure_interrupt(5, edge_triggered=False)
        assert gpio._interrupt_config[5]["edge_triggered"] is False

    def test_clear_interrupt_flag(self, gpio):
        """Test clearing interrupt flag."""
        gpio._interrupt_flags[3] = True
        gpio.clear_interrupt_flag(3)
        assert gpio._interrupt_flags[3] is False

    def test_masked_interrupt_status(self, gpio):
        """Test masked interrupt status register."""
        gpio._interrupt_flags[2] = True
        gpio._interrupt_flags[5] = True
        gpio.configure_interrupt(2)
        gpio.configure_interrupt(5)
        mis = gpio.read_register(gpio._gpio_config.offsets.mis)
        assert (mis & (1 << 2)) != 0
        assert (mis & (1 << 5)) != 0

    def test_configure_interrupt_invalid_pin(self, gpio):
        """Test configuring interrupt on invalid pin raises error."""
        with pytest.raises(ValueError):
            gpio.configure_interrupt(20)

    def test_clear_interrupt_flag_invalid_pin(self, gpio):
        """Test clearing interrupt flag on invalid pin raises error."""
        with pytest.raises(ValueError):
            gpio.clear_interrupt_flag(20)


class TestSTM32Reset:
    """Test STM32 GPIO reset functionality."""

    def test_reset_clears_registers(self, gpio):
        """Test that reset clears all registers."""
        gpio.write_register(gpio._gpio_config.offsets.data, 0xFFFF)
        gpio.reset()
        assert gpio.read_register(gpio._gpio_config.offsets.data) == 0x0000

    def test_reset_restores_pin_modes(self, gpio):
        """Test that reset restores all pins to input mode."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.ALTERNATE)
        gpio.reset()
        assert gpio.get_pin_mode(0) == PinMode.INPUT
        assert gpio.get_pin_mode(1) == PinMode.INPUT

    def test_reset_clears_interrupts(self, gpio):
        """Test that reset clears all interrupt flags."""
        gpio._interrupt_flags[0] = True
        gpio._interrupt_flags[5] = True
        gpio.reset()
        for flag in gpio._interrupt_flags:
            assert flag is False

    def test_reset_clears_interrupt_config(self, gpio):
        """Test that reset clears interrupt configuration."""
        gpio.configure_interrupt(3, edge_triggered=True)
        gpio.reset()
        assert gpio._interrupt_config[3]["edge_triggered"] is False


class TestSTM32Integration:
    """Integration tests for STM32 GPIO functionality."""

    def test_gpio_direction_and_value_workflow(self, gpio):
        """Test typical GPIO direction and value workflow."""
        # Set pins 0-7 as output, 8-15 as input
        for pin in range(8):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
        for pin in range(8, 16):
            gpio.set_pin_mode(pin, PinMode.INPUT)

        # Set output pins
        for pin in range(8):
            gpio.set_pin_value(pin, PinLevel.HIGH)

        # Verify
        for pin in range(8):
            assert gpio.get_pin_mode(pin) == PinMode.OUTPUT
            assert gpio.get_pin_value(pin) == PinLevel.HIGH
        for pin in range(8, 16):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_mixed_pin_modes(self, gpio):
        """Test mixed pin modes in same port."""
        modes = [PinMode.OUTPUT, PinMode.INPUT, PinMode.ALTERNATE]
        for pin in range(min(3, gpio.NUM_PINS)):
            gpio.set_pin_mode(pin, modes[pin % len(modes)])

        for pin in range(min(3, gpio.NUM_PINS)):
            assert gpio.get_pin_mode(pin) == modes[pin % len(modes)]

    def test_port_state_after_reset(self, gpio):
        """Test port state after reset."""
        gpio.set_port_state(0xABCD)
        gpio.reset()
        assert gpio.get_port_state() == 0x0000
