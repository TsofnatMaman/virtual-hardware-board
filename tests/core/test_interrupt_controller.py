from simulator.core.clock import Clock
from simulator.core.interrupt_controller import InterruptController


class DummyCpu:
    def __init__(self):
        self.events = []

    def handle_interrupt(self, event) -> None:
        self.events.append(event)


def test_interrupt_controller_notify_and_timestamp():
    clock = Clock()
    ctrl = InterruptController(clock)
    cpu = DummyCpu()
    ctrl.attach_cpu(cpu)

    clock.tick(7)
    event = ctrl.notify(source="gpio", vector=5)

    assert event.source == "gpio"
    assert event.vector == 5
    assert event.timestamp == 7
    assert cpu.events == [event]


def test_interrupt_controller_reset_clears_pending():
    ctrl = InterruptController()
    ctrl.notify(source="timer", vector=None)
    assert len(ctrl._pending) == 1
    ctrl.reset()
    assert len(ctrl._pending) == 0


def test_interrupt_controller_subscribe_no_duplicates():
    ctrl = InterruptController()
    obj = object()
    ctrl.subscribe(obj)
    ctrl.subscribe(obj)
    assert len(ctrl._subscribers) == 1
