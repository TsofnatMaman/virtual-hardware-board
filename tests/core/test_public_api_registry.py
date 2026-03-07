import simulator

EXPECTED_BOARDS = {"stm32f4", "stm32c031", "tm4c123"}


def test_simulator_import_registers_boards():
    boards = set(simulator.list_available_boards())
    assert EXPECTED_BOARDS.issubset(boards)  # nosec B101


def test_create_board_from_public_api():
    board = simulator.create_board("tm4c123")
    assert board.name == "TM4C123"  # nosec B101
