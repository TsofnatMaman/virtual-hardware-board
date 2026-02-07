"""Unit tests for TM4C123 GPIO Peripheral class."""

import pytest

from simulator.interfaces.gpio_enums import PinLevel, PinMode
from simulator.tm4c123.gpio import TM4C123GPIO
from simulator.utils.config_loader import load_config


@pytest.fixture
def gpio_config():
    """Load GPIO configuration from config file."""
    config = load_config("tm4c123")
    return config.gpio


@pytest.fixture
def gpio(gpio_config):
    """Create a GPIO peripheral instance."""
    return TM4C123GPIO(gpio_config=gpio_config, initial_value=0x00)


class TestGPIOInitialization:
    """Test GPIO peripheral initialization."""

    def test_init_with_default_value(self, gpio_config):
        """Test initialization with default initial value."""
        gpio = TM4C123GPIO(gpio_config=gpio_config)
        assert gpio.read_register(gpio_config.offsets.data) == 0x00

    def test_init_with_custom_value(self, gpio_config):
        """Test initialization with custom initial value."""
        gpio = TM4C123GPIO(gpio_config=gpio_config, initial_value=0xFF)
        assert gpio.read_register(gpio_config.offsets.data) == 0xFF

    def test_init_all_pins_as_input(self, gpio):
        """Test that all pins start as inputs."""
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_init_no_interrupts(self, gpio, gpio_config):
        """Test that no interrupts are configured initially."""
        raw_status = gpio.read_register(gpio_config.offsets.ris)
        assert raw_status == 0x00


class TestRegisterOperations:
    """Test low-level register read/write operations."""

    def test_write_and_read_register(self, gpio, gpio_config):
        """Test basic register write and read."""
        gpio.write_register(gpio_config.offsets.data, 0xAA)
        assert gpio.read_register(gpio_config.offsets.data) == 0xAA

    def test_write_register_masks_to_32bit(self, gpio, gpio_config):
        """Test that write_register masks values to 32-bit."""
        gpio.write_register(gpio_config.offsets.data, 0x1FFFFFFFF)
        assert gpio.read_register(gpio_config.offsets.data) == 0xFFFFFFFF

    def test_read_unwritten_register_returns_initial_value(self, gpio):
        """Test reading unwritten register returns initial value."""
        assert gpio.read_register(0x999) == gpio._initial_value

    def test_write_data_masked(self, gpio, gpio_config):
        """Test masked write operation."""
        gpio.write_register(gpio_config.offsets.data, 0xFF)
        gpio.write_data_masked(gpio_config.offsets.data, 0xF0, 0x0F)
        # Should replace lower 4 bits with 0xF0 (masked to 0x00)
        assert gpio.read_register(gpio_config.offsets.data) == 0xF0

    def test_read_data_masked(self, gpio, gpio_config):
        """Test masked read operation."""
        gpio.write_register(gpio_config.offsets.data, 0xAB)
        result = gpio.read_data_masked(gpio_config.offsets.data, 0x0F)
        assert result == 0x0B


class TestPinModeConfiguration:
    """Test pin mode configuration."""

    def test_set_pin_mode_output(self, gpio, gpio_config):
        """Test setting pin to output mode."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        assert gpio.get_pin_mode(0) == PinMode.OUTPUT
        # Check GPIODIR register bit is set
        assert gpio.read_register(gpio_config.offsets.dir) & (1 << 0)

    def test_set_pin_mode_input(self, gpio, gpio_config):
        """Test setting pin to input mode."""
        gpio.set_pin_mode(3, PinMode.INPUT)
        assert gpio.get_pin_mode(3) == PinMode.INPUT
        # Check GPIODIR register bit is clear
        assert not (gpio.read_register(gpio_config.offsets.dir) & (1 << 3))

    def test_set_pin_mode_alternate(self, gpio, gpio_config):
        """Test setting pin to alternate function mode."""
        gpio.set_pin_mode(5, PinMode.ALTERNATE)
        assert gpio.get_pin_mode(5) == PinMode.ALTERNATE
        # Check GPIOAFSEL register bit is set
        assert gpio.read_register(gpio_config.offsets.afsel) & (1 << 5)

    def test_set_pin_mode_invalid_pin_low(self, gpio):
        """Test setting mode on invalid pin (too low)."""
        with pytest.raises(ValueError, match="out of range"):
            gpio.set_pin_mode(-1, PinMode.OUTPUT)

    def test_set_pin_mode_invalid_pin_high(self, gpio):
        """Test setting mode on invalid pin (too high)."""
        with pytest.raises(ValueError, match="out of range"):
            gpio.set_pin_mode(8, PinMode.OUTPUT)

    def test_get_pin_mode_invalid_pin(self, gpio):
        """Test getting mode from invalid pin."""
        with pytest.raises(ValueError, match="out of range"):
            gpio.get_pin_mode(10)


class TestPinValueControl:
    """Test individual pin value control."""

    def test_set_pin_high(self, gpio):
        """Test setting a pin to HIGH."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH

    def test_set_pin_low(self, gpio):
        """Test setting a pin to LOW."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(0, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_set_multiple_pins(self, gpio):
        """Test setting multiple pins independently."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(1, PinLevel.HIGH)
        gpio.set_pin_value(2, PinLevel.LOW)

        assert gpio.get_pin_value(0) == PinLevel.HIGH
        assert gpio.get_pin_value(1) == PinLevel.HIGH
        assert gpio.get_pin_value(2) == PinLevel.LOW

    def test_set_pin_value_invalid_pin(self, gpio):
        """Test setting value on invalid pin."""
        with pytest.raises(ValueError, match="out of range"):
            gpio.set_pin_value(9, PinLevel.HIGH)

    def test_get_pin_value_invalid_pin(self, gpio):
        """Test getting value from invalid pin."""
        with pytest.raises(ValueError, match="out of range"):
            gpio.get_pin_value(-1)

    def test_pin_value_persistence(self, gpio):
        """Test that pin value persists after set."""
        gpio.set_pin_value(5, PinLevel.HIGH)
        assert gpio.get_pin_value(5) == PinLevel.HIGH
        assert gpio.get_pin_value(5) == PinLevel.HIGH  # Read again


class TestPortStateControl:
    """Test port-wide state control."""

    def test_set_port_state_all_high(self, gpio):
        """Test setting all pins to HIGH simultaneously."""
        gpio.set_port_state(0xFF)
        assert gpio.get_port_state() == 0xFF

    def test_set_port_state_all_low(self, gpio):
        """Test setting all pins to LOW simultaneously."""
        gpio.set_port_state(0x00)
        assert gpio.get_port_state() == 0x00

    def test_set_port_state_mixed(self, gpio):
        """Test setting mixed port state."""
        gpio.set_port_state(0xAA)  # Alternating HIGH/LOW
        assert gpio.get_port_state() == 0xAA

    def test_set_port_state_masks_to_8bits(self, gpio):
        """Test that port state is masked to 8 bits."""
        gpio.set_port_state(0x1FF)  # More than 8 bits
        assert gpio.get_port_state() == 0xFF

    def test_port_state_individual_consistency(self, gpio):
        """Test that port state is consistent with individual pin reads."""
        gpio.set_port_state(0xC3)  # 11000011 in binary
        assert gpio.get_pin_value(0) == PinLevel.HIGH
        assert gpio.get_pin_value(1) == PinLevel.HIGH
        assert gpio.get_pin_value(2) == PinLevel.LOW
        assert gpio.get_pin_value(7) == PinLevel.HIGH


class TestInterruptConfiguration:
    """Test interrupt configuration."""

    def test_configure_interrupt_edge_triggered(self, gpio, gpio_config):
        """Test configuring edge-triggered interrupt."""
        gpio.configure_interrupt(2, edge_triggered=True)
        # GPIOIS bit should be clear for edge-triggered
        assert not (gpio.read_register(gpio_config.offsets.is_) & (1 << 2))
        # GPIOIM bit should be set
        assert gpio.read_register(gpio_config.offsets.im) & (1 << 2)

    def test_configure_interrupt_level_triggered(self, gpio, gpio_config):
        """Test configuring level-triggered interrupt."""
        gpio.configure_interrupt(3, edge_triggered=False)
        # GPIOIS bit should be set for level-triggered
        assert gpio.read_register(gpio_config.offsets.is_) & (1 << 3)
        # GPIOIM bit should be set
        assert gpio.read_register(gpio_config.offsets.im) & (1 << 3)

    def test_clear_interrupt_flag(self, gpio, gpio_config):
        """Test clearing an interrupt flag."""
        # Set interrupt flag manually
        gpio._interrupt_flags[4] = True
        assert gpio.read_register(gpio_config.offsets.ris) & (1 << 4)

        # Clear the flag
        gpio.clear_interrupt_flag(4)
        assert not (gpio.read_register(gpio_config.offsets.ris) & (1 << 4))

    def test_masked_interrupt_status(self, gpio, gpio_config):
        """Test masked interrupt status register."""
        # Set interrupt flags
        gpio._interrupt_flags[1] = True
        gpio._interrupt_flags[3] = True

        # Enable only pin 1 interrupt
        gpio.write_register(gpio_config.offsets.im, 0x02)

        # Masked status should only show pin 1
        masked_status = gpio.read_register(gpio_config.offsets.mis)
        assert masked_status == 0x02

    def test_configure_interrupt_invalid_pin(self, gpio):
        """Test configuring interrupt on invalid pin."""
        with pytest.raises(ValueError, match="out of range"):
            gpio.configure_interrupt(8)

    def test_clear_interrupt_flag_invalid_pin(self, gpio):
        """Test clearing interrupt flag on invalid pin."""
        with pytest.raises(ValueError, match="out of range"):
            gpio.clear_interrupt_flag(-1)


class TestReset:
    """Test reset functionality."""

    def test_reset_clears_registers(self, gpio, gpio_config):
        """Test that reset clears all register values."""
        gpio.write_register(gpio_config.offsets.data, 0xFF)
        gpio.write_register(gpio_config.offsets.dir, 0xAA)
        gpio.reset()

        assert gpio.read_register(gpio_config.offsets.data) == gpio._initial_value
        assert gpio.read_register(gpio_config.offsets.dir) == 0x00

    def test_reset_restores_pin_modes(self, gpio):
        """Test that reset restores all pins to INPUT mode."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.ALTERNATE)
        gpio.reset()

        assert gpio.get_pin_mode(0) == PinMode.INPUT
        assert gpio.get_pin_mode(1) == PinMode.INPUT

    def test_reset_clears_interrupts(self, gpio, gpio_config):
        """Test that reset clears interrupt flags."""
        gpio._interrupt_flags[3] = True
        gpio.reset()

        assert gpio.read_register(gpio_config.offsets.ris) == 0x00

    def test_reset_clears_interrupt_config(self, gpio):
        """Test that reset clears interrupt configuration."""
        gpio.configure_interrupt(5, edge_triggered=True)
        gpio.reset()

        assert not gpio._interrupt_config[5]["edge_triggered"]


class TestIntegration:
    """Integration tests for complex scenarios."""

    def test_gpio_direction_and_value_workflow(self, gpio):
        """Test typical GPIO workflow."""
        # Configure pin 0 as output
        gpio.set_pin_mode(0, PinMode.OUTPUT)

        # Set pin value
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH

        # Change value
        gpio.set_pin_value(0, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_mixed_pin_modes(self, gpio):
        """Test port with mixed pin modes."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.INPUT)
        gpio.set_pin_mode(2, PinMode.ALTERNATE)
        gpio.set_pin_mode(3, PinMode.INPUT_PULLUP)

        assert gpio.get_pin_mode(0) == PinMode.OUTPUT
        assert gpio.get_pin_mode(1) == PinMode.INPUT
        assert gpio.get_pin_mode(2) == PinMode.ALTERNATE
        assert gpio.get_pin_mode(3) == PinMode.INPUT_PULLUP

    def test_port_state_after_reset(self, gpio):
        """Test that port state is reset properly."""
        gpio.set_port_state(0xFF)
        gpio.reset()
        assert gpio.get_port_state() == 0x00
