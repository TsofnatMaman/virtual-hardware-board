"""Memory map interface for board address spaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.core.address_space import MemoryRegion


class IMemoryMap(ABC):
    """Interface for address space routing."""

    @abstractmethod
    def read(self, address: int, size: int) -> int:
        """Read from the memory map."""
        ...

    @abstractmethod
    def write(self, address: int, size: int, value: int) -> None:
        """Write to the memory map."""
        ...

    @abstractmethod
    def resolve_region(self, address: int) -> "MemoryRegion | None":
        """Resolve which region contains the given address."""
        ...

    @property
    @abstractmethod
    def regions(self) -> list["MemoryRegion"]:
        """Return all regions in this memory map."""
        ...
