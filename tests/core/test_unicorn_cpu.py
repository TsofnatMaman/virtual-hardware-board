import types

from simulator.core import unicorn_cpu as ucmod
from simulator.interfaces.cpu import BaseCPU
from simulator.utils.config_loader import Memory_Config


class FakeUc:
    def __init__(self, arch, mode):
        self.arch = arch
        self.mode = mode
        self.mapped = []
        self.hooks = []
        self.mem = {}
        self.regs = {}

    def mem_map(self, base, size):
        self.mapped.append((base, size))

    def hook_add(self, flags, callback, begin=None, end=None):
        # store callback for inspection
        self.hooks.append((flags, callback, begin, end))

    def mem_write(self, addr, data):
        # store as bytes
        self.mem[addr] = bytes(data)

    def mem_read(self, addr, size):
        return self.mem.get(addr, b"\x00" * size)

    def reg_write(self, reg_const, value):
        self.regs[reg_const] = value

    def reg_read(self, reg_const):
        return self.regs.get(reg_const, 0)

    def emu_start(self, pc, end, count=0):
        # no-op for tests
        return


class FakeMemory:
    def __init__(self, cfg: Memory_Config, sp: int, reset_vector: int, firmware: bytes = b""):
        self.memory_config = cfg
        # read_block should return firmware bytes
        self._firmware = firmware or (sp.to_bytes(4, "little") + reset_vector.to_bytes(4, "little"))
        self.read_calls = []

    def read_block(self, address: int, size: int) -> bytes:
        # return at least requested size
        return self._firmware.ljust(size, b"\x00")[:size]

    def read(self, address: int, size: int) -> int:
        # emulate reading initial sp and reset vector from flash
        # address == flash_base -> return first 4 bytes; flash_base+4 -> next 4
        self.read_calls.append((address, size))
        offset = 0 if address == self.memory_config.flash_base else 4 if address == self.memory_config.flash_base + 4 else None
        if offset is None:
            return 0
        return int.from_bytes(self._firmware[offset:offset+4], "little")


class TestUnicornCPU:
    def test_reset_core_writes_firmware_and_sets_registers(self, monkeypatch):
        # Prepare fake Uc and patch module
        monkeypatch.setattr(ucmod, "Uc", FakeUc)

        # Create a Memory_Config
        cfg = Memory_Config(
            flash_base=0x08000000,
            flash_size=64,
            sram_base=0x20000000,
            sram_size=0x1000,
            periph_base=0x40000000,
            periph_size=0x100000,
            bitband_base=0x42000000,
            bitband_size=0x2000000,
        )

        initial_sp = 0x20001000
        reset_vector = 0x08000100

        mem = FakeMemory(cfg, initial_sp, reset_vector)

        # Create a small concrete CPU subclass to implement abstract reset
        class TestCPU(ucmod.BaseCortexM_CPU):
            def reset(self):
                # call reset_core using current config
                self.reset_core(cfg.flash_base, cfg.flash_size)

        cpu = TestCPU(mem)

        # Call reset which triggers reset_core
        cpu.reset()

        # The underlying FakeUc instance should have MSP, SP, PC written
        # Use the constants from ucmod to verify
        msp = ucmod.UC_ARM_REG_MSP
        sp = ucmod.UC_ARM_REG_SP
        pc = ucmod.UC_ARM_REG_PC

        assert cpu._uc.regs.get(msp) == initial_sp
        assert cpu._uc.regs.get(sp) == initial_sp
        # PC should have least significant bit cleared
        assert cpu._uc.regs.get(pc) == (reset_vector & 0xFFFFFFFE)

        # Verify that firmware bytes were written into unicorn memory at flash_base
        assert cfg.flash_base in cpu._uc.mem

    def test_mmio_hook_read_calls_memory_and_writes_back(self, monkeypatch):
        # Patch Uc
        monkeypatch.setattr(ucmod, "Uc", FakeUc)

        cfg = Memory_Config(
            flash_base=0x08000000,
            flash_size=64,
            sram_base=0x20000000,
            sram_size=0x1000,
            periph_base=0x40000000,
            periph_size=0x100000,
            bitband_base=0x42000000,
            bitband_size=0x2000000,
        )

        # memory that returns a known value for a peripheral read
        class MemForMMIO(FakeMemory):
            def read(self, address: int, size: int) -> int:
                if address == cfg.periph_base:
                    return 0xA5A5A5A5
                return super().read(address, size)

        mem = MemForMMIO(cfg, 0, 0)

        class TestCPU(ucmod.BaseCortexM_CPU):
            def reset(self):
                pass

        cpu = TestCPU(mem)

        # create fake uc to pass to hook
        fake_uc = cpu._uc

        # Call mmio hook for read
        ucmod.UC_MEM_READ  # ensure constant exists
        cpu._mmio_hook(fake_uc, ucmod.UC_MEM_READ, cfg.periph_base, 4, 0, None)

        # FakeUc.mem should have been written at the peripheral address
        written = fake_uc.mem.get(cfg.periph_base)
        assert written == (0xA5A5A5A5).to_bytes(4, "little")
