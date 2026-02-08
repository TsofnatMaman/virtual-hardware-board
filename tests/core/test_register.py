import pytest

from simulator.core.register import (
    ReadOnlyRegister,
    RegisterDescriptor,
    RegisterFile,
    SimpleRegister,
    WriteOnlyRegister,
)


def test_register_descriptor_fields():
    desc = RegisterDescriptor(
        offset=0x10,
        name="ODR",
        width=4,
        read_only=False,
        write_only=False,
        reset_value=0x1234,
        side_effects_on_read=True,
        side_effects_on_write=True,
    )
    assert desc.offset == 0x10
    assert desc.name == "ODR"
    assert desc.width == 4
    assert desc.reset_value == 0x1234
    assert desc.side_effects_on_read is True


def test_simple_register_read_write_and_reset():
    reg = SimpleRegister(offset=0x00, width=4, reset_value=0x12345678)
    assert reg.read(4) == 0x12345678
    assert reg.read(1) == 0x78

    reg.write(1, 0xAB)
    assert reg.read(4) == 0x123456AB

    reg.reset()
    assert reg.read(4) == 0x12345678


def test_read_only_register_ignores_writes():
    reg = ReadOnlyRegister(offset=0x04, width=4, reset_value=0xAAAA)
    reg.write(4, 0x1234)
    assert reg.read(4) == 0xAAAA


def test_write_only_register_reads_reset_value():
    reg = WriteOnlyRegister(offset=0x08, width=4, reset_value=0x1111)
    reg.write(4, 0x2222)
    assert reg.read(4) == 0x1111


def test_register_file_add_duplicate_and_defaults():
    rf = RegisterFile()
    reg = SimpleRegister(offset=0x00, width=4, reset_value=0x0)
    rf.add(reg)

    with pytest.raises(ValueError):
        rf.add(SimpleRegister(offset=0x00, width=4, reset_value=0x0))

    # Read missing offset returns default_reset masked
    assert rf.read(0x10, 1, default_reset=0xFF) == 0xFF


def test_register_file_write_unknown_is_ignored():
    rf = RegisterFile()
    reg = SimpleRegister(offset=0x00, width=4, reset_value=0x0)
    rf.add(reg)

    rf.write(0x10, 4, 0xDEAD)
    assert reg.read(4) == 0x0


def test_register_file_reset_and_get_register():
    rf = RegisterFile()
    reg = SimpleRegister(offset=0x00, width=4, reset_value=0xA5A5)
    rf.add(reg)
    reg.write(4, 0x0000)

    rf.reset()
    assert reg.read(4) == 0xA5A5
    assert rf.get_register(0x00) is reg
    assert rf.get_register(0x10) is None


def test_register_file_invalid_access_size():
    rf = RegisterFile()
    with pytest.raises(ValueError):
        rf.read(0x00, 3)
