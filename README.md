# Virtual Hardware Board

A Python-based virtual hardware platform for simulating Cortex-M boards, loading
firmware binaries, and observing peripheral behavior through CLI examples and a
GUI.

## Quick start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Run the LED blink example

```bash
python examples/run_led_blink.py
```

### 3) Run tests

```bash
pytest
```

## GUI

```bash
# install GUI dependencies
pip install -r requirements-gui.txt

# run GUI (TM4C123 + LED blink firmware)
python examples/run_gui.py

# or run directly
python -m simulator_gui --board tm4c123 --firmware firmware/led_blink/tm4c/firmware.bin
```

## Project structure

```text
simulator/
  core/         # CPU, clock, interrupt controller, address-space & registry
  interfaces/   # behavioral contracts for boards/peripherals
  stm32/        # STM32F4 implementation + config
  stm32c031/    # STM32C031 implementation + config
  tm4c/         # TM4C123 implementation + config
  utils/        # config parsing/validation helpers

simulator_gui/
  components/   # visual components (LED/button/switch)
  view/         # Qt views/widgets
  backend.py    # adapter from board API to GUI controllers

tests/
  core/         # core engine and registry tests
  interfaces/   # contract-level tests
  stm32*/tm4c*  # board-specific behavior tests
  utils/        # config/constant tests
```

## Architecture (high level)

1. Board modules register themselves during import via `register_board(...)`.
2. `create_board(<name>)` instantiates a board through the global registry.
3. Board wires CPU + memory + peripherals + interrupt controller.
4. `SimulationEngine`/GUI drives execution via `board.step(cycles)`.
5. Peripherals expose memory-mapped behavior through the address space.

## Adding a new board

1. Create a new module under `simulator/<vendor_or_board>/`.
2. Implement `Board` interface (`name`, `read/write`, `step`, `reset`, etc.).
3. Add `config.yaml` and parse it through `simulator.utils.config_loader`.
4. Register board in module `__init__.py` with a unique key:

   ```python
   from simulator.core.board import register_board
   register_board("myboard", MyBoard)
   ```

5. Add board-level tests under `tests/<myboard>/`.
6. (Optional) add GUI config in `simulator_gui/boards/<myboard>.yaml`.

## Quality checks

Run all local checks (formatting, linting, typing, complexity, tests):

```bash
python utils/run_quality_checks.py
```
