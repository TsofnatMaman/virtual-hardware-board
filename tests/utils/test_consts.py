from simulator.utils.consts import ConstUtils, align_to_page


def test_const_utils_masks():
    assert ConstUtils.MASK_8_BITS == 0xFF
    assert ConstUtils.MASK_16_BITS == 0xFFFF
    assert ConstUtils.MASK_32_BITS == 0xFFFFFFFF


def test_align_to_page_rounds_up():
    assert align_to_page(4096) == 4096
    assert align_to_page(4097) == 8192
    assert align_to_page(1) == 4096
