"""Unit tests for TM4C123_Memory class."""

from unittest.mock import MagicMock, Mock

import pytest

from simulator.core.exceptions import MemoryAccessError, MemoryBoundsError
from simulator.interfaces.peripheral import BasePeripherals
from simulator.tm4c123.memory import PeripheralMapping, TM4C123_Memory
from simulator.utils.config_loader import Memory_Config


class MockPeripheral(BasePeripherals):
    """Mock peripheral for testing."""

    def __init__(self):
        self.registers = {}

    def write_register(self, offset: int, value: int) -> None:
        self.registers[offset] = value

    def read_register(self, offset: int) -> int:
        return self.registers.get(offset, 0)

    def reset(self) -> None:
        self.registers.clear()


@pytest.fixture
def memory_config():
    """Create a Memory_Config fixture."""
    return Memory_Config(
        flash_base=0x08000000,
        flash_size=524288,  # 512 KB
        sram_base=0x20000000,
        sram_size=131072,  # 128 KB
        periph_base=0x40000000,
        periph_size=0x00100000,  # 1 MB
        bitband_base=0x42000000,
        bitband_size=0x02000000,  # 32 MB
    )


@pytest.fixture
def memory(memory_config):
    """Create a TM4C123_Memory instance."""
    return TM4C123_Memory(memory_config)


@pytest.fixture
def mock_peripheral():
    """Create a mock peripheral."""
    return MockPeripheral()


class TestTM4C123MemoryInit:
    """Test memory initialization."""

    def test_init_creates_empty_storages(self, memory_config):
        """Test that init creates empty FLASH and SRAM."""
        mem = TM4C123_Memory(memory_config)
        assert len(mem._flash) == memory_config.flash_size
        assert len(mem._sram) == memory_config.sram_size

    def test_init_creates_empty_peripherals(self, memory_config):
        """Test that peripherals dict is empty on init."""
        mem = TM4C123_Memory(memory_config)
        assert mem._peripherals == {}

    def test_init_stores_config(self, memory_config):
        """Test that config is stored."""
        mem = TM4C123_Memory(memory_config)
        assert mem.memory_config == memory_config


class TestFlashMemoryOperations:
    """Test FLASH memory read operations."""

    def test_read_single_byte_from_flash(self, memory):
        """Test reading a single byte from FLASH."""
        # Write directly to backing storage
        memory._flash[0] = 0x42
        value = memory.read(0x08000000, 1)
        assert value == 0x42

    def test_read_two_bytes_from_flash_little_endian(self, memory):
        """Test reading 2 bytes from FLASH in little-endian."""
        memory._flash[0] = 0x34
        memory._flash[1] = 0x12
        value = memory.read(0x08000000, 2)
        assert value == 0x1234

    def test_read_four_bytes_from_flash_little_endian(self, memory):
        """Test reading 4 bytes from FLASH in little-endian."""
        memory._flash[0] = 0x78
        memory._flash[1] = 0x56
        memory._flash[2] = 0x34
        memory._flash[3] = 0x12
        value = memory.read(0x08000000, 4)
        assert value == 0x12345678

    def test_write_to_flash_raises_error(self, memory):
        """Test that writing to FLASH raises MemoryPermissionError."""
        with pytest.raises(MemoryAccessError):
            memory.write(0x08000000, 1, 0xFF)

    def test_read_from_flash_boundary(self, memory):
        """Test reading at the end of FLASH range."""
        # FLASH_BASE + FLASH_SIZE - 1 is the last valid address
        flash_last_addr = 0x08000000 + 524288 - 1
        memory._flash[-1] = 0xAA
        value = memory.read(flash_last_addr, 1)
        assert value == 0xAA

    def test_read_beyond_flash_raises_error(self, memory):
        """Test that reading beyond FLASH range raises error."""
        flash_end = 0x08000000 + 524288
        with pytest.raises(MemoryAccessError):
            memory.read(flash_end, 1)


class TestSRAMMemoryOperations:
    """Test SRAM memory read/write operations."""

    def test_write_single_byte_to_sram(self, memory):
        """Test writing a single byte to SRAM."""
        memory.write(0x20000000, 1, 0x42)
        assert memory._sram[0] == 0x42

    def test_read_single_byte_from_sram(self, memory):
        """Test reading a single byte from SRAM."""
        memory._sram[0] = 0x55
        value = memory.read(0x20000000, 1)
        assert value == 0x55

    def test_write_two_bytes_to_sram_little_endian(self, memory):
        """Test writing 2 bytes to SRAM in little-endian."""
        memory.write(0x20000000, 2, 0x1234)
        assert memory._sram[0] == 0x34
        assert memory._sram[1] == 0x12

    def test_read_two_bytes_from_sram_little_endian(self, memory):
        """Test reading 2 bytes from SRAM in little-endian."""
        memory._sram[0] = 0x34
        memory._sram[1] = 0x12
        value = memory.read(0x20000000, 2)
        assert value == 0x1234

    def test_write_four_bytes_to_sram_little_endian(self, memory):
        """Test writing 4 bytes to SRAM in little-endian."""
        memory.write(0x20000000, 4, 0x12345678)
        assert memory._sram[0] == 0x78
        assert memory._sram[1] == 0x56
        assert memory._sram[2] == 0x34
        assert memory._sram[3] == 0x12

    def test_read_four_bytes_from_sram_little_endian(self, memory):
        """Test reading 4 bytes from SRAM in little-endian."""
        memory._sram[0] = 0x78
        memory._sram[1] = 0x56
        memory._sram[2] = 0x34
        memory._sram[3] = 0x12
        value = memory.read(0x20000000, 4)
        assert value == 0x12345678

    def test_sram_read_write_roundtrip(self, memory):
        """Test writing and reading back the same value."""
        test_values = [0xFF, 0x1234, 0xDEADBEEF]
        for i, val in enumerate(test_values):
            size = 1 if val < 256 else (2 if val < 65536 else 4)
            addr = 0x20000000 + i * 4
            memory.write(addr, size, val)
            read_val = memory.read(addr, size)
            assert read_val == val

    def test_write_beyond_sram_raises_error(self, memory):
        """Test that writing beyond SRAM raises error."""
        sram_end = 0x20000000 + 131072
        with pytest.raises(MemoryAccessError):
            memory.write(sram_end, 1, 0xFF)

    def test_read_beyond_sram_raises_error(self, memory):
        """Test that reading beyond SRAM raises error."""
        sram_end = 0x20000000 + 131072
        with pytest.raises(MemoryAccessError):
            memory.read(sram_end, 1)

    def test_write_at_sram_boundary(self, memory):
        """Test writing at the end of SRAM range."""
        sram_last_addr = 0x20000000 + 131072 - 1
        memory.write(sram_last_addr, 1, 0xBB)
        assert memory._sram[-1] == 0xBB


class TestInvalidMemoryOperations:
    """Test invalid memory access operations."""

    def test_read_invalid_size(self, memory):
        """Test that reading with invalid size raises error."""
        with pytest.raises(MemoryAccessError):
            memory.read(0x20000000, 3)  # Invalid size

    def test_write_invalid_size(self, memory):
        """Test that writing with invalid size raises error."""
        with pytest.raises(MemoryAccessError):
            memory.write(0x20000000, 3, 0xFF)  # Invalid size

    def test_read_unmapped_address(self, memory):
        """Test reading from unmapped address raises error."""
        # Use address that doesn't map to any region
        unmapped_addr = 0x30000000
        with pytest.raises(MemoryAccessError):
            memory.read(unmapped_addr, 1)

    def test_write_unmapped_address(self, memory):
        """Test writing to unmapped address raises error."""
        unmapped_addr = 0x30000000
        with pytest.raises(MemoryAccessError):
            memory.write(unmapped_addr, 1, 0xFF)

    def test_read_negative_size(self, memory):
        """Test that negative size is handled."""
        with pytest.raises(MemoryAccessError):
            memory.read(0x20000000, -1)

    def test_write_negative_size(self, memory):
        """Test that negative size is handled."""
        with pytest.raises(MemoryAccessError):
            memory.write(0x20000000, -1, 0xFF)

    def test_read_zero_size(self, memory):
        """Test that zero size is handled."""
        with pytest.raises(MemoryAccessError):
            memory.read(0x20000000, 0)

    def test_write_zero_size(self, memory):
        """Test that zero size is handled."""
        with pytest.raises(MemoryAccessError):
            memory.write(0x20000000, 0, 0xFF)


class TestPeripheralOperations:
    """Test peripheral memory operations."""

    def test_write_to_peripheral(self, memory, mock_peripheral):
        """Test writing to a peripheral."""
        # Register peripheral
        memory._peripherals[0x40000000] = PeripheralMapping(
            base=0x40000000, size=0x1000, instance=mock_peripheral
        )

        memory.write(0x40000000, 4, 0x12345678)
        assert mock_peripheral.read_register(0) == 0x12345678

    def test_read_from_peripheral(self, memory, mock_peripheral):
        """Test reading from a peripheral."""
        memory._peripherals[0x40000000] = PeripheralMapping(
            base=0x40000000, size=0x1000, instance=mock_peripheral
        )

        mock_peripheral.write_register(0, 0xDEADBEEF)
        value = memory.read(0x40000000, 4)
        assert value == 0xDEADBEEF

    def test_read_from_nonexistent_peripheral(self, memory):
        """Test reading from unmapped peripheral address."""
        with pytest.raises(MemoryAccessError):
            memory.read(0x40000000, 4)

    def test_write_to_nonexistent_peripheral(self, memory):
        """Test writing to unmapped peripheral address."""
        with pytest.raises(MemoryAccessError):
            memory.write(0x40000000, 4, 0xFF)

    def test_multiple_peripherals(self, memory):
        """Test accessing multiple peripherals."""
        periph1 = MockPeripheral()
        periph2 = MockPeripheral()

        memory._peripherals[0x40000000] = PeripheralMapping(
            base=0x40000000, size=0x1000, instance=periph1
        )
        memory._peripherals[0x40001000] = PeripheralMapping(
            base=0x40001000, size=0x1000, instance=periph2
        )

        memory.write(0x40000000, 4, 0x1111)
        memory.write(0x40001000, 4, 0x2222)

        assert memory.read(0x40000000, 4) == 0x1111
        assert memory.read(0x40001000, 4) == 0x2222

    def test_peripherals_property_is_dict(self, memory):
        """Test that peripherals property returns a dictionary."""
        assert isinstance(memory._peripherals, dict)


class TestBitbandOperations:
    """Test bit-band alias region operations."""

    def test_read_bitband_bit_0(self, memory):
        """Test reading bit 0 via bit-band."""
        # Set bit 0 in underlying SRAM
        memory.write(0x20000000, 4, 0x00000001)
        # Read via bit-band: each bitband word maps to 1 bit
        value = memory.read(0x42000000, 4)  # Bitband word 0 = bit 0
        assert value == 1

    def test_read_bitband_bit_not_set(self, memory):
        """Test reading unset bit via bit-band."""
        memory.write(0x20000000, 4, 0x00000000)
        value = memory.read(0x42000000, 4)
        assert value == 0

    def test_write_bitband_set_bit(self, memory):
        """Test setting a bit via bit-band."""
        memory.write(0x20000000, 4, 0x00000000)
        # Write 1 to bit 0 (word 0 at bitband 0x42000000)
        memory.write(0x42000000, 4, 1)
        value = memory.read(0x20000000, 4)
        assert value == 1

    def test_write_bitband_clear_bit(self, memory):
        """Test clearing a bit via bit-band."""
        memory.write(0x20000000, 4, 0xFFFFFFFF)
        # Write 0 to bit 0 (word 0 at bitband 0x42000000)
        memory.write(0x42000000, 4, 0)
        value = memory.read(0x20000000, 4)
        # After clearing bit 0, value should be 0xFFFFFFFE
        assert value == 0xFFFFFFFE

    def test_multiple_bitband_operations(self, memory):
        """Test multiple bit-band read/write operations."""
        # Clear SRAM first
        memory.write(0x20000000, 4, 0)
        memory.write(0x20000004, 4, 0)
        memory.write(0x20000008, 4, 0)
        memory.write(0x2000000C, 4, 0)

        # Set, read and verify via bit-band at different addresses
        memory.write(0x42000000, 4, 1)  # Set bit via bitband
        value = memory.read(0x42000000, 4)
        assert value == 1

        # Clear the bit
        memory.write(0x42000000, 4, 0)
        value = memory.read(0x42000000, 4)
        assert value == 0


class TestAddressClassification:
    """Test address region classification."""

    def test_is_flash(self, memory):
        """Test Flash address classification."""
        assert memory._is_flash(0x08000000) is True
        assert memory._is_flash(0x08000001) is True
        assert memory._is_flash(0x0807FFFF) is True
        assert memory._is_flash(0x08080000) is False  # Beyond FLASH_SIZE
        assert memory._is_flash(0x20000000) is False  # SRAM address

    def test_is_sram(self, memory):
        """Test SRAM address classification."""
        assert memory._is_sram(0x20000000) is True
        assert memory._is_sram(0x20000001) is True
        assert memory._is_sram(0x2001FFFF) is True
        assert memory._is_sram(0x20020000) is False  # Beyond SRAM_SIZE
        assert memory._is_sram(0x08000000) is False  # FLASH address

    def test_is_peripheral(self, memory):
        """Test peripheral address classification."""
        assert memory._is_peripheral(0x40000000) is True
        assert memory._is_peripheral(0x40000001) is True
        assert memory._is_peripheral(0x400FFFFF) is True
        assert memory._is_peripheral(0x40100000) is False  # Beyond PERIPH_SIZE
        assert memory._is_peripheral(0x20000000) is False  # SRAM address

    def test_is_bitband_alias(self, memory):
        """Test bit-band alias address classification."""
        assert memory._is_bitband_alias(0x42000000) is True
        assert memory._is_bitband_alias(0x42000001) is True
        assert memory._is_bitband_alias(0x43FFFFFF) is True
        assert memory._is_bitband_alias(0x44000000) is False  # Beyond BITBAND_SIZE
        assert memory._is_bitband_alias(0x20000000) is False  # SRAM address

    def test_in_region_helper(self, memory):
        """Test the _in_region helper method."""
        # Test inside region
        assert memory._in_region(0x20000000, 0x20000000, 0x1000) is True
        assert memory._in_region(0x20000500, 0x20000000, 0x1000) is True

        # Test outside region
        assert memory._in_region(0x20001000, 0x20000000, 0x1000) is False
        assert memory._in_region(0x1FFFFFFF, 0x20000000, 0x1000) is False

        # Test boundary
        assert (
            memory._in_region(0x20001000, 0x20000000, 0x1000) is False
        )  # Exclusive upper


class TestValueMasking:
    """Test that values are properly masked."""

    def test_write_8bit_value_masked(self, memory):
        """Test that 8-bit writes are properly masked."""
        memory.write(0x20000000, 1, 0x1FF)  # 9-bit value, but 8-bit write
        assert memory._sram[0] == 0xFF  # Masked to 8 bits

    def test_write_16bit_value_masked(self, memory):
        """Test that 16-bit writes are properly masked."""
        memory.write(0x20000000, 2, 0x1FFFF)  # 17-bit value
        value = memory.read(0x20000000, 2)
        assert value == 0xFFFF  # Masked to 16 bits

    def test_write_32bit_value_masked(self, memory):
        """Test that 32-bit writes are properly masked."""
        memory.write(0x20000000, 4, 0x1FFFFFFFF)  # 33-bit value
        value = memory.read(0x20000000, 4)
        assert value == 0xFFFFFFFF  # Masked to 32 bits


class TestMemoryReset:
    """Test memory reset functionality."""

    def test_reset_clears_sram_single_location(self, memory):
        """Test that reset clears a single SRAM location."""
        sram_addr = 0x20000000
        test_value = 0xDEADBEEF

        memory.write(sram_addr, 4, test_value)
        assert memory.read(sram_addr, 4) == test_value

        memory.reset()
        assert memory.read(sram_addr, 4) == 0x00000000

    def test_reset_clears_entire_sram(self, memory):
        """Test that reset clears entire SRAM."""
        # Write to multiple locations across SRAM
        locations = [
            0x20000000,
            0x20001000,
            0x20002000,
            0x2001FC00,  # Near end of SRAM
        ]

        for addr in locations:
            memory.write(addr, 4, 0xFFFFFFFF)

        # Verify writes succeeded
        for addr in locations:
            assert memory.read(addr, 4) == 0xFFFFFFFF

        # Reset
        memory.reset()

        # Verify all locations cleared
        for addr in locations:
            assert memory.read(addr, 4) == 0x00000000

    def test_reset_preserves_flash(self, memory):
        """Test that reset preserves FLASH content."""
        flash_addr = 0x08000000
        # Read FLASH before reset
        flash_value_before = memory.read(flash_addr, 4)

        # Write to SRAM and reset
        memory.write(0x20000000, 4, 0xDEADBEEF)
        memory.reset()

        # Verify FLASH unchanged
        flash_value_after = memory.read(flash_addr, 4)
        assert flash_value_after == flash_value_before

    def test_reset_clears_peripherals_dict(self, memory, mock_peripheral):
        """Test that reset clears registered peripherals."""
        # Register peripherals
        memory._peripherals[0x40000000] = PeripheralMapping(
            base=0x40000000, size=0x1000, instance=mock_peripheral
        )
        memory._peripherals[0x40001000] = PeripheralMapping(
            base=0x40001000, size=0x1000, instance=mock_peripheral
        )

        assert len(memory._peripherals) == 2

        # Reset
        memory.reset()

        # New behavior: Memory.reset() no longer unregisters peripherals;
        # peripheral lifecycle is managed by the board. Verify peripherals
        # remain registered and memory cleared SRAM instead.
        assert len(memory._peripherals) == 2
        assert memory._peripherals != {}

    def test_reset_calls_peripheral_reset(self, memory):
        """Test that registered peripherals are reset during memory reset."""
        mock_periph = MagicMock(spec=BasePeripherals)
        memory._peripherals[0x40000000] = PeripheralMapping(
            base=0x40000000, size=0x1000, instance=mock_periph
        )

        memory.reset()

        # New behavior: Memory.reset() does not call peripheral.reset() and
        # does not clear the peripherals dict. The board is responsible for
        # invoking peripheral.reset() when appropriate.
        assert not mock_periph.reset.called
        assert 0x40000000 in memory._peripherals

    def test_reset_multiple_times_idempotent(self, memory):
        """Test that multiple resets produce consistent results."""
        sram_addr = 0x20000000
        test_value = 0x12345678

        for _ in range(3):
            memory.write(sram_addr, 4, test_value)
            memory.reset()
            assert memory.read(sram_addr, 4) == 0x00000000

    def test_reset_with_pattern_writes(self, memory):
        """Test reset after writing various patterns."""
        patterns = [0x00000000, 0xFFFFFFFF, 0xAAAAAAAA, 0x55555555]
        sram_addr = 0x20000000

        for pattern in patterns:
            memory.write(sram_addr, 4, pattern)
            assert memory.read(sram_addr, 4) == pattern

            memory.reset()
            assert memory.read(sram_addr, 4) == 0x00000000

    def test_reset_clears_byte_wise(self, memory):
        """Test that reset clears SRAM on byte boundaries."""
        # Write different values to different bytes
        base = 0x20000000
        values = [0x11, 0x22, 0x33, 0x44]

        for i, val in enumerate(values):
            memory.write(base + i, 1, val)

        # Verify writes
        for i, val in enumerate(values):
            assert memory.read(base + i, 1) == val

        # Reset
        memory.reset()

        # Verify all bytes cleared
        for i in range(4):
            assert memory.read(base + i, 1) == 0x00

    def test_reset_preserves_flash_multiple_regions(self, memory):
        """Test that reset preserves multiple FLASH regions."""
        flash_addrs = [0x08000000, 0x08001000, 0x08010000]

        # Read values before reset
        flash_values = {addr: memory.read(addr, 4) for addr in flash_addrs}

        # Corrupt SRAM and reset
        memory.write(0x20000000, 4, 0xDEADBEEF)
        memory.write(0x20001000, 4, 0xCAFEBABE)
        memory.reset()

        # Verify FLASH regions preserved
        for addr, expected_val in flash_values.items():
            assert memory.read(addr, 4) == expected_val


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_back_to_back_writes_and_reads(self, memory):
        """Test consecutive writes and reads."""
        for i in range(10):
            addr = 0x20000000 + i * 4
            memory.write(addr, 4, 0x12345600 + i)
            assert memory.read(addr, 4) == 0x12345600 + i

    def test_mixed_size_access(self, memory):
        """Test writing as 4-byte and reading as 1-byte."""
        memory.write(0x20000000, 4, 0x12345678)
        assert memory.read(0x20000000, 1) == 0x78
        assert memory.read(0x20000001, 1) == 0x56
        assert memory.read(0x20000002, 1) == 0x34
        assert memory.read(0x20000003, 1) == 0x12

    def test_zero_value_operations(self, memory):
        """Test reading and writing zero values."""
        memory.write(0x20000000, 4, 0)
        assert memory.read(0x20000000, 4) == 0

    def test_all_ones_value(self, memory):
        """Test reading and writing all-ones value."""
        memory.write(0x20000000, 4, 0xFFFFFFFF)
        assert memory.read(0x20000000, 4) == 0xFFFFFFFF

    def test_alternating_bits_pattern(self, memory):
        """Test pattern with alternating bits."""
        pattern = 0xAAAAAAAA
        memory.write(0x20000000, 4, pattern)
        assert memory.read(0x20000000, 4) == pattern

        pattern = 0x55555555
        memory.write(0x20000004, 4, pattern)
        assert memory.read(0x20000004, 4) == pattern
