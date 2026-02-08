import pytest

from simulator.core.exceptions import (
    MemoryAccessError,
    MemoryAlignmentError,
    MemoryBoundsError,
    MemoryPermissionError,
    MemoryException,
    SimulatorError,
)


def test_memory_access_error_includes_address():
    exc = MemoryAccessError(0x20000000)
    assert isinstance(exc, MemoryException)
    assert "0x20000000" in str(exc)
    assert exc.details["address"] == "0x20000000"


def test_memory_permission_error_message_and_fields():
    exc = MemoryPermissionError(0x08000000, "write")
    assert isinstance(exc, SimulatorError)
    assert "cannot write" in str(exc)
    assert exc.operation == "write"


def test_memory_alignment_error_message():
    exc = MemoryAlignmentError(0x20000001, 4)
    assert "Unaligned" in str(exc)
    assert exc.size == 4


def test_memory_bounds_error_message():
    exc = MemoryBoundsError(0x20000010, 4, "SRAM")
    assert "Out-of-bounds" in str(exc)
    assert exc.region == "SRAM"
