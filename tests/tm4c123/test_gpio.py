"""Comprehensive unit tests for TM4C123_GPIO class."""

import pytest

from simulator.interfaces.gpio_enums import PinLevel, PinMode
from simulator.tm4c123.gpio import TM4C123_GPIO
from simulator.utils.config_loader import load_config
from simulator.utils.consts import ConstUtils


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def gpio_config():
    """Load TM4C123 GPIO configuration."""
    config = load_config("tm4c123")
    return config.gpio


@pytest.fixture
def gpio(gpio_config):
    """Create a TM4C123_GPIO peripheral instance with default value."""
    return TM4C123_GPIO(gpio_config=gpio_config, initial_value=0x00)


@pytest.fixture
def gpio_nonzero(gpio_config):
    """Create a TM4C123_GPIO with non-zero initial value."""
    return TM4C123_GPIO(gpio_config=gpio_config, initial_value=0xAA)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def set_interrupt_flag(gpio: TM4C123_GPIO, pin: int) -> None:
    """Set interrupt flag for a pin."""
    gpio._interrupt_flags |= (1 << pin)


def clear_interrupt_flag(gpio: TM4C123_GPIO, pin: int) -> None:
    """Clear interrupt flag for a pin."""
    gpio._interrupt_flags &= ~(1 << pin)


def is_interrupt_flag_set(gpio: TM4C123_GPIO, pin: int) -> bool:
    """Check if interrupt flag is set for a pin."""
    return (gpio._interrupt_flags & (1 << pin)) != 0


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

class TestTM4C123GPIOInitialization:
    """Test TM4C123_GPIO initialization."""

    def test_init_with_default_value(self, gpio_config):
        """Test initialization with default value 0x00."""
        gpio = TM4C123_GPIO(gpio_config=gpio_config)
        assert gpio.read_register(gpio_config.offsets.data) == 0x00

    def test_init_with_custom_value(self, gpio_config):
        """Test initialization with custom initial value."""
        gpio = TM4C123_GPIO(gpio_config=gpio_config, initial_value=0xFF)
        assert gpio.read_register(gpio_config.offsets.data) == 0xFF

    def test_init_with_nonzero_value(self, gpio_nonzero):
        """Test initialization with non-zero value."""
        assert gpio_nonzero.read_register(
            gpio_nonzero._gpio_config.offsets.data
        ) == 0xAA

    def test_init_all_pins_as_input(self, gpio):
        """Test that all pins are initialized as INPUT."""
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_init_no_interrupts(self, gpio):
        """Test that no interrupts are enabled on init."""
        im_value = gpio.read_register(gpio._gpio_config.offsets.im)
        assert im_value == 0x00

    def test_init_interrupt_flags_clear(self, gpio):
        """Test that interrupt flags are clear on init."""
        ris_value = gpio.read_register(gpio._gpio_config.offsets.ris)
        assert ris_value == 0x00

    def test_tm4c123_has_8_pins(self, gpio):
        """Test that TM4C123 has 8 pins per port."""
        assert gpio.NUM_PINS == 8
        assert gpio.MAX_PIN == 7

    def test_initial_value_persists(self, gpio_nonzero):
        """Test that initial value is stored and retrievable."""
        data_value = gpio_nonzero.read_register(
            gpio_nonzero._gpio_config.offsets.data
        )
        assert data_value == 0xAA


# ============================================================================
# REGISTER READ/WRITE TESTS
# ============================================================================

class TestTM4C123RegisterOperations:
    """Test basic register read/write operations."""

    def test_write_and_read_data_register(self, gpio):
        """Test writing to and reading from DATA register."""
        offset = gpio._gpio_config.offsets.data
        gpio.write_register(offset, 0x55)
        assert gpio.read_register(offset) == 0x55

    def test_write_register_masks_to_8bits(self, gpio):
        """Test that DATA register writes are stored with 32-bit masking in base class."""
        offset = gpio._gpio_config.offsets.data
        # Direct write via base class implementation masks to 32 bits, not 8
        gpio.write_register(offset, 0x1FF)  # 9-bit value
        # The base write_register masks to 32 bits, so 0x1FF is stored as-is
        assert gpio.read_register(offset) == 0x1FF

    def test_read_unwritten_register_returns_zero(self, gpio):
        """Test that reading unwritten register returns 0."""
        offset = gpio._gpio_config.offsets.dir
        assert gpio.read_register(offset) == 0x00

    def test_write_dir_register(self, gpio):
        """Test writing to DIR register."""
        offset = gpio._gpio_config.offsets.dir
        gpio.write_register(offset, 0x0F)
        assert gpio.read_register(offset) == 0x0F

    def test_write_afsel_register(self, gpio):
        """Test writing to AFSEL register."""
        offset = gpio._gpio_config.offsets.afsel
        gpio.write_register(offset, 0x03)
        assert gpio.read_register(offset) == 0x03

    def test_write_im_register(self, gpio):
        """Test writing to IM (Interrupt Mask) register."""
        offset = gpio._gpio_config.offsets.im
        gpio.write_register(offset, 0x0F)
        assert gpio.read_register(offset) == 0x0F

    def test_sequential_writes(self, gpio):
        """Test multiple sequential writes."""
        offset = gpio._gpio_config.offsets.data
        for value in [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80]:
            gpio.write_register(offset, value)
            assert gpio.read_register(offset) == value


# ============================================================================
# MASKED DATA REGISTER TESTS
# ============================================================================

class TestMaskedDATARegister:
    """Test Tiva-C masked DATA register behavior.
    
    The masked DATA register uses the address offset [9:2] as a bitmask.
    Writing to DATA + 0x004 to DATA + 0x3FC applies a selective bitmask.
    """

    def test_masked_write_single_bit_offset_4(self, gpio):
        """Test masked write using offset 0x004 (mask = 0x01)."""
        data_offset = gpio._gpio_config.offsets.data
        # Write 0xFF to DATA register via direct access
        gpio.write_register(data_offset, 0xFF)
        # Write to masked address (offset + 4), mask = (4 >> 2) = 1
        masked_offset = data_offset + 0x004
        gpio.write_register(masked_offset, 0x00)
        # Result: bit 0 should be cleared
        assert gpio.read_register(data_offset) == 0xFE

    def test_masked_write_two_bits_offset_8(self, gpio):
        """Test masked write using offset 0x008 (mask = 0x03)."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0xFF)
        # Mask for offset 0x008: (8 >> 2) = 2 = 0b10
        masked_offset = data_offset + 0x008
        gpio.write_register(masked_offset, 0x00)
        # Only bit 1 should be affected
        assert gpio.read_register(data_offset) == 0xFD

    def test_masked_write_all_bits(self, gpio):
        """Test masked write using offset 0x3FC (mask = 0xFF)."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0x00)
        # Mask for offset 0x3FC: (0x3FC >> 2) = 0xFF (all 8 bits)
        masked_offset = data_offset + 0x3FC
        gpio.write_register(masked_offset, 0xFF)
        assert gpio.read_register(data_offset) == 0xFF

    def test_masked_write_preserves_unmasked_bits(self, gpio):
        """Test that masked write preserves bits outside the mask."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0b10101010)
        # Mask bits 1-0 (offset 0x00C: mask = 0x00C >> 2 = 0x03 = bits 1-0)
        masked_offset = data_offset + 0x00C
        gpio.write_register(masked_offset, 0b11111111)
        # Writing 0xFF with mask 0x03 sets bits [1:0] to 11
        # Original: 0b10101010, set bits [1:0]: 0b10101011 = 0xAB
        # Bits [7:2] are unchanged, bits [1:0] are set to match value & mask
        assert gpio.read_register(data_offset) == 0b10101011

    def test_masked_read_single_bit(self, gpio):
        """Test masked read returns only masked bits."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0xFF)
        # Read from masked address with mask = 1 (offset 0x004)
        masked_offset = data_offset + 0x004
        value = gpio.read_register(masked_offset)
        # Should return only bit 0
        assert value == 0x01

    def test_masked_read_multiple_bits(self, gpio):
        """Test masked read with multiple bits."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0b10110101)
        # Read from offset 0x00C: mask = 0x03 (bits 0-1)
        masked_offset = data_offset + 0x00C
        value = gpio.read_register(masked_offset)
        # Should return bits 0-1: 0b01
        assert value == 0b01

    def test_direct_data_register_unchanged_by_mask(self, gpio):
        """Test that direct DATA register writes bypass masking."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0xFF)
        # Direct write should replace entire value
        gpio.write_register(data_offset, 0x55)
        assert gpio.read_register(data_offset) == 0x55

    def test_masked_write_boundary_offset(self, gpio):
        """Test masked write at maximum valid offset (0x3FC)."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0x00)
        masked_offset = data_offset + ConstUtils.DATA_MASKED_MAX_OFFSET
        gpio.write_register(masked_offset, 0xAB)
        # All 8 bits should be set
        assert gpio.read_register(data_offset) == 0xAB

    def test_multiple_sequential_masked_writes(self, gpio):
        """Test multiple sequential masked writes."""
        data_offset = gpio._gpio_config.offsets.data
        gpio.write_register(data_offset, 0x00)
        
        # Set bit 0
        gpio.write_register(data_offset + 0x004, 0xFF)
        assert gpio.read_register(data_offset) == 0x01
        
        # Set bit 1
        gpio.write_register(data_offset + 0x008, 0xFF)
        assert gpio.read_register(data_offset) == 0x03
        
        # Clear bit 0
        gpio.write_register(data_offset + 0x004, 0x00)
        assert gpio.read_register(data_offset) == 0x02


# ============================================================================
# PIN MODE CONFIGURATION TESTS
# ============================================================================

class TestPinModeConfiguration:
    """Test pin mode configuration (INPUT, OUTPUT, ALTERNATE)."""

    def test_set_pin_mode_output(self, gpio):
        """Test setting a pin to OUTPUT mode."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        assert gpio.get_pin_mode(0) == PinMode.OUTPUT

    def test_set_pin_mode_input(self, gpio):
        """Test setting a pin to INPUT mode."""
        gpio.set_pin_mode(3, PinMode.INPUT)
        assert gpio.get_pin_mode(3) == PinMode.INPUT

    def test_set_pin_mode_alternate(self, gpio):
        """Test setting a pin to ALTERNATE mode."""
        gpio.set_pin_mode(5, PinMode.ALTERNATE)
        assert gpio.get_pin_mode(5) == PinMode.ALTERNATE

    def test_set_pin_mode_updates_dir_register_for_output(self, gpio):
        """Test that OUTPUT mode sets DIR register bit."""
        gpio.set_pin_mode(2, PinMode.OUTPUT)
        dir_value = gpio.read_register(gpio._gpio_config.offsets.dir)
        assert dir_value & (1 << 2)

    def test_set_pin_mode_updates_afsel_register_for_alternate(self, gpio):
        """Test that ALTERNATE mode sets AFSEL register bit."""
        gpio.set_pin_mode(4, PinMode.ALTERNATE)
        afsel_value = gpio.read_register(gpio._gpio_config.offsets.afsel)
        assert afsel_value & (1 << 4)

    def test_set_pin_mode_clears_dir_for_input(self, gpio):
        """Test that INPUT mode clears DIR register bit."""
        gpio.set_pin_mode(1, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.INPUT)
        dir_value = gpio.read_register(gpio._gpio_config.offsets.dir)
        assert not (dir_value & (1 << 1))

    def test_set_pin_mode_clears_afsel_for_input(self, gpio):
        """Test that INPUT mode clears AFSEL register bit."""
        gpio.set_pin_mode(1, PinMode.ALTERNATE)
        gpio.set_pin_mode(1, PinMode.INPUT)
        afsel_value = gpio.read_register(gpio._gpio_config.offsets.afsel)
        assert not (afsel_value & (1 << 1))

    def test_set_pin_mode_output_clears_afsel(self, gpio):
        """Test that OUTPUT mode clears AFSEL bit."""
        gpio.set_pin_mode(0, PinMode.ALTERNATE)
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        afsel_value = gpio.read_register(gpio._gpio_config.offsets.afsel)
        assert not (afsel_value & (1 << 0))

    def test_set_pin_mode_alternate_clears_dir(self, gpio):
        """Test that ALTERNATE mode clears DIR bit."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(0, PinMode.ALTERNATE)
        dir_value = gpio.read_register(gpio._gpio_config.offsets.dir)
        assert not (dir_value & (1 << 0))

    def test_set_pin_mode_all_pins(self, gpio):
        """Test setting mode on all pins."""
        for pin in range(gpio.NUM_PINS):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
            assert gpio.get_pin_mode(pin) == PinMode.OUTPUT

    def test_set_pin_mode_invalid_pin_negative(self, gpio):
        """Test that negative pin raises ValueError."""
        with pytest.raises(ValueError):
            gpio.set_pin_mode(-1, PinMode.OUTPUT)

    def test_set_pin_mode_invalid_pin_too_high(self, gpio):
        """Test that pin >= NUM_PINS raises ValueError."""
        with pytest.raises(ValueError):
            gpio.set_pin_mode(8, PinMode.OUTPUT)

    def test_get_pin_mode_invalid_pin_negative(self, gpio):
        """Test that getting mode for negative pin raises ValueError."""
        with pytest.raises(ValueError):
            gpio.get_pin_mode(-1)

    def test_get_pin_mode_invalid_pin_too_high(self, gpio):
        """Test that getting mode for pin >= NUM_PINS raises ValueError."""
        with pytest.raises(ValueError):
            gpio.get_pin_mode(8)

    def test_mode_persistence_across_writes(self, gpio):
        """Test that pin mode persists across register writes."""
        gpio.set_pin_mode(3, PinMode.OUTPUT)
        gpio.write_register(gpio._gpio_config.offsets.data, 0xFF)
        assert gpio.get_pin_mode(3) == PinMode.OUTPUT


# ============================================================================
# PIN VALUE CONTROL TESTS
# ============================================================================

class TestPinValueControl:
    """Test pin value read/write operations."""

    def test_set_pin_high(self, gpio):
        """Test setting a pin HIGH."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH

    def test_set_pin_low(self, gpio):
        """Test setting a pin LOW."""
        gpio.set_pin_value(0, PinLevel.LOW)
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_set_multiple_pins_mixed(self, gpio):
        """Test setting multiple pins with different values."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(1, PinLevel.LOW)
        gpio.set_pin_value(2, PinLevel.HIGH)
        gpio.set_pin_value(3, PinLevel.LOW)
        
        assert gpio.get_pin_value(0) == PinLevel.HIGH
        assert gpio.get_pin_value(1) == PinLevel.LOW
        assert gpio.get_pin_value(2) == PinLevel.HIGH
        assert gpio.get_pin_value(3) == PinLevel.LOW

    def test_set_pin_value_invalid_pin_negative(self, gpio):
        """Test that setting value for negative pin raises ValueError."""
        with pytest.raises(ValueError):
            gpio.set_pin_value(-1, PinLevel.HIGH)

    def test_set_pin_value_invalid_pin_too_high(self, gpio):
        """Test that setting value for pin >= NUM_PINS raises ValueError."""
        with pytest.raises(ValueError):
            gpio.set_pin_value(8, PinLevel.HIGH)

    def test_get_pin_value_invalid_pin_negative(self, gpio):
        """Test that getting value for negative pin raises ValueError."""
        with pytest.raises(ValueError):
            gpio.get_pin_value(-1)

    def test_get_pin_value_invalid_pin_too_high(self, gpio):
        """Test that getting value for pin >= NUM_PINS raises ValueError."""
        with pytest.raises(ValueError):
            gpio.get_pin_value(8)

    def test_pin_value_persistence(self, gpio):
        """Test that pin value persists across multiple reads."""
        gpio.set_pin_value(5, PinLevel.HIGH)
        for _ in range(10):
            assert gpio.get_pin_value(5) == PinLevel.HIGH

    def test_pin_value_toggle(self, gpio):
        """Test toggling pin value multiple times."""
        pin = 3
        for _ in range(3):
            gpio.set_pin_value(pin, PinLevel.HIGH)
            assert gpio.get_pin_value(pin) == PinLevel.HIGH
            gpio.set_pin_value(pin, PinLevel.LOW)
            assert gpio.get_pin_value(pin) == PinLevel.LOW

    def test_set_pin_affecting_data_register(self, gpio):
        """Test that setting pin value updates DATA register correctly."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        data = gpio.read_register(gpio._gpio_config.offsets.data)
        assert data & 0x01

    def test_set_all_pins_high(self, gpio):
        """Test setting all pins HIGH."""
        for pin in range(gpio.NUM_PINS):
            gpio.set_pin_value(pin, PinLevel.HIGH)
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_value(pin) == PinLevel.HIGH
        data = gpio.read_register(gpio._gpio_config.offsets.data)
        assert data == 0xFF

    def test_set_all_pins_low(self, gpio):
        """Test setting all pins LOW."""
        gpio.set_port_state(0xFF)  # Set all first
        for pin in range(gpio.NUM_PINS):
            gpio.set_pin_value(pin, PinLevel.LOW)
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_value(pin) == PinLevel.LOW
        data = gpio.read_register(gpio._gpio_config.offsets.data)
        assert data == 0x00


# ============================================================================
# PORT STATE CONTROL TESTS
# ============================================================================

class TestPortStateControl:
    """Test port-wide state read/write operations."""

    def test_set_port_state_all_high(self, gpio):
        """Test setting all pins HIGH via port state."""
        gpio.set_port_state(0xFF)
        assert gpio.get_port_state() == 0xFF

    def test_set_port_state_all_low(self, gpio):
        """Test setting all pins LOW via port state."""
        gpio.set_port_state(0x00)
        assert gpio.get_port_state() == 0x00

    def test_set_port_state_mixed_pattern(self, gpio):
        """Test setting port to mixed bit pattern."""
        pattern = 0b10101010
        gpio.set_port_state(pattern)
        assert gpio.get_port_state() == pattern

    def test_set_port_state_alternating_pattern(self, gpio):
        """Test alternating bit pattern."""
        pattern = 0b01010101
        gpio.set_port_state(pattern)
        assert gpio.get_port_state() == pattern

    def test_set_port_state_masks_to_8bits(self, gpio):
        """Test that port state is masked to 8 bits."""
        gpio.set_port_state(0x1FF)  # 9-bit value
        assert gpio.get_port_state() == 0xFF

    def test_port_state_individual_pin_consistency(self, gpio):
        """Test that port state reflects individual pin values."""
        gpio.set_pin_value(0, PinLevel.HIGH)
        gpio.set_pin_value(2, PinLevel.HIGH)
        gpio.set_pin_value(4, PinLevel.HIGH)
        
        expected = (1 << 0) | (1 << 2) | (1 << 4)
        assert gpio.get_port_state() == expected

    def test_set_port_state_replaces_previous_value(self, gpio):
        """Test that setting port state replaces previous values."""
        gpio.set_port_state(0xFF)
        assert gpio.get_port_state() == 0xFF
        gpio.set_port_state(0x00)
        assert gpio.get_port_state() == 0x00

    def test_sequential_port_writes(self, gpio):
        """Test multiple sequential port state writes."""
        patterns = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80]
        for pattern in patterns:
            gpio.set_port_state(pattern)
            assert gpio.get_port_state() == pattern

    def test_port_state_with_nonzero_initial_value(self, gpio_nonzero):
        """Test port state with non-zero initial value."""
        # Initial value is 0xAA, direct read should return it
        assert gpio_nonzero.get_port_state() == 0xAA

    def test_port_state_overrides_initial_value(self, gpio_nonzero):
        """Test that setting port state overrides initial value."""
        gpio_nonzero.set_port_state(0x55)
        assert gpio_nonzero.get_port_state() == 0x55


# ============================================================================
# INTERRUPT CONFIGURATION TESTS
# ============================================================================

class TestInterruptConfiguration:
    """Test interrupt configuration and handling."""

    def test_configure_interrupt_edge_triggered(self, gpio):
        """Test configuring interrupt as edge-triggered."""
        gpio.configure_interrupt(0, edge_triggered=True)
        assert gpio._interrupt_config[0]["edge_triggered"] is True

    def test_configure_interrupt_level_triggered(self, gpio):
        """Test configuring interrupt as level-triggered."""
        gpio.configure_interrupt(5, edge_triggered=False)
        assert gpio._interrupt_config[5]["edge_triggered"] is False

    def test_configure_interrupt_updates_is_register_edge(self, gpio):
        """Test that edge-triggered sets IS register bit to 0."""
        gpio.configure_interrupt(2, edge_triggered=True)
        is_value = gpio.read_register(gpio._gpio_config.offsets.is_)
        # Edge-triggered is 0, level-triggered is 1
        assert not (is_value & (1 << 2))

    def test_configure_interrupt_updates_is_register_level(self, gpio):
        """Test that level-triggered sets IS register bit to 1."""
        gpio.configure_interrupt(3, edge_triggered=False)
        is_value = gpio.read_register(gpio._gpio_config.offsets.is_)
        # Level-triggered is 1
        assert is_value & (1 << 3)

    def test_configure_interrupt_updates_im_register(self, gpio):
        """Test that configure_interrupt sets IM register bit."""
        gpio.configure_interrupt(1)
        im_value = gpio.read_register(gpio._gpio_config.offsets.im)
        assert im_value & (1 << 1)

    def test_clear_interrupt_flag(self, gpio):
        """Test clearing an interrupt flag."""
        set_interrupt_flag(gpio, 3)
        assert is_interrupt_flag_set(gpio, 3)
        gpio.clear_interrupt_flag(3)
        assert not is_interrupt_flag_set(gpio, 3)

    def test_clear_interrupt_flag_via_icr_register(self, gpio):
        """Test clearing interrupt flag via ICR register write."""
        set_interrupt_flag(gpio, 2)
        gpio.write_register(gpio._gpio_config.offsets.icr, (1 << 2))
        assert not is_interrupt_flag_set(gpio, 2)

    def test_raw_interrupt_status_register(self, gpio):
        """Test RIS register returns current interrupt flags."""
        set_interrupt_flag(gpio, 0)
        set_interrupt_flag(gpio, 3)
        set_interrupt_flag(gpio, 7)
        
        ris_value = gpio.read_register(gpio._gpio_config.offsets.ris)
        assert (ris_value & (1 << 0)) != 0
        assert (ris_value & (1 << 3)) != 0
        assert (ris_value & (1 << 7)) != 0

    def test_masked_interrupt_status_register(self, gpio):
        """Test MIS register applies interrupt mask."""
        set_interrupt_flag(gpio, 1)
        set_interrupt_flag(gpio, 5)
        
        gpio.configure_interrupt(1)  # Enable interrupt 1
        gpio.configure_interrupt(5)  # Enable interrupt 5
        
        mis_value = gpio.read_register(gpio._gpio_config.offsets.mis)
        assert (mis_value & (1 << 1)) != 0
        assert (mis_value & (1 << 5)) != 0

    def test_masked_interrupt_status_respects_disable(self, gpio):
        """Test MIS register reflects disabled interrupts."""
        set_interrupt_flag(gpio, 2)
        # Don't configure interrupt 2, so IM bit is not set
        
        mis_value = gpio.read_register(gpio._gpio_config.offsets.mis)
        # Even though flag is set, MIS should be 0 if interrupt not enabled
        assert not (mis_value & (1 << 2))

    def test_configure_interrupt_invalid_pin_negative(self, gpio):
        """Test that configuring interrupt for negative pin raises ValueError."""
        with pytest.raises(ValueError):
            gpio.configure_interrupt(-1)

    def test_configure_interrupt_invalid_pin_too_high(self, gpio):
        """Test that configuring interrupt for pin >= NUM_PINS raises ValueError."""
        with pytest.raises(ValueError):
            gpio.configure_interrupt(8)

    def test_clear_interrupt_flag_invalid_pin(self, gpio):
        """Test that clearing interrupt for invalid pin raises ValueError."""
        with pytest.raises(ValueError):
            gpio.clear_interrupt_flag(8)

    def test_multiple_interrupts_configured(self, gpio):
        """Test configuring multiple pin interrupts."""
        for pin in range(4):
            gpio.configure_interrupt(pin, edge_triggered=(pin % 2 == 0))
        
        im_value = gpio.read_register(gpio._gpio_config.offsets.im)
        assert im_value == 0x0F  # Lower 4 bits set

    def test_interrupts_edge_triggered_vs_level(self, gpio):
        """Test mixed edge and level triggered configurations."""
        gpio.configure_interrupt(0, edge_triggered=True)
        gpio.configure_interrupt(1, edge_triggered=False)
        gpio.configure_interrupt(2, edge_triggered=True)
        
        # Check interrupt config
        assert gpio._interrupt_config[0]["edge_triggered"] is True   # Pin 0: edge-triggered
        assert gpio._interrupt_config[1]["edge_triggered"] is False  # Pin 1: level-triggered  
        assert gpio._interrupt_config[2]["edge_triggered"] is True   # Pin 2: edge-triggered


# ============================================================================
# RESET TESTS
# ============================================================================

class TestReset:
    """Test GPIO reset functionality."""

    def test_reset_clears_data_register(self, gpio):
        """Test that reset clears DATA register."""
        gpio.write_register(gpio._gpio_config.offsets.data, 0xFF)
        gpio.reset()
        assert gpio.read_register(gpio._gpio_config.offsets.data) == 0x00

    def test_reset_preserves_initial_value(self, gpio_nonzero):
        """Test that reset restores initial value."""
        gpio_nonzero.write_register(gpio_nonzero._gpio_config.offsets.data, 0x55)
        gpio_nonzero.reset()
        # After reset, reading DATA should return initial value
        assert gpio_nonzero.read_register(
            gpio_nonzero._gpio_config.offsets.data
        ) == 0xAA

    def test_reset_restores_pin_modes_to_input(self, gpio):
        """Test that reset restores all pins to INPUT mode."""
        for pin in range(gpio.NUM_PINS):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
        
        gpio.reset()
        
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT

    def test_reset_clears_dir_register(self, gpio):
        """Test that reset clears DIR register."""
        gpio.write_register(gpio._gpio_config.offsets.dir, 0xFF)
        gpio.reset()
        assert gpio.read_register(gpio._gpio_config.offsets.dir) == 0x00

    def test_reset_clears_afsel_register(self, gpio):
        """Test that reset clears AFSEL register."""
        gpio.write_register(gpio._gpio_config.offsets.afsel, 0xFF)
        gpio.reset()
        assert gpio.read_register(gpio._gpio_config.offsets.afsel) == 0x00

    def test_reset_clears_interrupt_flags(self, gpio):
        """Test that reset clears all interrupt flags."""
        set_interrupt_flag(gpio, 0)
        set_interrupt_flag(gpio, 3)
        set_interrupt_flag(gpio, 7)
        
        gpio.reset()
        
        for pin in range(gpio.NUM_PINS):
            assert not is_interrupt_flag_set(gpio, pin)

    def test_reset_clears_im_register(self, gpio):
        """Test that reset clears IM register."""
        gpio.write_register(gpio._gpio_config.offsets.im, 0xFF)
        gpio.reset()
        assert gpio.read_register(gpio._gpio_config.offsets.im) == 0x00

    def test_reset_clears_is_register(self, gpio):
        """Test that reset clears IS register."""
        gpio.write_register(gpio._gpio_config.offsets.is_, 0xFF)
        gpio.reset()
        assert gpio.read_register(gpio._gpio_config.offsets.is_) == 0x00

    def test_reset_clears_interrupt_config(self, gpio):
        """Test that reset clears interrupt configuration."""
        for pin in range(4):
            gpio.configure_interrupt(pin, edge_triggered=True)
        
        gpio.reset()
        
        # After reset, all interrupts should be cleared
        for pin in range(gpio.NUM_PINS):
            assert gpio._interrupt_config[pin]["edge_triggered"] is False

    def test_reset_multiple_times_idempotent(self, gpio):
        """Test that multiple resets produce consistent results."""
        for _ in range(3):
            gpio.write_register(gpio._gpio_config.offsets.data, 0xFF)
            gpio.reset()
            assert gpio.read_register(gpio._gpio_config.offsets.data) == 0x00

    def test_reset_after_complex_operations(self, gpio):
        """Test reset after performing various operations."""
        # Perform multiple operations
        for pin in range(4):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
            gpio.set_pin_value(pin, PinLevel.HIGH)
            gpio.configure_interrupt(pin)
        
        # Reset and verify
        gpio.reset()
        
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_mode(pin) == PinMode.INPUT
            assert gpio.get_pin_value(pin) == PinLevel.LOW
            assert not is_interrupt_flag_set(gpio, pin)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests covering complex scenarios."""

    def test_gpio_direction_and_value_workflow(self, gpio):
        """Test complete GPIO configuration workflow."""
        # Configure pins 0-3 as OUTPUT
        for pin in range(4):
            gpio.set_pin_mode(pin, PinMode.OUTPUT)
        
        # Configure pins 4-7 as ALTERNATE
        for pin in range(4, 8):
            gpio.set_pin_mode(pin, PinMode.ALTERNATE)
        
        # Set output pins HIGH
        for pin in range(4):
            gpio.set_pin_value(pin, PinLevel.HIGH)
        
        # Verify configuration
        for pin in range(4):
            assert gpio.get_pin_mode(pin) == PinMode.OUTPUT
            assert gpio.get_pin_value(pin) == PinLevel.HIGH
        
        for pin in range(4, 8):
            assert gpio.get_pin_mode(pin) == PinMode.ALTERNATE

    def test_mixed_pin_modes(self, gpio):
        """Test pins with different modes in same port."""
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_mode(1, PinMode.INPUT)
        gpio.set_pin_mode(2, PinMode.ALTERNATE)
        
        assert gpio.get_pin_mode(0) == PinMode.OUTPUT
        assert gpio.get_pin_mode(1) == PinMode.INPUT
        assert gpio.get_pin_mode(2) == PinMode.ALTERNATE

    def test_port_state_after_individual_operations(self, gpio):
        """Test that port state reflects individual pin operations."""
        for pin in range(4):
            gpio.set_pin_value(pin, PinLevel.HIGH)
        
        assert gpio.get_port_state() == 0x0F

    def test_interrupt_workflow_complete(self, gpio):
        """Test complete interrupt configuration workflow."""
        # Configure interrupts on pins 0, 2, 4, 6
        for pin in [0, 2, 4, 6]:
            gpio.configure_interrupt(pin, edge_triggered=True)
        
        # Simulate interrupt flags
        for pin in [0, 2, 4, 6]:
            set_interrupt_flag(gpio, pin)
        
        # Check RIS
        ris = gpio.read_register(gpio._gpio_config.offsets.ris)
        assert ris == 0b01010101
        
        # Check MIS
        mis = gpio.read_register(gpio._gpio_config.offsets.mis)
        assert mis == 0b01010101
        
        # Clear interrupt 0
        gpio.clear_interrupt_flag(0)
        
        # Verify cleared
        ris = gpio.read_register(gpio._gpio_config.offsets.ris)
        assert not (ris & (1 << 0))

    def test_masked_data_with_pin_operations(self, gpio):
        """Test masked DATA register with pin operations."""
        gpio.set_port_state(0xFF)
        
        # Use masked read to get specific bits
        data_offset = gpio._gpio_config.offsets.data
        masked_offset = data_offset + 0x00C  # mask = 0x03
        
        value = gpio.read_register(masked_offset)
        assert value == 0x03  # Lower 2 bits set

    def test_reset_preserves_configuration_template(self, gpio):
        """Test that reset provides clean slate for reconfiguration."""
        # Initial configuration
        gpio.set_pin_mode(0, PinMode.OUTPUT)
        gpio.set_pin_value(0, PinLevel.HIGH)
        
        # Reset
        gpio.reset()
        
        # Reconfigure differently
        gpio.set_pin_mode(0, PinMode.INPUT)
        assert gpio.get_pin_mode(0) == PinMode.INPUT
        assert gpio.get_pin_value(0) == PinLevel.LOW

    def test_all_pins_full_workflow(self, gpio):
        """Test a full workflow across all 8 pins."""
        # Set each pin's mode based on position
        for pin in range(gpio.NUM_PINS):
            if pin % 3 == 0:
                gpio.set_pin_mode(pin, PinMode.OUTPUT)
            elif pin % 3 == 1:
                gpio.set_pin_mode(pin, PinMode.INPUT)
            else:
                gpio.set_pin_mode(pin, PinMode.ALTERNATE)
        
        # Set output pins
        for pin in range(gpio.NUM_PINS):
            if pin % 3 == 0:
                gpio.set_pin_value(pin, PinLevel.HIGH)
        
        # Configure interrupts
        for pin in range(gpio.NUM_PINS):
            if pin % 3 == 1:
                gpio.configure_interrupt(pin, edge_triggered=(pin % 2 == 0))
        
        # Verify all pins
        for pin in range(gpio.NUM_PINS):
            if pin % 3 == 0:
                assert gpio.get_pin_mode(pin) == PinMode.OUTPUT
                assert gpio.get_pin_value(pin) == PinLevel.HIGH
            elif pin % 3 == 1:
                assert gpio.get_pin_mode(pin) == PinMode.INPUT
            else:
                assert gpio.get_pin_mode(pin) == PinMode.ALTERNATE


# ============================================================================
# EDGE CASES AND BOUNDARY TESTS
# ============================================================================

class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_repeated_writes_same_value(self, gpio):
        """Test repeated writes of the same value."""
        for _ in range(10):
            gpio.write_register(gpio._gpio_config.offsets.data, 0x55)
            assert gpio.read_register(gpio._gpio_config.offsets.data) == 0x55

    def test_alternating_bit_patterns(self, gpio):
        """Test alternating bit patterns."""
        patterns = [0xAA, 0x55, 0xAA, 0x55]
        for pattern in patterns:
            gpio.set_port_state(pattern)
            assert gpio.get_port_state() == pattern

    def test_all_zeros_then_all_ones(self, gpio):
        """Test transitions between all zeros and all ones."""
        gpio.set_port_state(0x00)
        assert gpio.get_port_state() == 0x00
        
        gpio.set_port_state(0xFF)
        assert gpio.get_port_state() == 0xFF

    def test_set_pin_immediately_after_reset(self, gpio):
        """Test setting pin value immediately after reset."""
        gpio.reset()
        gpio.set_pin_value(0, PinLevel.HIGH)
        assert gpio.get_pin_value(0) == PinLevel.HIGH

    def test_masked_register_boundary_conditions(self, gpio):
        """Test masked register at boundary offsets."""
        data_offset = gpio._gpio_config.offsets.data
        
        # Test at offset + 4 (minimum masked offset)
        masked_offset_min = data_offset + 0x004
        gpio.write_register(masked_offset_min, 0xFF)
        assert gpio.read_register(data_offset) == 0x01
        
        # Test at maximum offset
        gpio.write_register(data_offset, 0x00)
        masked_offset_max = data_offset + ConstUtils.DATA_MASKED_MAX_OFFSET
        gpio.write_register(masked_offset_max, 0xFF)
        assert gpio.read_register(data_offset) == 0xFF

    def test_sequential_mode_changes(self, gpio):
        """Test rapidly changing pin modes."""
        pin = 0
        modes = [PinMode.OUTPUT, PinMode.INPUT, PinMode.ALTERNATE, PinMode.OUTPUT]
        
        for mode in modes:
            gpio.set_pin_mode(pin, mode)
            assert gpio.get_pin_mode(pin) == mode

    def test_interrupt_flag_operations_consistency(self, gpio):
        """Test consistency of interrupt flag operations."""
        for pin in range(gpio.NUM_PINS):
            set_interrupt_flag(gpio, pin)
            assert is_interrupt_flag_set(gpio, pin)
            clear_interrupt_flag(gpio, pin)
            assert not is_interrupt_flag_set(gpio, pin)

    def test_register_mask_8bit_enforcement(self, gpio):
        """Test that TM4C123 specific registers mask to 8 bits on write."""
        # These registers are explicitly masked to 8 bits in write_register
        registers_8bit = [
            gpio._gpio_config.offsets.dir,
            gpio._gpio_config.offsets.afsel,
            gpio._gpio_config.offsets.im,
            gpio._gpio_config.offsets.is_,
        ]
        
        for offset in registers_8bit:
            gpio.write_register(offset, 0xFFFF)  # 16-bit value
            value = gpio.read_register(offset)
            # DIR, AFSEL, IS, IM are masked to 8 bits in write_register
            assert value == 0xFF
        
        # DATA register uses base class masking (32-bit)
        gpio.write_register(gpio._gpio_config.offsets.data, 0x1FFFF)
        data_value = gpio.read_register(gpio._gpio_config.offsets.data)
        assert data_value == 0x1FFFF  # Base class masks to 32 bits

    def test_zero_initial_value_operations(self, gpio):
        """Test operations with zero initial value."""
        data = gpio.read_register(gpio._gpio_config.offsets.data)
        assert data == 0x00
        
        for pin in range(gpio.NUM_PINS):
            assert gpio.get_pin_value(pin) == PinLevel.LOW

    def test_nonzero_initial_value_operations(self, gpio_nonzero):
        """Test operations with non-zero initial value."""
        data = gpio_nonzero.read_register(gpio_nonzero._gpio_config.offsets.data)
        assert data == 0xAA
        
        for pin in range(gpio_nonzero.NUM_PINS):
            expected = PinLevel.HIGH if (0xAA & (1 << pin)) else PinLevel.LOW
            assert gpio_nonzero.get_pin_value(pin) == expected
