from dataclasses import replace

import pytest

from simulator.stm32c031.board import STM32C031Board


class DummyCPU:
    def __init__(self):
        self.reset_called = False
        self.ticks = []
        self.interrupts = []

    def reset(self) -> None:
        self.reset_called = True

    def tick(self, cycles: int = 1) -> None:
        self.ticks.append(cycles)

    def handle_interrupt(self, event) -> None:
        self.interrupts.append(event)


def test_stm32c031_board_wiring_and_step(monkeypatch):
    dummy_cpu = DummyCPU()
    monkeypatch.setattr(
        "simulator.stm32c031.board.create_cpu_for_address_space",
        lambda _addr: dummy_cpu,
    )

    board = STM32C031Board()
    assert board.name == "STM32C031"
    assert board.cpu is dummy_cpu
    assert board.peripherals
    assert board.memory_map is board.address_space
    assert board.memory_access_model is not None

    board.step(4)
    assert dummy_cpu.ticks == [4]
    assert board.clock.cycle_count == 4

    periph = next(iter(board.peripherals.values()))
    assert getattr(periph, "_interrupt_controller", None) is board.interrupt_ctrl


def test_stm32c031_board_pin_mask_and_gpio_kind_errors(monkeypatch):
    dummy_cpu = DummyCPU()
    monkeypatch.setattr(
        "simulator.stm32c031.board.create_cpu_for_address_space",
        lambda _addr: dummy_cpu,
    )
    board = STM32C031Board()

    empty_pins = replace(board.config.pins, pin_masks={})
    board.config = replace(board.config, pins=empty_pins)
    with pytest.raises(ValueError):
        board._pin_data_mask()

    bad_gpio = replace(board.config.gpio, kind="tm4c123")
    board.config = replace(board.config, gpio=bad_gpio)
    with pytest.raises(ValueError):
        board._init_gpio()


def test_stm32c031_board_read_write_and_reset(monkeypatch):
    dummy_cpu = DummyCPU()
    monkeypatch.setattr(
        "simulator.stm32c031.board.create_cpu_for_address_space",
        lambda _addr: dummy_cpu,
    )

    board = STM32C031Board()
    addr = board.address_space.sram.base
    board.write(addr, 4, 0x12345678)
    assert board.read(addr, 4) == 0x12345678

    periph = next(iter(board.peripherals.values()))
    board.interrupt_ctrl.notify(periph, vector=3)
    assert board.interrupt_ctrl._pending

    flags = {"addr_reset": False}
    board._address_space.reset = lambda: flags.__setitem__("addr_reset", True)

    board.reset()
    assert flags["addr_reset"] is True
    assert dummy_cpu.reset_called is True
    assert board.clock.cycle_count == 0
    assert board.interrupt_ctrl._pending == []
