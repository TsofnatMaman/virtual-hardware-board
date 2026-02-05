from interfaces.board import BaseBoard


class TM4C123_Board(BaseBoard):
    """
    TM4C123 (Tiva C) board implementation.

    Responsibilities:
    - Owns and initializes memory + peripherals
    - Aggresgates interrupt signals
    - Exposes board state in a GUI-agnostic form
    """

    # Board memory characteristics (used by CPU / loader validation)
    # FLASH_BASE: int = consts.FLASH_BASE
