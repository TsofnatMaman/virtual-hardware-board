# USB CMSIS-DAP (Virtual HID) - WIP

Goal: make Windows/Keil see a **USB CMSIS-DAP** debug probe that bridges to the
Python simulator.

## Architecture
1. Keil talks to a virtual HID device (CMSIS-DAP v1, 64-byte reports).
2. The virtual HID driver forwards packets to a user-mode proxy.
3. The proxy maps CMSIS-DAP commands to the simulator TCP debug server.

## Current status
1. Proxy exists: `tools/cmsis_dap_proxy/proxy.py`.
2. Driver is in progress under `tools/cmsis_dap_vhid/vhidmini2_src`.
3. `DAP_Transfer` and `DAP_TransferBlock` are implemented with a minimal MEM-AP
   model and basic Cortex-M debug register emulation.

## Phase 1: enumeration + basic debug (current)
Purpose: Keil should **see** a CMSIS-DAP device and perform basic transfers.

What works
1. `DAP_Info`
2. `DAP_Connect` / `DAP_Disconnect`
3. `DAP_ResetTarget`
4. `DAP_TransferConfigure`
5. `DAP_Transfer` / `DAP_TransferBlock` (basic MEM-AP)

What is missing
1. Driver build/sign/install steps (KMDF virtual HID driver)
2. Full CoreSight coverage (DWT watchpoints, richer status/registers)
3. Performance (run loop currently steps one instruction at a time)

## Phase 2: full debug (future)
Implement SWD/DAP register access and map to simulator `read_mem`/`write_mem`
and register operations. This is the hard part.

## Driver build notes
1. Use WDK + Visual Studio.
2. Start from the `vhidmini2` sample and adapt it to CMSIS-DAP.
3. Product string must include `CMSIS-DAP` so Keil recognizes the probe.
4. Expose a bridge device `\\.\CmsisDapBridge` for the proxy.

## Run (Phase 1)
1. Start the simulator debug server (no BIN when using an external debugger):
   `python -m simulator.debug.server --board tm4c123`
   By default this also launches the GUI. Use `--no-gui` for headless mode.
   Optional smoke-test (pre-load a BIN):
   `python -m simulator.debug.server --board tm4c123 --firmware firmware/led_blink/tm4c/firmware.bin`
2. Start the proxy:
   `python tools/cmsis_dap_proxy/proxy.py --board tm4c123 --bridge`
3. Load the driver and open Keil. The device should appear as CMSIS-DAP.
