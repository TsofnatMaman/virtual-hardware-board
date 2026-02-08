import pytest

from simulator.stm32.memory_access import STM32F4DirectAccessModel


def test_stm32_direct_access_decode_encode():
    base = 0x40020000
    model = STM32F4DirectAccessModel(base)

    decoded = model.decode_register_access(base + 0x14, 4)
    assert decoded == ("ODR", 0x14)

    assert model.decode_register_access(base - 4, 4) is None
    assert model.encode_register_address("ODR") == base + 0x14

    with pytest.raises(ValueError):
        model.encode_register_address("UNKNOWN")


def test_stm32_direct_access_description_includes_base():
    base = 0x40020000
    model = STM32F4DirectAccessModel(base)
    desc = model.description
    assert "STM32F4 Direct Register Offset Mapping" in desc
    assert f"0x{base:08X}" in desc
