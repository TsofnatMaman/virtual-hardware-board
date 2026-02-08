import pytest

from simulator.core import cpu as cpu_mod
from simulator.core.address_space import AddressRange, FlashMemory, PeripheralWindow, RamMemory, BitBandRegion
from simulator.core.memmap import AddressSpace


class DummyUc:
    def __init__(self):
        self.mem_maps = []
        self.mem_writes = []
        self.mem_reads = {}
        self.regs = {}
        self.hooks = []
        self.started = []

    def mem_map(self, base, size):
        self.mem_maps.append((base, size))

    def mem_write(self, base, data):
        self.mem_writes.append((base, data))

    def mem_read(self, base, size):
        return self.mem_reads.get((base, size), b"\x00" * size)

    def reg_write(self, reg, val):
        self.regs[reg] = val

    def reg_read(self, reg):
        return self.regs.get(reg, 0)

    def hook_add(self, flags, callback, begin, end):
        self.hooks.append((flags, callback, begin, end))

    def emu_start(self, pc, _end, count=1):
        self.started.append((pc, count))


class DummyEngine:
    def __init__(self):
        self.uc = DummyUc()

    def map_memory(self, base: int, size: int) -> None:
        self.uc.mem_map(base, size)

    def write_memory(self, base: int, data: bytes) -> None:
        self.uc.mem_write(base, data)

    def read_memory(self, base: int, size: int) -> bytes:
        return self.uc.mem_read(base, size)

    def set_register(self, reg_const: int, value: int) -> None:
        self.uc.reg_write(reg_const, value)

    def get_register(self, reg_const: int) -> int:
        return self.uc.reg_read(reg_const)

    def add_memory_hook(self, callback, begin: int, end: int) -> None:
        self.uc.hook_add(0, callback, begin, end)

    def step(self, pc: int) -> None:
        self.uc.emu_start(pc, 0xFFFFFFFF, count=1)


def _make_address_space() -> AddressSpace:
    flash = FlashMemory(AddressRange(0x08000000, 0x100))
    sram = RamMemory(AddressRange(0x20000000, 0x100))
    mmio = PeripheralWindow(AddressRange(0x40000000, 0x100))
    bitband = BitBandRegion(AddressRange(0x22000000, 0x20), AddressRange(0x20000000, 0x100), False)
    return AddressSpace(flash, sram, mmio, [bitband])


def _load_vector_table(addr_space: AddressSpace, msp: int, reset_vector: int) -> None:
    data = msp.to_bytes(4, "little") + reset_vector.to_bytes(4, "little")
    addr_space.flash.load_image(data)


def test_unicorn_engine_init_raises_when_unavailable(monkeypatch):
    monkeypatch.setattr(cpu_mod, "UNICORN_AVAILABLE", False)
    with pytest.raises(ImportError):
        cpu_mod.UnicornEngine()


def test_cpu_import_path_without_unicorn():
    import builtins
    import importlib
    import sys

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "unicorn" or name.startswith("unicorn."):
            raise ImportError("no unicorn")
        return original_import(name, *args, **kwargs)

    try:
        builtins.__import__ = fake_import
        sys.modules.pop("unicorn", None)
        sys.modules.pop("unicorn.arm_const", None)
        reloaded = importlib.reload(cpu_mod)
        assert reloaded.UNICORN_AVAILABLE is False
    finally:
        builtins.__import__ = original_import
        importlib.reload(cpu_mod)


def test_unicorn_engine_map_memory_aligns(monkeypatch):
    monkeypatch.setattr(cpu_mod, "UNICORN_AVAILABLE", True)
    monkeypatch.setattr(cpu_mod, "Uc", lambda *args, **kwargs: DummyUc())
    monkeypatch.setattr(cpu_mod, "UC_ARCH_ARM", 1)
    monkeypatch.setattr(cpu_mod, "UC_MODE_THUMB", 2)

    eng = cpu_mod.UnicornEngine()
    eng.map_memory(0x1000, 4097)
    base, size = eng.uc.mem_maps[0]
    assert base == 0x1000
    assert size == 8192

    eng.write_memory(0x2000, b"\xAA\xBB")
    assert eng.uc.mem_writes[-1] == (0x2000, b"\xAA\xBB")

    eng.uc.mem_reads[(0x3000, 2)] = b"\x11\x22"
    assert eng.read_memory(0x3000, 2) == b"\x11\x22"

    eng.set_register(1, 0x1234)
    assert eng.get_register(1) == 0x1234

    eng.add_memory_hook(lambda *_args: None, 0x4000, 0x5000)
    assert eng.uc.hooks

    eng.step(0x6000)
    assert eng.uc.started


def test_cortexm_reset_success():
    addr_space = _make_address_space()
    msp = addr_space.sram.base + 0x10
    reset_vector = addr_space.flash.base + 0x80 | 1
    _load_vector_table(addr_space, msp, reset_vector)

    engine = DummyEngine()
    cpu = cpu_mod.CortexM(engine, addr_space)
    cpu.reset()

    assert engine.uc.regs[cpu_mod.UC_ARM_REG_MSP] == msp
    assert engine.uc.regs[cpu_mod.UC_ARM_REG_SP] == msp
    assert engine.uc.regs[cpu_mod.UC_ARM_REG_PC] == (reset_vector & cpu_mod._PC_THUMB_MASK)


def test_cortexm_reset_invalid_msp_raises():
    addr_space = _make_address_space()
    msp = addr_space.sram.base - 4
    reset_vector = addr_space.flash.base + 0x80 | 1
    _load_vector_table(addr_space, msp, reset_vector)

    cpu = cpu_mod.CortexM(DummyEngine(), addr_space)
    with pytest.raises(RuntimeError):
        cpu.reset()


def test_cortexm_reset_invalid_reset_vector_raises():
    addr_space = _make_address_space()
    msp = addr_space.sram.base + 0x10
    reset_vector = addr_space.flash.base + 0x80  # Thumb bit not set
    _load_vector_table(addr_space, msp, reset_vector)

    cpu = cpu_mod.CortexM(DummyEngine(), addr_space)
    with pytest.raises(RuntimeError):
        cpu.reset()


def test_cortexm_get_set_register_and_invalid_index():
    cpu = cpu_mod.CortexM(DummyEngine(), _make_address_space())
    cpu.set_register(0, 0x1234)
    assert cpu.get_register(0) == 0x1234

    with pytest.raises(ValueError):
        cpu.get_register(16)

    with pytest.raises(ValueError):
        cpu.set_register(16, 0)


def test_cortexm_tick_and_handle_interrupt():
    cpu = cpu_mod.CortexM(DummyEngine(), _make_address_space())
    cpu.tick(2)
    assert cpu.engine.uc.started  # step called

    cpu.handle_interrupt(object())
    assert len(cpu._pending_interrupts) == 1


def test_cortexm_step_error_propagates():
    class FailingEngine(DummyEngine):
        def step(self, pc: int) -> None:
            raise RuntimeError("boom")

    cpu = cpu_mod.CortexM(FailingEngine(), _make_address_space())
    with pytest.raises(RuntimeError):
        cpu.step()


def test_memory_hook_read_and_write(monkeypatch):
    addr_space = _make_address_space()
    addr_space.sram.write(addr_space.sram.base, 4, 0xAABBCCDD)
    cpu = cpu_mod.CortexM(DummyEngine(), addr_space)

    monkeypatch.setattr(cpu_mod, "UC_MEM_READ", 1)
    monkeypatch.setattr(cpu_mod, "UC_MEM_WRITE", 2)

    class DummyUcMem:
        def __init__(self):
            self.writes = []

        def mem_write(self, addr, data):
            self.writes.append((addr, data))

    uc = DummyUcMem()

    cpu._memory_hook(uc, 1, addr_space.sram.base, 4, 0, None)
    assert uc.writes

    cpu._memory_hook(uc, 2, addr_space.sram.base, 4, 0x11223344, None)
    assert addr_space.read(addr_space.sram.base, 4) == 0x11223344


def test_memory_hook_error_raises(monkeypatch):
    addr_space = _make_address_space()
    cpu = cpu_mod.CortexM(DummyEngine(), addr_space)

    monkeypatch.setattr(cpu_mod, "UC_MEM_READ", 1)

    class DummyUcMem:
        def mem_write(self, addr, data):
            pass

    with pytest.raises(Exception):
        cpu._memory_hook(DummyUcMem(), 1, 0xDEADBEEF, 4, 0, None)
