from simulator.core.builders import (
    create_address_space_from_config,
    create_cpu_for_address_space,
)
from simulator.core.memmap import AddressSpace
from simulator.utils.config_loader import load_config


class DummyEngine:
    def __init__(self):
        self.mapped = []
        self.hook_args = None

    def map_memory(self, base: int, size: int) -> None:
        self.mapped.append((base, size))

    def add_memory_hook(self, callback, begin: int, end: int) -> None:
        self.hook_args = (callback, begin, end)


def test_create_address_space_from_config():
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)
    assert isinstance(addr_space, AddressSpace)
    assert len(addr_space.bitband_regions) == 2


def test_create_cpu_for_address_space(monkeypatch):
    cfg = load_config("stm32f4", path="simulator/stm32/config.yaml")
    addr_space = create_address_space_from_config(cfg.memory)

    dummy_engine = DummyEngine()

    def dummy_engine_factory():
        return dummy_engine

    monkeypatch.setattr("simulator.core.builders.UnicornEngine", dummy_engine_factory)

    cpu = create_cpu_for_address_space(addr_space)

    # Ensure memory mapped for flash/sram/mmio
    assert (addr_space.flash.base, addr_space.flash.size) in dummy_engine.mapped
    assert (addr_space.sram.base, addr_space.sram.size) in dummy_engine.mapped
    assert (addr_space.mmio.base, addr_space.mmio.size) in dummy_engine.mapped

    # Hook registered over MMIO range
    _, begin, end = dummy_engine.hook_args
    assert begin == addr_space.mmio.base
    assert end == addr_space.mmio.base + addr_space.mmio.size

    # CPU instance returned
    assert cpu.address_space is addr_space
