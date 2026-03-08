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

    def get_register(self, index: int) -> int:
        if index != 0:
            raise ValueError("Dummy CPU exposes only R0")
        return self.steps

    def set_register(self, index: int, value: int) -> None:
        if index != 0:
            raise ValueError("Dummy CPU exposes only R0")
        self.steps = value


def test_icpu_default_tick_calls_step():
    cpu = DummyCPU()
    cpu.tick(3)
    assert cpu.steps == 3  # nosec B101


def test_icpu_default_handle_interrupt_noop():
    cpu = DummyCPU()
    result = cpu.handle_interrupt(object())
    assert result is None  # nosec B101


def test_icpu_register_access_contract():
    cpu = DummyCPU()
    cpu.set_register(0, 7)
    assert cpu.get_register(0) == 7  # nosec B101
