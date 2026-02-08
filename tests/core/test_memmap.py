import pytest

from simulator.core.address_space import AddressRange, BitBandRegion, FlashMemory, PeripheralWindow, RamMemory
from simulator.core.exceptions import MemoryAccessError, MemoryAlignmentError
from simulator.core.memmap import AddressSpace


class DummyPeripheral:
    def __init__(self):
        self.word = 0
        self.writes = []

    def read(self, offset: int, size: int) -> int:
        return self.word

    def write(self, offset: int, size: int, value: int) -> None:
        self.writes.append((offset, size, value))
        self.word = value

    def reset(self) -> None:
        self.word = 0


def _make_address_space() -> AddressSpace:
    flash = FlashMemory(AddressRange(0x00000000, 0x100))
    sram = RamMemory(AddressRange(0x20000000, 0x100))
    mmio = PeripheralWindow(AddressRange(0x40000000, 0x100))
    bitband = BitBandRegion(
        AddressRange(0x22000000, 0x200),
        AddressRange(0x20000000, 0x100),
        target_is_peripheral=False,
    )
    bitband_periph = BitBandRegion(
        AddressRange(0x42000000, 0x200),
        AddressRange(0x40000000, 0x100),
        target_is_peripheral=True,
    )
    return AddressSpace(flash, sram, mmio, [bitband, bitband_periph])


def test_validate_access_size_and_alignment():
    addr_space = _make_address_space()
    with pytest.raises(MemoryAccessError):
        addr_space.read(0x20000000, 3)
    with pytest.raises(MemoryAlignmentError):
        addr_space.read(0x20000001, 4)


def test_flash_read_and_write_error():
    addr_space = _make_address_space()
    addr_space.flash.load_image(b"\x01\x02\x03\x04")
    assert addr_space.read(0x00000000, 4) == 0x04030201
    with pytest.raises(MemoryAccessError):
        addr_space.write(0x00000000, 4, 0x1234)


def test_sram_read_write_and_read_block():
    addr_space = _make_address_space()
    addr_space.write(0x20000000, 4, 0xDEADBEEF)
    assert addr_space.read(0x20000000, 4) == 0xDEADBEEF
    assert addr_space.read_block(0x20000000, 4) == b"\xEF\xBE\xAD\xDE"


def test_read_block_invalid_region_raises():
    addr_space = _make_address_space()
    with pytest.raises(MemoryAccessError):
        addr_space.read_block(0x40000000, 4)


def test_mmio_missing_peripheral_raises():
    addr_space = _make_address_space()
    with pytest.raises(MemoryAccessError):
        addr_space.read(0x40000000, 4)
    with pytest.raises(MemoryAccessError):
        addr_space.write(0x40000000, 4, 0x1)


def test_register_peripheral_invalid_size():
    addr_space = _make_address_space()
    with pytest.raises(ValueError):
        addr_space.register_peripheral(0x40000000, 0, DummyPeripheral())


def test_bitband_peripheral_read_write():
    addr_space = _make_address_space()
    periph = DummyPeripheral()
    addr_space.register_peripheral(0x40000000, 0x100, periph)

    # Set underlying word then read bit 3 via bitband
    periph.word = 0b1000
    alias_addr = 0x42000000 + (0x00 * 32) + (3 * 4)
    assert addr_space.read(alias_addr, 4) == 1

    # Write bit 1 via bitband
    alias_addr = 0x42000000 + (0x00 * 32) + (1 * 4)
    addr_space.write(alias_addr, 4, 1)
    assert periph.word & (1 << 1)

    # Clear bit via bitband
    addr_space.write(alias_addr, 4, 0)
    assert (periph.word & (1 << 1)) == 0


def test_bitband_peripheral_missing_mapping_raises():
    addr_space = _make_address_space()
    alias_addr = 0x42000000 + (0x00 * 32) + (1 * 4)
    with pytest.raises(MemoryAccessError):
        addr_space.read(alias_addr, 4)
    with pytest.raises(MemoryAccessError):
        addr_space.write(alias_addr, 4, 1)


def test_bitband_invalid_access_size():
    addr_space = _make_address_space()
    alias_addr = 0x22000000 + (0x00 * 32) + (1 * 4)
    with pytest.raises(MemoryAccessError):
        addr_space.read(alias_addr, 2)
    with pytest.raises(MemoryAccessError):
        addr_space.write(alias_addr, 2, 1)


def test_read_write_address_not_mapped():
    addr_space = _make_address_space()
    with pytest.raises(MemoryAccessError):
        addr_space.read(0x60000000, 4)
    with pytest.raises(MemoryAccessError):
        addr_space.write(0x60000000, 4, 0x1)


def test_find_peripheral_no_match_and_resolve_none():
    addr_space = _make_address_space()
    periph = DummyPeripheral()
    addr_space.register_peripheral(0x40000000, 0x10, periph)
    assert addr_space.find_peripheral(0x40000020) is None
    assert addr_space.resolve_region(0x60000000) is None


def test_register_peripheral_overlap_with_next():
    addr_space = _make_address_space()
    periph_a = DummyPeripheral()
    periph_b = DummyPeripheral()
    addr_space.register_peripheral(0x40000080, 0x10, periph_a)
    with pytest.raises(ValueError):
        addr_space.register_peripheral(0x40000000, 0x100, periph_b)


def test_flash_write_path_return_line():
    class WritableFlash(FlashMemory):
        def write(self, address: int, size: int, value: int) -> None:
            # Allow writes for testing the return path
            self._data[address - self.base:address - self.base + size] = value.to_bytes(size, "little")

    flash = WritableFlash(AddressRange(0x00000000, 0x100))
    sram = RamMemory(AddressRange(0x20000000, 0x100))
    mmio = PeripheralWindow(AddressRange(0x40000000, 0x100))
    bitband = BitBandRegion(AddressRange(0x22000000, 0x20), AddressRange(0x20000000, 0x100), False)
    addr_space = AddressSpace(flash, sram, mmio, [bitband])

    addr_space.write(0x00000000, 4, 0xAABBCCDD)
    assert addr_space.read(0x00000000, 4) == 0xAABBCCDD


def test_get_memory_map_includes_peripherals():
    addr_space = _make_address_space()
    periph = DummyPeripheral()
    addr_space.register_peripheral(0x40000000, 0x100, periph)
    layout = addr_space.get_memory_map()
    assert layout["peripherals"]
