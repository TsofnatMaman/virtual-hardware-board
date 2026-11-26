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

## Layout
- `src/*.c` - your code (all files are compiled).
- `board/` - startup code, linker scripts and register headers per board.
- `make BOARD=tm4c123|stm32c031` - build from a terminal.
