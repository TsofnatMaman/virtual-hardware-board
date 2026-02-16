# CMSIS-DAP Proxy (WIP)

This proxy sits between a virtual HID CMSIS-DAP driver and the simulator
debug TCP server. It receives 64-byte CMSIS-DAP packets from the driver and
returns responses.

Current scope
1. Implements basic CMSIS-DAP commands for enumeration.
2. Implements `DAP_Transfer` and `DAP_TransferBlock` with a minimal MEM-AP model.
3. Emulates a small subset of Cortex-M debug registers (DHCSR/DCRSR/DCRDR/DEMCR)
   and FPB breakpoints.
4. Run/step is emulated by a background step loop (slow but functional).

## Run (Phase 1)
1. Start the simulator debug server (no BIN when using an external debugger):
   `python -m simulator.debug.server --board tm4c123`
   By default this also launches the GUI. Use `--no-gui` for headless mode.
   Optional smoke-test (pre-load a BIN):
   `python -m simulator.debug.server --board tm4c123 --firmware firmware/led_blink/tm4c/firmware.bin`
2. Start the proxy (bridge mode):
   `python tools/cmsis_dap_proxy/proxy.py --board tm4c123 --bridge`

The bridge reads/writes 64-byte packets from `\\.\CmsisDapBridge`.

Optional TCP mode (legacy):
`python tools/cmsis_dap_proxy/proxy.py --board tm4c123 --listen-host 127.0.0.1 --listen-port 7230`

## Next step
1. Implement a KMDF virtual HID driver (CMSIS-DAP v1).
2. Improve CoreSight debug register coverage (DWT watchpoints, better CPUID).
3. Optimize run performance (batch stepping / server-side run thread).
