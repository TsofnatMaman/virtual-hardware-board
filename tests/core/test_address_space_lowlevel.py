import pytest

from simulator.core.address_space import (
    AddressRange,
    BitBandRegion,
    FlashMemory,
    PeripheralWindow,
    RamMemory,
)
from simulator.core.exceptions import MemoryAccessError, MemoryBoundsError


def test_address_range_contains_and_str():
    ar = AddressRange(base=0x1000, size=0x100)
    assert ar.contains(0x1000) is True
    assert ar.contains(0x10FF) is True
    assert ar.contains(0x1100) is False
    assert ar.contains_range(0x1000, 0x100) is True
    assert ar.contains_range(0x10FF, 2) is False
    assert str(ar) == "0x00001000-0x00001100"


def test_flash_memory_load_read_and_bounds():
    flash = FlashMemory(AddressRange(0x08000000, 16))
    flash.load_image(b"\x01\x02\x03\x04")
    assert flash.read(0x08000000, 4) == 0x04030201

    with pytest.raises(ValueError):
        flash.load_image(b"\x00" * 32)

    with pytest.raises(MemoryBoundsError):
        flash.read(0x08000010, 4)

    with pytest.raises(MemoryAccessError):
        flash.write(0x08000000, 4, 0xDEAD)

    # reset is a no-op but should be callable
    flash.reset()


def test_flash_memory_read_block_bounds():
    flash = FlashMemory(AddressRange(0x08000000, 8))
    flash.load_image(b"\xAA\xBB\xCC\xDD\x00\x00\x00\x00")
    assert flash.read_block(0x08000000, 4) == b"\xAA\xBB\xCC\xDD"

    with pytest.raises(MemoryBoundsError):
        flash.read_block(0x08000006, 4)


def test_ram_memory_read_write_reset_and_bounds():
    ram = RamMemory(AddressRange(0x20000000, 8))
    ram.write(0x20000000, 4, 0x12345678)
    assert ram.read(0x20000000, 4) == 0x12345678
    assert ram.read_block(0x20000000, 4) == b"\x78\x56\x34\x12"

    with pytest.raises(MemoryBoundsError):
        ram.write(0x20000008, 1, 0xFF)
    with pytest.raises(MemoryBoundsError):
        ram.read(0x20000008, 1)
    with pytest.raises(MemoryBoundsError):
        ram.read_block(0x20000006, 4)

    ram.reset()
    assert ram.read(0x20000000, 4) == 0


def test_bitband_translate_and_errors():
    alias = AddressRange(0x22000000, 0x20)
    target = AddressRange(0x20000000, 0x10)
    bb = BitBandRegion(alias, target, target_is_peripheral=False)

    target_addr, bit_idx = bb.translate(0x22000000)
    assert target_addr == 0x20000000
    assert bit_idx == 0

    with pytest.raises(MemoryBoundsError):
        bb.translate(0x22000040)

    # Alias maps beyond target
    alias2 = AddressRange(0x22000000, 0x40)
    target2 = AddressRange(0x20000000, 0x04)
    bb2 = BitBandRegion(alias2, target2, target_is_peripheral=False)
    with pytest.raises(MemoryBoundsError):
        bb2.translate(0x22000020)


def test_bitband_and_peripheral_window_read_write_raise():
    bb = BitBandRegion(AddressRange(0x22000000, 0x20), AddressRange(0x20000000, 0x20), False)
    with pytest.raises(RuntimeError):
        bb.read(0x22000000, 4)
    with pytest.raises(RuntimeError):
        bb.write(0x22000000, 4, 1)
    bb.reset()

    mmio = PeripheralWindow(AddressRange(0x40000000, 0x100))
    with pytest.raises(RuntimeError):
        mmio.read(0x40000000, 4)
    with pytest.raises(RuntimeError):
        mmio.write(0x40000000, 4, 0x1)
    mmio.reset()
