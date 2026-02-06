"""TM4C123 ARM Cortex-M4 CPU implementation."""

from __future__ import annotations

from typing import override

from simulator.interfaces.cpu import BaseCPU
from simulator.interfaces.memory import BaseMemory


class TM4C123_CPU(BaseCPU):
    """TM4C123 ARM Cortex-M4 processor simulation.

    Responsibilities:
    - Fetch instructions from memory
    - Execute ARM Thumb-2 instructions
    - Manage registers, PC, SP, etc.
    - Access memory via memory bus
    """

    def __init__(self, memory: BaseMemory) -> None:
        """Initialize CPU with memory bus.

        Args:
            memory: BaseMemory instance for instruction/data access
        """
        self._memory = memory

    @property
    @override
    def memory(self) -> BaseMemory:
        """Get the CPU's memory bus.

        Returns:
            BaseMemory instance provided during initialization
        """
        return self._memory

    @override
    def reset(self) -> None:
        """Reset CPU to power-on state.

        Sets all registers to 0, PC to RESET_VECTOR (0x08000000),
        PSP/MSP to top of SRAM.
        """
        # TODO: Implement CPU reset

    @override
    def step(self) -> None:
        """Execute one instruction cycle.

        Fetches instruction from PC, decodes, and executes.
        """
        # TODO: Implement instruction fetch/decode/execute cycle
