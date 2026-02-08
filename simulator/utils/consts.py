"""Constants and utility values for the simulator."""


class ConstUtils:
    """Bitwise masks and register constants."""

    # Bitwise masks for different data widths
    MASK_8_BITS = 0xFF
    """8-bit mask: 0xFF"""

    MASK_16_BITS = 0xFFFF
    """16-bit mask: 0xFFFF"""

    MASK_32_BITS = 0xFFFFFFFF
    """32-bit mask: 0xFFFFFFFF"""

    # Tiva-C (TM4C123) specific constants
    DATA_MASKED_MAX_OFFSET = 0x3FC
    """Maximum offset for masked DATA register access on Tiva-C (TM4C123).
    Tiva-C supports masked read/write on DATA using offsets 0x004–0x3FC."""

    # Unicorn Engine page alignment (required for mem_map)
    UNICORN_PAGE_SIZE = 4096
    """Minimum alignment for Unicorn mem_map size (4 KiB)."""


# GPIO port sizes (per-port register block, MCU-specific)
STM32_GPIO_PORT_SIZE = 0x400
TM4C123_GPIO_PORT_SIZE = 0x1000


def align_to_page(size: int) -> int:
    """Round size up to Unicorn mem_map page boundary (4 KiB).

    Unicorn Engine requires mem_map size to be a multiple of 4096 bytes.
    Use this for flash_size and sram_size when calling mem_map.
    """
    page = ConstUtils.UNICORN_PAGE_SIZE
    return ((size + page - 1) // page) * page

