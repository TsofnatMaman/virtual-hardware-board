from simulator.core.simulation_engine import SimulationEngine


class DummyBoard:
    def __init__(self):
        self.steps = []
        self.resets = 0

    def step(self, cycles: int = 1) -> None:
        self.steps.append(cycles)

    def reset(self) -> None:
        self.resets += 1


def test_simulation_engine_run_step_reset():
    board = DummyBoard()
    engine = SimulationEngine()

    engine.run(board, cycles=4)
    engine.step(board, cycles=2)
    engine.reset(board)

    assert board.steps == [4, 2]
    assert board.resets == 1
