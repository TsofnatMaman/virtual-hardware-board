"""CMSIS-DAP emulator (tools/cmsis_dap_proxy) driven like Keil does, against a real board."""

from __future__ import annotations

import importlib.util
import struct
import sys
from pathlib import Path

import pytest

pytest.importorskip("unicorn")

from simulator import create_board  # noqa: E402
from simulator.debug.session import DebugSession  # noqa: E402

PROXY_PATH = (
    Path(__file__).resolve().parents[2] / "tools" / "cmsis_dap_proxy" / "proxy.py"
)
spec = importlib.util.spec_from_file_location("cmsis_dap_proxy", PROXY_PATH)
proxy = importlib.util.module_from_spec(spec)
sys.modules["cmsis_dap_proxy"] = proxy  # dataclasses needs the module registered
spec.loader.exec_module(proxy)

DHCSR, DCRSR, DCRDR = 0xE000EDF0, 0xE000EDF4, 0xE000EDF8
APnDP, RnW = 1, 2


class SessionClient:
    """Stands in for the TCP DebugClient: same methods, talks to a DebugSession directly."""

    def __init__(self, session):
        self.s = session

    def read_mem(self, address, size):
        return self.s.read_memory(address, size)

    def write_mem(self, address, data):
        self.s.write_memory(address, data)

    def read_reg(self, index):
        return self.s.read_register(index)

    def write_reg(self, index, value):
        self.s.write_register(index, value)

    def reset(self):
        self.s.reset()

    def step(self):
        return self.s.step().__dict__

    def halt(self):
        self.s.request_halt()

    def set_breakpoint(self, address):
        self.s.add_breakpoint(address)

    def clear_breakpoint(self, address):
        self.s.remove_breakpoint(address)


@pytest.fixture(name="dap")
def fixture_dap():
    board = create_board("tm4c123")
    session = DebugSession(board)
    emu = proxy.CmsisDapEmulator("tm4c123", SessionClient(session))

    class Dap:
        def __init__(self):
            self.emu, self.board, self.session = emu, board, session

        def tx(self, *payload) -> bytes:
            return emu.handle_packet(bytes(payload).ljust(64, b"\0"))

        def dp_write(self, reg, value):
            r = self.tx(0x05, 0, 1, (reg & 0xC), *struct.pack("<I", value))
            assert r[1] == 1 and r[2] == proxy.DAP_TRANSFER_OK, r[:4].hex()

        def ap_write(self, reg, value):
            r = self.tx(0x05, 0, 1, APnDP | (reg & 0xC), *struct.pack("<I", value))
            assert r[1] == 1 and r[2] == proxy.DAP_TRANSFER_OK, r[:4].hex()

        def ap_read(self, reg) -> int:
            r = self.tx(
                0x05, 0, 2, APnDP | RnW | (reg & 0xC), RnW | 0x0C
            )  # AP read, then DP RDBUFF
            assert r[1] == 2 and r[2] == proxy.DAP_TRANSFER_OK, r[:4].hex()
            return struct.unpack("<I", r[3:7])[0]

        def w32(self, address, value):
            self.ap_write(0x04, address)  # TAR
            self.ap_write(0x0C, value)  # DRW

        def r32(self, address) -> int:
            self.ap_write(0x04, address)
            return self.ap_read(0x0C)

    dap = Dap()
    dap.dp_write(0x08, 0)  # DP SELECT = 0 (AP bank 0)
    dap.ap_write(0x00, 0x23000002)  # CSW: 32-bit, no auto-increment
    return dap


def test_unknown_and_empty_commands_are_errors():
    emu = proxy.CmsisDapEmulator("tm4c123", None)
    assert emu.handle_packet(b"")[0] == proxy.DAP_ERROR  # nosec B101
    assert (
        emu.handle_packet(bytes([0x6B]).ljust(64, b"\0"))[0] == proxy.DAP_ERROR
    )  # nosec B101


def test_dap_info_identifies_a_cmsis_dap_probe(dap):
    # Keil only accepts the device if its product string contains "CMSIS-DAP".
    product = dap.tx(0x00, proxy.INFO_PRODUCT_NAME)
    assert b"CMSIS-DAP" in product[2 : 2 + product[1]]  # nosec B101
    packet_size = dap.tx(0x00, proxy.INFO_PACKET_SIZE)
    assert struct.unpack("<H", packet_size[2:4])[0] == 64  # nosec B101
    assert dap.tx(0x00, 0xEE)[1] == 0  # nosec B101  (unknown info id: empty answer)


def test_connect_configure_and_housekeeping_commands(dap):
    assert dap.tx(0x02, 0x01)[:2] == bytes([0x02, 0x01])  # nosec B101  (SWD selected)
    for cmd in (0x04, 0x08, 0x09, 0x12, 0x13, 0x15, 0x17):
        assert dap.tx(cmd, 0, 0, 0, 0)[0] == cmd  # nosec B101  (acknowledged)
    assert dap.tx(0x03)[:2] == bytes([0x03, proxy.DAP_OK])  # nosec B101  (disconnect)


def test_mem_ap_reads_and_writes_sram_and_flash(dap):
    dap.w32(0x20000100, 0xCAFEBABE)
    assert dap.r32(0x20000100) == 0xCAFEBABE  # nosec B101
    assert (
        dap.board.read(0x20000100, 4) == 0xCAFEBABE
    )  # nosec B101  (really in the simulator)
    flash = dap.board.address_space.flash.base
    dap.w32(flash, 0x2000F000)  # a flash download, one word at a time like Keil
    assert dap.r32(flash) == 0x2000F000  # nosec B101


def test_block_transfer_reads_consecutive_words(dap):
    dap.session.write_memory(
        0x20000200, struct.pack("<4I", 0x1000, 0x1001, 0x1002, 0x1003)
    )
    dap.ap_write(0x00, 0x23000012)  # CSW: 32-bit with address auto-increment
    dap.ap_write(0x04, 0x20000200)
    r = dap.tx(0x06, 0, 4, 0, APnDP | RnW | 0x0C)  # DAP_TransferBlock: 4 words from DRW
    assert struct.unpack("<H", r[1:3])[0] == 4  # nosec B101
    assert r[3] == proxy.DAP_TRANSFER_OK  # nosec B101
    assert struct.unpack("<4I", r[4:20]) == (
        0x1000,
        0x1001,
        0x1002,
        0x1003,
    )  # nosec B101


def test_halt_registers_and_single_step_through_the_core_debug_registers(dap):
    base = dap.board.address_space.flash.base
    # download a vector table + NOPs, then halt, like Keil's "Download" followed by "Reset"
    dap.w32(base, 0x20001000)
    dap.w32(base + 4, base + 9)
    dap.session.reset()
    dap.w32(DHCSR, 0xA05F0003)  # DBGKEY | C_HALT | C_DEBUGEN
    status = dap.r32(DHCSR)
    assert (
        status & (1 << 17) and status & (1 << 16) and status & 1
    )  # nosec B101  (S_HALT, S_REGRDY, C_DEBUGEN)

    def core_reg(n):
        dap.w32(DCRSR, n)  # select register n for reading
        return dap.r32(DCRDR)

    pc0 = core_reg(15)
    dap.w32(DHCSR, 0xA05F0005)  # C_STEP | C_DEBUGEN
    assert core_reg(15) == pc0 + 2  # nosec B101  (one 16-bit instruction)
    dap.w32(DCRDR, 0x1234)
    dap.w32(DCRSR, (1 << 16) | 3)  # write R3
    assert dap.session.read_register(3) == 0x1234  # nosec B101
    assert core_reg(13) == 0x20001000  # nosec B101  (SP loaded from the vector table)


def test_breakpoint_comparators_reach_the_simulator(dap):
    base = dap.board.address_space.flash.base
    dap.w32(0xE0002000, 0x3)  # FP_CTRL: ENABLE | KEY
    dap.w32(0xE0002008, (base + 0x20) | 1)  # FP_COMP0: address + ENABLE
    assert (base + 0x20) in dap.session.breakpoints  # nosec B101
    dap.w32(0xE0002008, 0)
    assert (base + 0x20) not in dap.session.breakpoints  # nosec B101
