from simulator.interfaces.cpu import ICPU, CpuSnapshot, RegisterValue


class DummyCPU(ICPU):
    def __init__(self):
        self.steps = 0
        self.interrupts = 0

    def step(self) -> None:
        self.steps += 1

    def reset(self) -> None:
        self.steps = 0

    def get_snapshot(self) -> CpuSnapshot:
        return CpuSnapshot(
            registers=[RegisterValue("R0", self.steps)],
            flags={"Z": False},
        )


def test_icpu_default_tick_calls_step():
    cpu = DummyCPU()
    cpu.tick(3)
    assert cpu.steps == 3


def test_icpu_default_handle_interrupt_noop():
    cpu = DummyCPU()
    result = cpu.handle_interrupt(object())
    assert result is None
