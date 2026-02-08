"""System control (SYSCTL/RCC) peripheral.

This is a minimal, config-driven peripheral that exposes a set of
memory-mapped control registers (e.g., TM4C RCGCGPIO, STM32 RCC_xxx).
It does not enforce semantics; it simply stores values and supports
reads/writes like real hardware register files.
"""

from __future__ import annotations

from simulator.core.peripheral import BasePeripheral
from simulator.core.register import RegisterFile, SimpleRegister
from simulator.utils.config_loader import SysCtlConfig


def _infer_size(registers: dict[str, int]) -> int:
    """Infer a safe peripheral size from register offsets.

    Align to 0x100 to avoid tiny ranges and to cover typical sysctl blocks.
    """
    if not registers:
        return 0x100
    max_offset = max(registers.values())
    size = max_offset + 4
    return ((size + 0xFF) // 0x100) * 0x100


class SysCtl(BasePeripheral):
    """Generic SYSCTL/RCC peripheral backed by a register file."""

    def __init__(self, cfg: SysCtlConfig, base_addr: int = 0, name: str | None = None):
        size = _infer_size(cfg.registers)
        super().__init__(name=name or "SYSCTL", size=size, base_addr=base_addr)
        self.cfg = cfg
        self._registers = RegisterFile()

        for _name, offset in cfg.registers.items():
            self._registers.add(SimpleRegister(offset, 4, 0))

    def read(self, offset: int, size: int) -> int:
        return self._registers.read(offset, size, default_reset=0)

    def write(self, offset: int, size: int, value: int) -> None:
        self._registers.write(offset, size, value)

    def reset(self) -> None:
        self._registers.reset()
