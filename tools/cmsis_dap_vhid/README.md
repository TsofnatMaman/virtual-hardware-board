# Virtual CMSIS-DAP HID Driver (WIP)

This folder is a placeholder for a KMDF virtual HID driver that exposes a
CMSIS-DAP v1 device to Windows and forwards packets to the user-mode proxy.

## Prerequisites
1. Visual Studio
2. Windows Driver Kit (WDK) + WDK Visual Studio extension
3. Driver samples (optional if you use the vendored copy below)

Quick check:
`Test-Path "C:\Program Files (x86)\Windows Kits\10\Include\wdf"`

If Driver Samples are not installed via WDK, use the vendored sample at:
`tools/cmsis_dap_vhid/vhidmini2_src`

## Driver responsibilities
1. Enumerate a virtual HID device with a vendor-defined usage page.
2. Report size: 64 bytes input/output (Report ID 0).
3. Product string must include `CMSIS-DAP` so Keil detects it.
4. Bridge HID packets to a user-mode proxy via `\\.\CmsisDapBridge`.

## Recommended starting point
Microsoft recommends starting from the `vhidmini2` sample and adapting it
for a virtual HID device. Use WDK + Visual Studio to create the KMDF project.

To (re)import the sample after installing WDK or from a local clone:
`powershell -ExecutionPolicy Bypass -File tools\cmsis_dap_vhid\import_vhidmini2.ps1`

## Bridge contract (driver <-> proxy)
1. The driver creates a DOS device name: `\\.\CmsisDapBridge`.
2. `WriteFile` from the proxy sends a 64-byte response to the HID host.
3. `ReadFile` from the proxy returns the next 64-byte request from the HID host.

## Status
Only documentation and proxy exist right now. The driver implementation is
the next step.
