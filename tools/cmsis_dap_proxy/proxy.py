"""CMSIS-DAP v1 proxy (WIP).

Bridges a virtual HID CMSIS-DAP device to the simulator debug TCP server.
This is the user-mode side of the USB pipeline.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional

from ctypes import wintypes


DAP_PACKET_SIZE = 64
DAP_OK = 0x00
DAP_ERROR = 0xFF
DAP_TRANSFER_OK = 0x01
DAP_TRANSFER_WAIT = 0x02
DAP_TRANSFER_FAULT = 0x04
DAP_TRANSFER_ERROR = 0x08
DAP_TRANSFER_MISMATCH = 0x10

# DAP_Transfer request bit definitions
REQ_APnDP = 1 << 0
REQ_RnW = 1 << 1
REQ_A2 = 1 << 2
REQ_A3 = 1 << 3
REQ_MATCH_VALUE = 1 << 4
REQ_MATCH_MASK = 1 << 5
REQ_TIME_STAMP = 1 << 7

# CMSIS-DAP command IDs (v1/v2 share most IDs)
CMD_DAP_INFO = 0x00
CMD_DAP_HOST_STATUS = 0x01
CMD_DAP_CONNECT = 0x02
CMD_DAP_DISCONNECT = 0x03
CMD_DAP_TRANSFER_CONFIGURE = 0x04
CMD_DAP_TRANSFER = 0x05
CMD_DAP_TRANSFER_BLOCK = 0x06
CMD_DAP_WRITE_ABORT = 0x08
CMD_DAP_DELAY = 0x09
CMD_DAP_RESET_TARGET = 0x0A
CMD_DAP_SWJ_SEQUENCE = 0x12
CMD_DAP_SWD_CONFIGURE = 0x13
CMD_DAP_JTAG_CONFIGURE = 0x15
CMD_DAP_SWO_TRANSPORT = 0x17
CMD_DAP_SWD_SEQUENCE = 0x1D
CMD_DAP_UART_TRANSPORT = 0x1F
CMD_DAP_EXECUTE_COMMANDS = 0x7F
CMD_DAP_QUEUE_COMMANDS = 0x7E

# DAP_Info IDs
INFO_VENDOR_NAME = 0x01
INFO_PRODUCT_NAME = 0x02
INFO_SERIAL_NUMBER = 0x03
INFO_PROTOCOL_VERSION = 0x04
INFO_TARGET_DEVICE_VENDOR = 0x05
INFO_TARGET_DEVICE_NAME = 0x06
INFO_TARGET_BOARD_VENDOR = 0x07
INFO_TARGET_BOARD_NAME = 0x08
INFO_PRODUCT_FIRMWARE_VERSION = 0x09
INFO_CAPABILITIES = 0xF0
INFO_TEST_DOMAIN_TIMER = 0xF1
INFO_UART_RX_BUFFER_SIZE = 0xFB
INFO_UART_TX_BUFFER_SIZE = 0xFC
INFO_SWO_BUFFER_SIZE = 0xFD
INFO_PACKET_COUNT = 0xFE
INFO_PACKET_SIZE = 0xFF

# Core debug register addresses (System Control Space)
CPUID_ADDR = 0xE000ED00
DHCSR_ADDR = 0xE000EDF0
DCRSR_ADDR = 0xE000EDF4
DCRDR_ADDR = 0xE000EDF8
DEMCR_ADDR = 0xE000EDFC

# FPB (Flash Patch and Breakpoint) registers
FPB_BASE = 0xE0002000
FP_CTRL_ADDR = FPB_BASE + 0x00
FP_REMAP_ADDR = FPB_BASE + 0x04
FP_COMP_BASE = FPB_BASE + 0x08


def _pad_packet(payload: bytes, packet_size: int) -> bytes:
    if len(payload) > packet_size:
        raise ValueError("DAP payload exceeds packet size")
    return payload + bytes(packet_size - len(payload))


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            return b""
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


if os.name == "nt":
    _KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _CreateFileW = _KERNEL32.CreateFileW
    _ReadFile = _KERNEL32.ReadFile
    _WriteFile = _KERNEL32.WriteFile
    _CloseHandle = _KERNEL32.CloseHandle

    _CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    _CreateFileW.restype = wintypes.HANDLE
    _ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _ReadFile.restype = wintypes.BOOL
    _WriteFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    _WriteFile.restype = wintypes.BOOL
    _CloseHandle.argtypes = [wintypes.HANDLE]
    _CloseHandle.restype = wintypes.BOOL
else:
    _KERNEL32 = None
    _CreateFileW = None
    _ReadFile = None
    _WriteFile = None
    _CloseHandle = None

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 0x00000003
FILE_ATTRIBUTE_NORMAL = 0x00000080
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value


def _raise_last_error(message: str) -> None:
    err = ctypes.get_last_error()
    raise OSError(err, f"{message} (WinError {err})")


class HidBridge:
    def __init__(self, path: str, packet_size: int) -> None:
        self._path = path
        self._packet_size = packet_size
        self._handle: Optional[int] = None

    def open(self) -> None:
        if os.name != "nt":
            raise RuntimeError("Bridge mode is only supported on Windows")
        if self._handle is not None:
            return
        handle = _CreateFileW(
            self._path,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL,
            None,
        )
        if handle == INVALID_HANDLE_VALUE:
            _raise_last_error(f"CreateFile failed for {self._path}")
        self._handle = handle

    def close(self) -> None:
        if self._handle is None:
            return
        _CloseHandle(self._handle)
        self._handle = None

    def read_packet(self) -> bytes:
        if self._handle is None:
            raise RuntimeError("Bridge not open")
        buffer = (ctypes.c_ubyte * self._packet_size)()
        bytes_read = wintypes.DWORD(0)
        ok = _ReadFile(
            self._handle,
            buffer,
            self._packet_size,
            ctypes.byref(bytes_read),
            None,
        )
        if not ok:
            _raise_last_error("ReadFile failed")
        if bytes_read.value == 0:
            return b""
        return bytes(buffer[: bytes_read.value])

    def write_packet(self, payload: bytes) -> None:
        if self._handle is None:
            raise RuntimeError("Bridge not open")
        if len(payload) != self._packet_size:
            payload = payload[: self._packet_size].ljust(self._packet_size, b"\x00")
        bytes_written = wintypes.DWORD(0)
        ok = _WriteFile(
            self._handle,
            payload,
            self._packet_size,
            ctypes.byref(bytes_written),
            None,
        )
        if not ok:
            _raise_last_error("WriteFile failed")
        if bytes_written.value != self._packet_size:
            raise RuntimeError("Short write to bridge")


class DebugClient:
    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._file = None
        self._next_id = 1

    def _connect(self) -> None:
        if self._sock:
            return
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        self._sock = sock
        self._file = sock.makefile("rwb")

    def close(self) -> None:
        if self._file:
            self._file.close()
        if self._sock:
            self._sock.close()
        self._file = None
        self._sock = None

    def request(self, cmd: str, **kwargs: object) -> dict:
        self._connect()
        assert self._file is not None
        req_id = self._next_id
        self._next_id += 1
        payload = {"id": req_id, "cmd": cmd}
        payload.update(kwargs)
        self._file.write((json.dumps(payload) + "\n").encode("utf-8"))
        self._file.flush()
        line = self._file.readline()
        if not line:
            self.close()
            raise RuntimeError("Debug server disconnected")
        response = json.loads(line.decode("utf-8"))
        if not response.get("ok", False):
            raise RuntimeError(response.get("error", "Unknown debug error"))
        return response.get("result", {})

    def read_mem(self, address: int, size: int) -> bytes:
        result = self.request("read_mem", address=address, size=size)
        return bytes.fromhex(result.get("data", ""))

    def write_mem(self, address: int, data: bytes) -> None:
        self.request("write_mem", address=address, data=data.hex())

    def read_reg(self, index: int) -> int:
        result = self.request("read_reg", index=index)
        return int(result.get("value", 0))

    def write_reg(self, index: int, value: int) -> None:
        self.request("write_reg", index=index, value=value)

    def reset(self) -> None:
        self.request("reset")

    def step(self) -> dict:
        return self.request("step")

    def halt(self) -> None:
        self.request("halt")

    def set_breakpoint(self, address: int) -> None:
        self.request("set_bp", address=address)

    def clear_breakpoint(self, address: int) -> None:
        self.request("clear_bp", address=address)


@dataclass
class TransferConfig:
    idle_cycles: int = 0
    retry_count: int = 0
    match_retry: int = 0


class DebugRegisterFile:
    """Minimal emulation of Cortex-M debug registers for Keil."""

    def __init__(self, debug_client: Optional[DebugClient], board_name: str) -> None:
        self._client = debug_client
        self._board_name = board_name
        self._dhcsr = 0
        self._dcrsr = 0
        self._dcrdr = 0
        self._demcr = 0
        self._halted = False
        self._debug_enabled = False

        self._fpb_enabled = False
        self._fpb_num = 6
        self._fpb_comp: list[int | None] = [None] * self._fpb_num
        self._fpb_comp_raw: list[int] = [0] * self._fpb_num
        self._fpb_remap = 0

    def read(self, address: int, size: int) -> int:
        if address == CPUID_ADDR:
            return self._cpuid()
        if address == DHCSR_ADDR:
            return self._read_dhcsr()
        if address == DCRSR_ADDR:
            return self._dcrsr
        if address == DCRDR_ADDR:
            return self._dcrdr
        if address == DEMCR_ADDR:
            return self._demcr
        if address == FP_CTRL_ADDR:
            return self._read_fpb_ctrl()
        if address == FP_REMAP_ADDR:
            return self._fpb_remap
        if FP_COMP_BASE <= address < FP_COMP_BASE + 4 * self._fpb_num:
            idx = (address - FP_COMP_BASE) // 4
            return self._fpb_comp_raw[idx]
        # Default for other SCS addresses
        return 0

    def write(self, address: int, size: int, value: int) -> None:
        if address == DHCSR_ADDR:
            self._write_dhcsr(value)
            return
        if address == DCRSR_ADDR:
            self._write_dcrsr(value)
            return
        if address == DCRDR_ADDR:
            self._dcrdr = value & 0xFFFFFFFF
            return
        if address == DEMCR_ADDR:
            self._demcr = value & 0xFFFFFFFF
            return
        if address == FP_CTRL_ADDR:
            self._fpb_enabled = bool(value & 1)
            return
        if address == FP_REMAP_ADDR:
            self._fpb_remap = value & 0xFFFFFFFF
            return
        if FP_COMP_BASE <= address < FP_COMP_BASE + 4 * self._fpb_num:
            idx = (address - FP_COMP_BASE) // 4
            self._write_fpb_comp(idx, value)
            return
        # Ignore unknown debug regs

    def set_halted(self, halted: bool) -> None:
        self._halted = halted

    def is_halted(self) -> bool:
        return self._halted

    def _cpuid(self) -> int:
        # Default to Cortex-M4 if unknown; refine later per board.
        if self._board_name.lower().startswith("stm32c031"):
            # Cortex-M0+ (approximate)
            return 0x410CC200
        return 0x410FC241

    def _read_dhcsr(self) -> int:
        value = 0
        if self._debug_enabled:
            value |= 1 << 0  # C_DEBUGEN
        if self._halted:
            value |= 1 << 17  # S_HALT
        value |= 1 << 16  # S_REGRDY (always ready)
        return value

    def _write_dhcsr(self, value: int) -> None:
        if (value >> 16) != 0xA05F:
            return
        control = value & 0xFFFF
        self._debug_enabled = bool(control & (1 << 0))
        halt = bool(control & (1 << 1))
        step = bool(control & (1 << 2))

        if self._client is None:
            self._halted = halt or step
            return

        if step:
            self._client.step()
            self._halted = True
            return

        if halt:
            self._client.halt()
            self._halted = True
            return

        # Run/resume
        self._halted = False

    def _write_dcrsr(self, value: int) -> None:
        self._dcrsr = value & 0xFFFFFFFF
        regsel = value & 0x1F
        reg_write = bool(value & (1 << 16))

        if self._client is None:
            return

        if reg_write:
            self._write_core_reg(regsel, self._dcrdr)
        else:
            self._dcrdr = self._read_core_reg(regsel)

    def _read_core_reg(self, regsel: int) -> int:
        if self._client is None:
            return 0
        if 0 <= regsel <= 15:
            return self._client.read_reg(regsel)
        if regsel == 17:
            # MSP - approximate with SP
            return self._client.read_reg(13)
        return 0

    def _write_core_reg(self, regsel: int, value: int) -> None:
        if self._client is None:
            return
        if 0 <= regsel <= 15:
            self._client.write_reg(regsel, value)
            return
        # Ignore unsupported special registers for now.

    def _read_fpb_ctrl(self) -> int:
        num_code = (self._fpb_num & 0xF) << 4
        return num_code | (1 if self._fpb_enabled else 0)

    def _write_fpb_comp(self, idx: int, value: int) -> None:
        if idx >= self._fpb_num:
            return
        self._fpb_comp_raw[idx] = value & 0xFFFFFFFF
        enable = bool(value & 1)
        addr = value & 0x1FFFFFFC
        old_addr = self._fpb_comp[idx]
        if self._client is None:
            self._fpb_comp[idx] = addr if enable else None
            return
        if old_addr is not None and (not enable or old_addr != addr):
            self._client.clear_breakpoint(old_addr)
        if enable:
            self._client.set_breakpoint(addr)
            self._fpb_comp[idx] = addr
        else:
            self._fpb_comp[idx] = None


class CmsisDapEmulator:
    def __init__(
        self,
        board_name: str,
        debug_client: Optional[DebugClient],
        packet_size: int = DAP_PACKET_SIZE,
    ) -> None:
        self.board_name = board_name
        self.debug_client = debug_client
        self.packet_size = packet_size
        self.packet_count = 1
        self.connected_port = 0
        self.transfer_config = TransferConfig()
        self._dp_select = 0
        self._dp_ctrl_stat = 0
        self._dp_rdbuff = 0
        self._ap_csw = 0x00000002  # 32-bit, no auto-inc by default
        self._ap_tar = 0
        self._ap_idr = 0x24770011  # Minimal MEM-AP IDR
        self._debug_regs = DebugRegisterFile(debug_client, board_name)
        self._run_thread: Optional[threading.Thread] = None
        self._run_active = False
        self._run_lock = threading.Lock()

        self.vendor_name = "VirtualBoard"
        self.product_name = "Virtual CMSIS-DAP"
        self.serial_number = "0001"
        self.protocol_version = "2.1.0"
        self.firmware_version = "0.1"

    def handle_packet(self, packet: bytes) -> bytes:
        if not packet:
            return _pad_packet(bytes([DAP_ERROR]), self.packet_size)

        cmd = packet[0]
        handlers = {
            CMD_DAP_INFO: self._cmd_info,
            CMD_DAP_CONNECT: self._cmd_connect,
            CMD_DAP_DISCONNECT: self._cmd_disconnect,
            CMD_DAP_RESET_TARGET: self._cmd_reset_target,
            CMD_DAP_TRANSFER_CONFIGURE: self._cmd_transfer_configure,
            CMD_DAP_TRANSFER: self._cmd_transfer,
            CMD_DAP_TRANSFER_BLOCK: self._cmd_transfer_block,
            CMD_DAP_WRITE_ABORT: self._cmd_write_abort,
            CMD_DAP_SWJ_SEQUENCE: self._cmd_swj_sequence,
            CMD_DAP_SWD_CONFIGURE: self._cmd_swd_configure,
            CMD_DAP_JTAG_CONFIGURE: self._cmd_jtag_configure,
            CMD_DAP_SWO_TRANSPORT: self._cmd_swo_transport,
            CMD_DAP_DELAY: self._cmd_delay,
        }

        handler = handlers.get(cmd, self._cmd_not_implemented)
        response = handler(packet)
        return _pad_packet(response, self.packet_size)

    def _cmd_not_implemented(self, _packet: bytes) -> bytes:
        return bytes([DAP_ERROR])

    def _cmd_info(self, packet: bytes) -> bytes:
        if len(packet) < 2:
            return bytes([CMD_DAP_INFO, 0])
        info_id = packet[1]
        info = self._info_payload(info_id)
        return bytes([CMD_DAP_INFO, len(info)]) + info

    def _info_payload(self, info_id: int) -> bytes:
        if info_id == INFO_VENDOR_NAME:
            return self._string(self.vendor_name)
        if info_id == INFO_PRODUCT_NAME:
            return self._string(self.product_name)
        if info_id == INFO_SERIAL_NUMBER:
            return self._string(self.serial_number)
        if info_id == INFO_PROTOCOL_VERSION:
            return self._string(self.protocol_version)
        if info_id == INFO_TARGET_DEVICE_VENDOR:
            return self._string("Virtual")
        if info_id == INFO_TARGET_DEVICE_NAME:
            return self._string(self.board_name)
        if info_id == INFO_TARGET_BOARD_VENDOR:
            return self._string("VirtualBoard")
        if info_id == INFO_TARGET_BOARD_NAME:
            return self._string(self.board_name)
        if info_id == INFO_PRODUCT_FIRMWARE_VERSION:
            return self._string(self.firmware_version)
        if info_id == INFO_CAPABILITIES:
            # Bit0: SWD supported
            return bytes([0x01])
        if info_id == INFO_PACKET_COUNT:
            return bytes([self.packet_count & 0xFF])
        if info_id == INFO_PACKET_SIZE:
            return self.packet_size.to_bytes(2, "little")
        if info_id in (INFO_TEST_DOMAIN_TIMER, INFO_UART_RX_BUFFER_SIZE):
            return b""
        if info_id in (INFO_UART_TX_BUFFER_SIZE, INFO_SWO_BUFFER_SIZE):
            return b""
        return b""

    def _string(self, value: str) -> bytes:
        return (value + "\x00").encode("utf-8")

    def _cmd_connect(self, packet: bytes) -> bytes:
        port = packet[1] if len(packet) > 1 else 0
        if port in (0, 1):
            self.connected_port = 1
            return bytes([CMD_DAP_CONNECT, 1])
        self.connected_port = 0
        return bytes([CMD_DAP_CONNECT, 0])

    def _cmd_disconnect(self, _packet: bytes) -> bytes:
        self.connected_port = 0
        self._stop_run_loop()
        return bytes([CMD_DAP_DISCONNECT, DAP_OK])

    def _cmd_transfer_configure(self, packet: bytes) -> bytes:
        if len(packet) >= 4:
            self.transfer_config.idle_cycles = packet[1]
            self.transfer_config.retry_count = packet[2]
            self.transfer_config.match_retry = packet[3]
        return bytes([CMD_DAP_TRANSFER_CONFIGURE, DAP_OK])

    def _cmd_write_abort(self, _packet: bytes) -> bytes:
        return bytes([CMD_DAP_WRITE_ABORT, DAP_OK])

    def _cmd_swj_sequence(self, _packet: bytes) -> bytes:
        return bytes([CMD_DAP_SWJ_SEQUENCE, DAP_OK])

    def _cmd_swd_configure(self, _packet: bytes) -> bytes:
        return bytes([CMD_DAP_SWD_CONFIGURE, DAP_OK])

    def _cmd_jtag_configure(self, _packet: bytes) -> bytes:
        # JTAG not supported (SWD only)
        return bytes([CMD_DAP_JTAG_CONFIGURE, DAP_ERROR])

    def _cmd_swo_transport(self, _packet: bytes) -> bytes:
        return bytes([CMD_DAP_SWO_TRANSPORT, DAP_ERROR])

    def _cmd_delay(self, _packet: bytes) -> bytes:
        return bytes([CMD_DAP_DELAY, DAP_OK])

    def _cmd_reset_target(self, _packet: bytes) -> bytes:
        if self.debug_client:
            try:
                self.debug_client.reset()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.warning("Reset failed: %s", exc)
                return bytes([CMD_DAP_RESET_TARGET, DAP_ERROR, 0])
        return bytes([CMD_DAP_RESET_TARGET, DAP_OK, 0])

    def _cmd_transfer(self, packet: bytes) -> bytes:
        if len(packet) < 3:
            return bytes([CMD_DAP_TRANSFER, 0, DAP_TRANSFER_ERROR])
        if packet[0] != CMD_DAP_TRANSFER:
            return bytes([CMD_DAP_TRANSFER, 0, DAP_TRANSFER_ERROR])

        transfer_count = packet[2]
        offset = 3
        responses: list[int] = []
        status = DAP_TRANSFER_OK
        executed = 0

        for _ in range(transfer_count):
            if offset >= len(packet):
                status = DAP_TRANSFER_ERROR
                break
            request = packet[offset]
            offset += 1

            if request & REQ_TIME_STAMP:
                status = DAP_TRANSFER_ERROR
                break

            is_ap = bool(request & REQ_APnDP)
            is_read = bool(request & REQ_RnW)
            addr = ((request & REQ_A2) >> 2) | ((request & REQ_A3) >> 2)
            reg_addr = addr * 4

            if is_read:
                try:
                    value = self._transfer_read(is_ap, reg_addr)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logging.warning("Transfer read failed: %s", exc)
                    status = DAP_TRANSFER_FAULT
                    break
                responses.append(value)
            else:
                if offset + 4 > len(packet):
                    status = DAP_TRANSFER_ERROR
                    break
                value = int.from_bytes(packet[offset : offset + 4], "little")
                offset += 4
                try:
                    self._transfer_write(is_ap, reg_addr, value)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logging.warning("Transfer write failed: %s", exc)
                    status = DAP_TRANSFER_FAULT
                    break

            executed += 1

        resp = bytearray()
        resp.append(CMD_DAP_TRANSFER)
        resp.append(executed & 0xFF)
        resp.append(status & 0xFF)
        for value in responses:
            resp.extend(value.to_bytes(4, "little"))
        return bytes(resp)

    def _cmd_transfer_block(self, packet: bytes) -> bytes:
        if len(packet) < 5:
            return bytes([CMD_DAP_TRANSFER_BLOCK, 0, 0, DAP_TRANSFER_ERROR])
        if packet[0] != CMD_DAP_TRANSFER_BLOCK:
            return bytes([CMD_DAP_TRANSFER_BLOCK, 0, 0, DAP_TRANSFER_ERROR])

        transfer_count = int.from_bytes(packet[2:4], "little")
        request = packet[4]
        offset = 5
        responses: list[int] = []
        status = DAP_TRANSFER_OK
        executed = 0

        if request & REQ_TIME_STAMP:
            status = DAP_TRANSFER_ERROR
        else:
            is_ap = bool(request & REQ_APnDP)
            is_read = bool(request & REQ_RnW)
            addr = ((request & REQ_A2) >> 2) | ((request & REQ_A3) >> 2)
            reg_addr = addr * 4

            for _ in range(transfer_count):
                if is_read:
                    try:
                        value = self._transfer_read(is_ap, reg_addr)
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logging.warning("Transfer block read failed: %s", exc)
                        status = DAP_TRANSFER_FAULT
                        break
                    responses.append(value)
                else:
                    if offset + 4 > len(packet):
                        status = DAP_TRANSFER_ERROR
                        break
                    value = int.from_bytes(packet[offset : offset + 4], "little")
                    offset += 4
                    try:
                        self._transfer_write(is_ap, reg_addr, value)
                    except Exception as exc:  # pylint: disable=broad-exception-caught
                        logging.warning("Transfer block write failed: %s", exc)
                        status = DAP_TRANSFER_FAULT
                        break

                executed += 1

        resp = bytearray()
        resp.append(CMD_DAP_TRANSFER_BLOCK)
        resp.extend(executed.to_bytes(2, "little"))
        resp.append(status & 0xFF)
        for value in responses:
            resp.extend(value.to_bytes(4, "little"))
        return bytes(resp)

    def _transfer_read(self, is_ap: bool, reg_addr: int) -> int:
        if is_ap:
            value = self._ap_read(reg_addr)
        else:
            value = self._dp_read(reg_addr)
        self._dp_rdbuff = value
        return value & 0xFFFFFFFF

    def _transfer_write(self, is_ap: bool, reg_addr: int, value: int) -> None:
        if is_ap:
            self._ap_write(reg_addr, value)
        else:
            self._dp_write(reg_addr, value)

    def _dp_read(self, reg_addr: int) -> int:
        dp_addr = self._dp_reg_addr(reg_addr)
        if dp_addr == 0x00:
            return 0x2BA01477  # IDCODE (generic)
        if dp_addr == 0x04:
            return self._dp_ctrl_stat
        if dp_addr == 0x08:
            return self._dp_select
        if dp_addr == 0x0C:
            return self._dp_rdbuff
        return 0

    def _dp_write(self, reg_addr: int, value: int) -> None:
        dp_addr = self._dp_reg_addr(reg_addr)
        if dp_addr == 0x04:
            self._dp_ctrl_stat = value & 0xFFFFFFFF
        elif dp_addr == 0x08:
            self._dp_select = value & 0xFFFFFFFF

    def _ap_read(self, reg_addr: int) -> int:
        ap_addr = self._ap_reg_addr(reg_addr)
        if ap_addr == 0x00:
            return self._ap_csw
        if ap_addr == 0x04:
            return self._ap_tar
        if ap_addr == 0x0C:
            return self._read_mem_ap()
        if ap_addr == 0xFC:
            return self._ap_idr
        return 0

    def _ap_write(self, reg_addr: int, value: int) -> None:
        ap_addr = self._ap_reg_addr(reg_addr)
        if ap_addr == 0x00:
            self._ap_csw = value & 0xFFFFFFFF
        elif ap_addr == 0x04:
            self._ap_tar = value & 0xFFFFFFFF
        elif ap_addr == 0x0C:
            self._write_mem_ap(value)

    def _dp_reg_addr(self, reg_addr: int) -> int:
        dp_bank = self._dp_select & 0xF
        return (dp_bank << 4) | (reg_addr & 0xC)

    def _ap_reg_addr(self, reg_addr: int) -> int:
        ap_bank = (self._dp_select >> 4) & 0xF
        return (ap_bank << 4) | (reg_addr & 0xC)

    def _csw_size(self) -> int:
        size = self._ap_csw & 0x7
        if size == 0:
            return 1
        if size == 1:
            return 2
        if size == 2:
            return 4
        return 4

    def _csw_autoinc(self) -> bool:
        inc = (self._ap_csw >> 4) & 0x3
        return inc in (1, 2)

    def _read_mem_ap(self) -> int:
        size = self._csw_size()
        address = self._ap_tar
        value = self._read_target_memory(address, size)
        if self._csw_autoinc():
            self._ap_tar = (self._ap_tar + size) & 0xFFFFFFFF
        return value

    def _write_mem_ap(self, value: int) -> None:
        size = self._csw_size()
        address = self._ap_tar
        self._write_target_memory(address, size, value)
        if self._csw_autoinc():
            self._ap_tar = (self._ap_tar + size) & 0xFFFFFFFF

    def _read_target_memory(self, address: int, size: int) -> int:
        if self._is_debug_addr(address):
            return self._debug_regs.read(address, size)
        if self.debug_client is None:
            return 0
        data = self.debug_client.read_mem(address, size)
        return int.from_bytes(data, "little") if data else 0

    def _write_target_memory(self, address: int, size: int, value: int) -> None:
        if self._is_debug_addr(address):
            self._debug_regs.write(address, size, value)
            if address == DHCSR_ADDR:
                self._sync_run_state()
            return
        if self.debug_client is None:
            return
        data = value.to_bytes(4, "little")[:size]
        self.debug_client.write_mem(address, data)

    def _is_debug_addr(self, address: int) -> bool:
        return 0xE0000000 <= address <= 0xE00FFFFF

    def _sync_run_state(self) -> None:
        # Keep run loop aligned with DHCSR state.
        if self._debug_regs.is_halted():
            self._stop_run_loop()
        else:
            self._start_run_loop()

    def _start_run_loop(self) -> None:
        if self.debug_client is None:
            return
        with self._run_lock:
            if self._run_active:
                return
            self._run_active = True
            self._run_thread = threading.Thread(
                target=self._run_loop, daemon=True
            )
            self._run_thread.start()

    def _stop_run_loop(self) -> None:
        with self._run_lock:
            self._run_active = False

    def _run_loop(self) -> None:
        while True:
            with self._run_lock:
                if not self._run_active:
                    break
            if self.debug_client is None:
                break
            try:
                result = self.debug_client.step()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logging.warning("Run loop stopped: %s", exc)
                self._debug_regs.set_halted(True)
                self._stop_run_loop()
                break
            reason = result.get("reason")
            if reason and reason != "step":
                self._debug_regs.set_halted(True)
                self._stop_run_loop()
                break
            time.sleep(0)


def run_proxy(args: argparse.Namespace) -> int:
    debug_client = None
    if not args.no_debug_server:
        debug_client = DebugClient(args.debug_host, args.debug_port)

    emulator = CmsisDapEmulator(
        board_name=args.board,
        debug_client=debug_client,
        packet_size=args.packet_size,
    )

    if args.bridge:
        bridge = HidBridge(args.bridge_path, args.packet_size)
        try:
            bridge.open()
            logging.info("Connected to bridge %s", args.bridge_path)
            while True:
                data = bridge.read_packet()
                if not data:
                    break
                response = emulator.handle_packet(data)
                bridge.write_packet(response)
        finally:
            bridge.close()
        return 0

    with socket.create_server((args.listen_host, args.listen_port)) as server:
        logging.info("Listening for driver on %s:%d", args.listen_host, args.listen_port)
        while True:
            conn, addr = server.accept()
            logging.info("Driver connected from %s:%d", addr[0], addr[1])
            with conn:
                while True:
                    data = _recv_exact(conn, args.packet_size)
                    if not data:
                        break
                    response = emulator.handle_packet(data)
                    conn.sendall(response)
            logging.info("Driver disconnected")

    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CMSIS-DAP v1 proxy (WIP)")
    parser.add_argument("--board", required=True, help="Board name (for DAP_Info)")
    parser.add_argument(
        "--listen-host", default="127.0.0.1", help="Proxy listen host"
    )
    parser.add_argument("--listen-port", type=int, default=7230)
    parser.add_argument("--packet-size", type=int, default=DAP_PACKET_SIZE)
    parser.add_argument(
        "--bridge",
        action="store_true",
        help="Use Windows bridge device instead of TCP",
    )
    parser.add_argument(
        "--bridge-path",
        default="\\\\.\\CmsisDapBridge",
        help="Bridge device path",
    )
    parser.add_argument(
        "--debug-host", default="127.0.0.1", help="Simulator debug server host"
    )
    parser.add_argument("--debug-port", type=int, default=3333)
    parser.add_argument(
        "--no-debug-server",
        action="store_true",
        help="Run without connecting to the simulator debug server",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args()
    return run_proxy(args)


if __name__ == "__main__":
    raise SystemExit(main())
