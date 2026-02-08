import pytest

from simulator.core.builders import create_address_space_from_config
from simulator.core.memmap import BaseMemoryMap
from simulator.core.exceptions import MemoryAccessError, MemoryBoundsError
from simulator.utils.config_loader import load_config


class DummyPeripheral:
    def __init__(self):
        self.reset_called = False
        self.writes = []

    def read(self, offset: int, size: int) -> int:
        return 0x42

    def write(self, offset: int, size: int, value: int) -> None:
        self.writes.append((offset, size, value))

    def reset(self) -> None:
        self.reset_called = True


def test_address_space_regions_and_resolve():
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)

    assert isinstance(addr_space, BaseMemoryMap)
    regions = addr_space.regions
    assert addr_space.flash in regions
    assert addr_space.sram in regions
    assert addr_space.mmio in regions
    assert len(addr_space.bitband_regions) == 2

    assert addr_space.resolve_region(cfg.memory.flash_base) is addr_space.flash
    assert addr_space.resolve_region(cfg.memory.sram_base) is addr_space.sram
    assert addr_space.resolve_region(cfg.memory.periph_base) is addr_space.mmio

    alias_region = addr_space.resolve_region(cfg.memory.bitband_sram_base)
    assert alias_region in addr_space.bitband_regions


def test_address_space_mmio_dispatch_and_reset():
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)

    periph = DummyPeripheral()
    base = cfg.memory.periph_base
    size = 0x100
    addr_space.register_peripheral(base, size, periph)

    assert addr_space.read(base, 4) == 0x42
    addr_space.write(base + 4, 4, 0x1234)
    assert periph.writes == [(4, 4, 0x1234)]

    addr_space.reset()
    assert periph.reset_called is True


def test_address_space_mmio_missing_peripheral_raises():
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)

    with pytest.raises(MemoryAccessError):
        addr_space.read(cfg.memory.periph_base, 4)


def test_address_space_register_peripheral_out_of_bounds():
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)

    periph = DummyPeripheral()
    bad_base = cfg.memory.periph_base - 0x100

    with pytest.raises(MemoryBoundsError):
        addr_space.register_peripheral(bad_base, 0x80, periph)


def test_address_space_register_peripheral_overlap():
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)

    periph_a = DummyPeripheral()
    periph_b = DummyPeripheral()
    base = cfg.memory.periph_base + 0x100

    addr_space.register_peripheral(base, 0x100, periph_a)

    with pytest.raises(ValueError):
        addr_space.register_peripheral(base + 0x80, 0x100, periph_b)


def test_address_space_bitband_sram_read_write():
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)

    target_addr = cfg.memory.sram_base + 0x20
    addr_space.write(target_addr, 4, 0)

    bit_index = 5
    word_offset = (target_addr - cfg.memory.sram_base) // 4
    alias_addr = cfg.memory.bitband_sram_base + (word_offset * 32) + (bit_index * 4)
    addr_space.write(alias_addr, 4, 1)

    word = addr_space.read(target_addr, 4)
    assert (word >> bit_index) & 1 == 1
    assert addr_space.read(alias_addr, 4) == 1
