"""The one generic board class, exercised through every board that is built on it."""

from dataclasses import replace

import pytest

import simulator
from simulator.core.board import create_board, list_available_boards
from simulator.core.configured_board import BoardSpec, ConfiguredBoard
from simulator.interfaces.memory_access import MemoryAccessModel

BOARDS = {  # key -> (name, kind of GPIO config it declares)
    "tm4c123": ("TM4C123", "tm4c123"),
    "stm32f4": ("STM32F4", "stm32"),
    "stm32c031": ("STM32C031", "stm32"),
}
OTHER_KIND = {"tm4c123": "stm32", "stm32": "tm4c123"}


class DummyCPU:
    def __init__(self):
        self.reset_called = False
        self.ticks = []

    def reset(self) -> None:
        self.reset_called = True

    def tick(self, cycles: int = 1) -> None:
        self.ticks.append(cycles)

    def handle_interrupt(self, event) -> None:  # called by the interrupt controller
        pass


@pytest.fixture(name="dummy_cpu")
def fixture_dummy_cpu(monkeypatch):
    cpu = DummyCPU()
    monkeypatch.setattr(
        "simulator.core.configured_board.create_cpu_for_address_space", lambda _a: cpu
    )
    return cpu


def test_every_registered_board_is_a_configured_board():
    keys = set(list_available_boards())
    assert keys == set(BOARDS)
    for key in keys:
        board_class = type(create_board(key))
        assert issubclass(board_class, ConfiguredBoard)
        assert board_class.spec.key == key
        assert board_class.spec.config_path.is_file()


@pytest.mark.parametrize("key", BOARDS)
class TestEachBoard:
    def test_name_wiring_and_stepping(self, key, dummy_cpu):
        board = create_board(key)
        assert board.name == BOARDS[key][0]
        assert board.cpu is dummy_cpu
        assert board.memory_map is board.address_space
        assert isinstance(board.memory_access_model, MemoryAccessModel)
        assert {"SYSCTL", "GPIO_A"} <= set(board.peripherals)
        board.step(4)
        assert dummy_cpu.ticks == [4] and board.clock.cycle_count == 4
        periph = next(iter(board.peripherals.values()))
        assert periph._interrupt_controller is board.interrupt_ctrl

    def test_one_gpio_peripheral_per_configured_port(self, key, dummy_cpu):
        board = create_board(key)
        ports = board.config.gpio.ports
        gpios = {n for n in board.peripherals if n.startswith("GPIO_")}
        assert gpios == {f"GPIO_{p}" for p in ports}

    def test_memory_reads_writes_and_reset(self, key, dummy_cpu):
        board = create_board(key)
        sram = board.address_space.sram.base
        board.write(sram, 4, 0x12345678)
        assert board.read(sram, 4) == 0x12345678
        board.interrupt_ctrl.notify(next(iter(board.peripherals.values())), vector=3)
        assert board.interrupt_ctrl._pending
        board.step(2)
        board.reset()
        assert dummy_cpu.reset_called and board.clock.cycle_count == 0
        assert board.interrupt_ctrl._pending == []

    def test_empty_pin_masks_are_rejected(self, key, dummy_cpu):
        board = create_board(key)
        board.config = replace(
            board.config, pins=replace(board.config.pins, pin_masks={})
        )
        with pytest.raises(ValueError, match="pin mask is empty"):
            board._pin_data_mask()

    def test_a_config_for_another_gpio_family_is_rejected(self, key, dummy_cpu):
        board = create_board(key)
        wrong = replace(board.config.gpio, kind=OTHER_KIND[BOARDS[key][1]])
        board.config = replace(board.config, gpio=wrong)
        with pytest.raises(ValueError, match="Expected"):
            board._init_gpio()


def test_a_new_board_is_just_a_spec(dummy_cpu):
    """No board code beyond the spec: reuse an existing config and GPIO model."""
    base = type(create_board("stm32f4")).spec

    class Clone(ConfiguredBoard):
        spec = BoardSpec(**{**base.__dict__, "key": "stm32f4", "name": "CLONE"})

    board = Clone()
    assert board.name == "CLONE" and "GPIO_A" in board.peripherals


def test_the_public_api_still_exports_the_board_classes():
    assert {"TM4C123Board", "STM32F4Board", "STM32C031Board"} <= set(simulator.__all__)
