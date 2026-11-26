# Virtual Hardware Board

A Python-based virtual hardware platform for simulating Cortex-M boards, loading
firmware binaries, and observing peripheral behavior through CLI examples and a
GUI.

## Video tutorial

[`docs/tutorial.mp4`](docs/tutorial.mp4) (about 8 minutes, narrated in English) goes from a
fresh computer to debugging C code in VS Code on a virtual board:

1. installing the simulator,
2. creating a C project from the template and debugging it on the TM4C123,
3. the same workflow on the STM32F4 Discovery.

## Quick start

### 1) Install dependencies

```bash
pip install -r requirements.txt
```

### 2) Run the LED blink example

```bash
python -m examples.run_led_blink
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
python -m examples.run_gui

# or run directly
python -m simulator_gui --board tm4c123 --firmware firmware/led_blink/tm4c/firmware.bin
```

## GDB remote debugging (VS Code / gdb)

You can run the simulator as a classic **GDB remote target** and attach to it
from VS Code or plain `arm-none-eabi-gdb`.

### Option A: debug-only backend (headless, IDE loads program)

```bash
# terminal A: start simulator-backed GDB server
python -m simulator.debug --board tm4c123 --port 3333

# terminal B: connect with gdb
arm-none-eabi-gdb firmware/led_blink/tm4c/firmware.elf \
  -ex "target remote :3333"
```

### Option B: GUI + GDB on the same board instance (recommended)

```bash
# run GUI and embedded GDB server together
python -m simulator_gui --board tm4c123 --gdb-port 3333

# shortcut example script
python -m examples.run_gui_with_gdb
```

Supported protocol subset: register/memory read-write, binary memory write (`X`),
`monitor reset`, `step`, `continue`, software breakpoints (`Z0/z0`) and data
watchpoints (`watch`, `rwatch`, `awatch` = `Z2/Z3/Z4`) on any memory, including
stack locals. `continue` runs until a breakpoint/watchpoint fires; press
**Ctrl+C** (or the IDE pause button) to stop a running program. Use
`--max-continue-steps N` to bound a continue instead (default `0` = unlimited).

In both headless and GUI GDB modes, `--firmware` is optional: your IDE/GDB can upload
the program at runtime (using `load`). After code is written to flash, the simulator
performs a reset automatically on the first step/continue so execution starts from the
vector table like real hardware reset.

For VS Code, create `.vscode/launch.json` with a `cppdbg` or Cortex-Debug
configuration that points to `127.0.0.1:3333`.

### How the IDE finds the simulator (the port)

The IDE does not discover the simulator: the address is configured on both sides
and must match. The simulator listens on `--gdb-port` (default host `127.0.0.1`,
change with `--gdb-host`), and the IDE connects to it, e.g. in Cortex-Debug:

```json
"servertype": "external",
"gdbTarget": "127.0.0.1:3333"
```

(`miDebuggerServerAddress` in a `cppdbg` configuration.) The simulator board is
chosen with `--board`; a debug configuration only decides which firmware is built.
See [`templates/c_project/README.md`](templates/c_project/README.md) for details.

### Keil µVision (CMSIS-DAP, WIP, Windows)

Keil is bridged through a virtual CMSIS-DAP HID device:
`Keil -> virtual HID driver -> tools/cmsis_dap_proxy -> JSON debug server -> simulator`.
Run the JSON server without `--firmware` and let the debugger download the program:

```bash
python -m simulator.debug.server --board tm4c123          # GUI + debug server
python -m simulator.debug.server --board tm4c123 --no-gui # headless
```

See `tools/cmsis_dap_proxy/README.md` and `tools/cmsis_dap_vhid/README.md`.
The virtual HID driver is not implemented yet.

### Shared debug layer

GDB and Keil use the same `simulator.debug.DebugSession` (step/run/halt,
registers, memory, breakpoints, reset-after-flash-write). `GdbTarget` (GDB
protocol) and `DebugServer` (JSON for the CMSIS-DAP proxy) are thin adapters.
When `--gdb-port` is used with the GUI, the debugger owns the clock and the GUI
only repaints.

### VS Code: press F5 (Cortex-Debug)

The repo ships `.vscode/launch.json` and `tasks.json`. Prerequisites: the
**Cortex-Debug** extension (recommended automatically when you open the folder),
`arm-none-eabi-gcc`/`make`, `arm-none-eabi-gdb` on `PATH` (or set
`cortex-debug.gdbPath`, e.g. to `gdb-multiarch`), and `pip install -r requirements.txt -r requirements-gui.txt`.

1. Open the repo folder in VS Code.
2. Run and Debug -> pick **Debug TM4C123 on simulator (GUI)** (or STM32C031 /
   headless) -> **F5**.
3. VS Code builds the firmware (`build/<board>.elf`), starts the simulator with its
   GDB server on port 3333, downloads the program, resets and stops at `main`.
4. Set breakpoints/watchpoints in C, step, continue, **Pause** (Ctrl+C), and watch
   the LEDs in the simulator window. Stopping the session closes the simulator.

### Separate windows: simulator in one, your C project in another

To debug your own C project without opening this repo, copy
`templates/c_project/` anywhere and follow its README: start the simulator with
`python -m simulator_gui --board tm4c123 --gdb-port 3333` in one window, open the
copied project in another VS Code window and press F5.

### VS Code step-by-step (C firmware + visual simulator)

1. Build firmware + ELF:
   ```bash
   make -f firmware/Makefile BOARD=tm4c123 MAIN=firmware/led_blink/tm4c/main.c
   ```
2. Start the visual simulator with built-in GDB server:
   ```bash
   python -m simulator_gui --board tm4c123 --gdb-port 3333
   ```
3. In VS Code, open your C source folder and launch a `cppdbg` config that uses:
   - `miDebuggerPath`: `arm-none-eabi-gdb`
   - `program`: `firmware/led_blink/tm4c/firmware.elf`
   - `miDebuggerServerAddress`: `127.0.0.1:3333`
4. In the Debug Console run `load` (or let the extension upload automatically) so
   the IDE streams program bytes into the simulator.
5. Optionally run `monitor reset`/restart command from your extension; otherwise the
   first step/continue will reset automatically after load.
6. Set breakpoints in C and press **Start Debugging**.
7. Use **Continue / Step Over / Step Into** in VS Code and watch GPIO/LED changes
   in the GUI window.

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

quality/        # quality gates (registry, runner, one module per gate)

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

1. Create a package `simulator/<myboard>/` with a `config.yaml` (memory map, GPIO ports, pins,
   system control). The loader (`simulator.utils.config_loader`) validates it.
2. If the chip's GPIO or register layout differs from an existing one, add its GPIO
   peripheral and memory-access model next to it; otherwise reuse the existing ones.
3. Describe the board with a `BoardSpec` on a `ConfiguredBoard` subclass (all wiring is in
   `simulator/core/configured_board.py`; see `simulator/stm32/board.py` for a complete
   example of about ten lines):

   ```python
   class MyBoard(ConfiguredBoard):
       spec = BoardSpec(
           key="myboard", name="MyBoard", config_path=Path(__file__).parent / "config.yaml",
           gpio_kind="stm32", gpio_class=STM32GPIO, access_model=STM32F4DirectAccessModel,
       )
   ```

4. Register it in the package `__init__.py` with its key:

   ```python
   from simulator.core.board import register_board
   register_board(MyBoard.spec.key, MyBoard)
   ```

5. Add GPIO/memory-model tests under `tests/<myboard>/` if you added new peripherals;
   `tests/core/test_configured_board.py` covers the shared wiring (add the key to its table).
6. (Optional) add GUI config in `simulator_gui/boards/<myboard>.yaml`. A
   `background_image` (its size must equal `canvas`) gives the board a picture, and
   each component's `position` places an LED/switch on it. See
   `simulator_gui/boards/stm32f4.yaml`: its background is a photo of the STM32F4
   Discovery board and the four LEDs sit on their footprints.

To write and debug C code for the new board in VS Code, also add it to the C side:

7. `firmware/boards/<myboard>/` (linker script + register header) and a branch for
   it in `firmware/Makefile`.
8. `templates/c_project/`: `board/<myboard>/`, a `Makefile` branch, a
   `build (<myboard>)` task in `.vscode/tasks.json` and a debug configuration in
   `.vscode/launch.json` (checklist in `templates/c_project/README.md`).
9. This repo's own `.vscode/launch.json` / `tasks.json` if you want F5 for the
   bundled examples.

Start the simulator with `--board <myboard>` and keep `--gdb-port` equal to the
`gdbTarget` port in `launch.json`.

## Tests

```bash
pip install -r requirements-dev.txt -r requirements-gui.txt
pytest                      # everything (~45 s)
pytest -m "not integration" # fast unit tests only
```

| Area | Where | Needs |
|---|---|---|
| CPU, memory, GPIO, boards, config | `tests/core`, `tests/tm4c123`, `tests/stm32*`, `tests/utils` | `unicorn` |
| GDB server, debug session, watchpoints, Ctrl+C, JSON server | `tests/debug` | `unicorn` |
| CMSIS-DAP (Keil) emulator driven like Keil, on a real board | `tests/tools` | `unicorn` |
| GUI: board layouts (`simulator_gui/boards/*.yaml`), components, window, `run_gui` | `tests/gui` | `PySide6` (runs headless via Qt `offscreen`) |
| Firmware builds for every board and runs on the simulator; real `gdb` sessions; VS Code/template consistency | `tests/integration` | `arm-none-eabi-gcc`, `make`, `gdb-multiarch` |

Tests that need an optional tool are skipped when it is missing. CI installs everything and sets
`REQUIRE_FULL_TEST_ENV=1`, which turns a missing tool into a failure instead of a skip.

Adding a board? `tests/integration/test_vscode_and_board_consistency.py` fails until the
template (board files, `Makefile`, `tasks.json`, `launch.json`), `firmware/` and the GUI layout
all know about it.

## Quality checks

The coding rules are in [CODING_GUIDELINES.md](CODING_GUIDELINES.md); they are enforced by
quality gates that run locally, in CI and on a schedule
([docs/quality-gates.md](docs/quality-gates.md)).

```bash
python -m quality.run --list                # every gate and its stage
python -m quality.run --stage pre-commit    # the fast ones (also: pre-commit install)
python -m quality.run                       # everything CI runs, including the tests
python -m quality.run --fix                 # apply black/isort
```
