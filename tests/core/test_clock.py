import pytest

from simulator.core.clock import Clock


class SubscriberWithCycles:
    def __init__(self):
        self.calls = 0
        self.cycles = []

    def tick(self, cycles: int = 1) -> None:
        self.calls += 1
        self.cycles.append(cycles)


class SubscriberNoArgs:
    def __init__(self):
        self.calls = 0

    def tick(self) -> None:
        self.calls += 1


def test_clock_subscribe_unsubscribe_and_tick():
    clock = Clock(frequency=1_000)
    sub = SubscriberWithCycles()

    clock.subscribe(sub)
    clock.subscribe(sub)  # should not duplicate
    clock.tick(5)

    assert clock.cycle_count == 5
    assert sub.calls == 1
    assert sub.cycles == [5]

    clock.unsubscribe(sub)
    clock.tick(2)
    assert sub.calls == 1  # no new calls after unsubscribe


def test_clock_tick_fallback_for_no_args_subscriber():
    clock = Clock()
    sub = SubscriberNoArgs()
    clock.subscribe(sub)

    clock.tick(3)
    assert clock.cycle_count == 3
    assert sub.calls == 3


def test_clock_reset():
    clock = Clock()
    clock.tick(4)
    clock.reset()
    assert clock.cycle_count == 0


def test_clock_invalid_frequency():
    with pytest.raises(ValueError):
        Clock(frequency=0)


def test_clock_negative_cycles():
    clock = Clock()
    with pytest.raises(ValueError):
        clock.tick(-1)
