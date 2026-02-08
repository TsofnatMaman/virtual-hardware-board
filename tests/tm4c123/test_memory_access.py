import pytest

from simulator.tm4c.memory_access import TM4C123BitBandedAccessModel


def test_tm4c_bitband_access_decode_encode():
    base = 0x40004000
    model = TM4C123BitBandedAccessModel(base, num_pins=8)

    assert model.decode_register_access(base + 0x004, 4) == ("DATA_MASKED", 0x004)
    assert model.decode_register_access(base + 0x400, 4) == ("DIR", 0x400)
    assert model.decode_register_access(base - 4, 4) is None
    assert model.decode_register_access(base + 0x430, 4) is None

    assert model.encode_register_address("DATA") == base + 0x3FC
    assert model.encode_register_address("AFSEL") == base + 0x420

    with pytest.raises(ValueError):
        model.encode_register_address("UNKNOWN")


def test_tm4c_bitband_description_includes_base():
    base = 0x40004000
    model = TM4C123BitBandedAccessModel(base, num_pins=8)
    desc = model.description
    assert "TM4C123 Bit-Banded GPIO Addressing" in desc
    assert f"0x{base:08X}" in desc
