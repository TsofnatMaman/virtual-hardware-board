from simulator.core.clock import Clock
from simulator.core.interrupt_controller import InterruptController
from simulator.core.peripheral import BasePeripheral


class DummyPeripheral(BasePeripheral):
    def __init__(self):
        super().__init__(name="Dummy", size=4, base_addr=0x1000)
        self.last_write = None

    def read(self, offset: int, size: int) -> int:
        return 0xAB

    def write(self, offset: int, size: int, value: int) -> None:
        self.last_write = (offset, size, value)


class DummyCpu:
    def __init__(self):
        self.events = []

    def handle_interrupt(self, event) -> None:
        self.events.append(event)


def test_base_peripheral_read_write_aliases():
    periph = DummyPeripheral()
    assert periph.read_register(0x00, 4) == 0xAB
    periph.write_register(0x04, 4, 0x1234)
    assert periph.last_write == (0x04, 4, 0x1234)


def test_base_peripheral_emit_interrupt():
    clock = Clock()
    ctrl = InterruptController(clock)
    cpu = DummyCpu()
    ctrl.attach_cpu(cpu)

    periph = DummyPeripheral()
    periph.attach_interrupt_controller(ctrl)
    periph.emit_interrupt(vector=3)

    assert len(cpu.events) == 1
    event = cpu.events[0]
    assert event.source is periph
    assert event.vector == 3


def test_base_peripheral_emit_without_controller_no_error():
    periph = DummyPeripheral()
    periph.emit_interrupt(vector=1)
