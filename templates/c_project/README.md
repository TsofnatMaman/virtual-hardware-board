# C project for the Virtual Hardware Board

A self-contained Cortex-M C project you debug on the simulator from its **own**
VS Code window. The simulator runs separately (see below), like an external
debug probe plus board.

## One-time setup
- Install `arm-none-eabi-gcc`, `make`, and `arm-none-eabi-gdb` (or set
  `cortex-debug.gdbPath` to `gdb-multiarch`).
- VS Code extension **Cortex-Debug** (recommended automatically on open).

## Use
1. **Window 1 - the simulator** (open the `virtual-hardware-board` repo):

   ```bash
   pip install -r requirements.txt -r requirements-gui.txt   # once
   python -m simulator_gui --board tm4c123 --gdb-port 3333
   ```

   Leave it running. It starts empty and waits for the debugger to download your
   program. (For STM32C031 use `--board stm32c031`.)
2. **Window 2 - your C project:** copy this folder anywhere (it does not depend
   on the repo), open it in VS Code, edit `src/main.c`.
3. Press **F5** and pick *Debug on simulator (TM4C123)*. VS Code builds
   `build/app.elf`, connects to `127.0.0.1:3333`, downloads the program, resets
   and stops at `main`. Set breakpoints/watchpoints, step, **Pause**, and watch the
   LEDs in window 1.
4. Stop and press F5 again as often as you like; the simulator keeps running.

## How VS Code finds the simulator (port 3333)

VS Code does not discover the simulator. The address is written in **two places**
and they must match:

| Side | Where | Setting |
|---|---|---|
| Simulator | the command that starts it | `--gdb-port 3333` (optionally `--gdb-host`, default `127.0.0.1`) |
| VS Code | `.vscode/launch.json` | `"gdbTarget": "127.0.0.1:3333"` |

When you press F5, VS Code starts `gdb`, Cortex-Debug tells it to connect to
`gdbTarget`, and the simulator (listening on that port) answers with the GDB remote
protocol. `"servertype": "external"` means "the debug server is already running,
do not start one". If nothing is listening you get *connection refused*.

To use another port, change both sides, e.g. `--gdb-port 4444` and
`"gdbTarget": "127.0.0.1:4444"`. To reach a simulator on another machine start it with
`--gdb-host 0.0.0.0` and point `gdbTarget` at that machine's address.

**The board is chosen on the simulator side.** `launch.json` does not start the
simulator and does not select the chip: the `--board` flag does. A configuration
only decides *which firmware gets built* (through its `preLaunchTask`). If the
firmware does not match the running board (for example STM32 code on a
`tm4c123` simulator) the download can fail with *Load failed*, or the program
will not behave correctly, so keep the two in sync.

## Adding another board to this template

Say you added a board called `myboard` to the simulator (see the root README,
"Adding a new board"). To debug C code for it from this template:

1. **Board files:** create `board/myboard/` with `linker.ld` (its `FLASH`/`SRAM`
   origins and sizes must match the simulator's memory map) and a register header
   `myboard.h`. Copy one of the existing boards as a starting point.
2. **`Makefile`:** add a branch that selects the CPU, and update the error text:

   ```make
   else ifeq ($(BOARD),myboard)
   CPU := cortex-m4
   ```

3. **`.vscode/tasks.json`:** add a build task next to the existing ones:

   ```json
   {
     "label": "build (myboard)",
     "type": "shell",
     "command": "make BOARD=myboard",
     "problemMatcher": ["$gcc"],
     "group": "build"
   }
   ```

4. **`.vscode/launch.json`:** add a configuration. Copy an existing one and change
   only `name` and `preLaunchTask`; keep `gdbTarget` (same port) unless you changed it:

   ```json
   {
     "name": "Debug on simulator (MYBOARD)",
     "type": "cortex-debug",
     "request": "launch",
     "servertype": "external",
     "gdbTarget": "127.0.0.1:3333",
     "cwd": "${workspaceFolder}",
     "executable": "${workspaceFolder}/build/app.elf",
     "runToEntryPoint": "main",
     "overrideLaunchCommands": ["-target-download", "interpreter-exec console \"monitor reset\""],
     "overrideRestartCommands": ["interpreter-exec console \"monitor reset\""],
     "preLaunchTask": "build (myboard)"
   }
   ```

5. **Run:** start the simulator with `--board myboard --gdb-port 3333`, pick the new
   configuration in Run and Debug, press F5.

The same checklist applies to the repo's own `.vscode/launch.json` and
`.vscode/tasks.json` (the F5 setup for the bundled examples).

## Layout
- `src/*.c` - your code (all files are compiled).
- `board/` - startup code, linker scripts and register headers per board.
- `make BOARD=tm4c123|stm32c031` - build from a terminal.
