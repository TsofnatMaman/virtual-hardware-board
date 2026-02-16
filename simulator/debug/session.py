"""Debug session shared by every external-debugger front end.

``DebugSession`` is the single place that knows how to halt, step, run,
read/write registers and memory, and manage breakpoints on a ``Board``.
Protocol front ends are thin adapters on top of it:

* :class:`simulator.debug.gdb_server.GdbTarget` - GDB remote serial protocol
  (VS Code, ``arm-none-eabi-gdb``, Keil's GDB mode).
* :class:`simulator.debug.server.DebugServer` - line-delimited JSON over TCP,
  used by the CMSIS-DAP proxy (``tools/cmsis_dap_proxy``) for Keil.

Programming flash through the debugger marks the session as "needs reset":
the next ``step``/``run`` resets the board first, like a real target after a
download.
"""

from __future__ import annotations

import binascii
import threading
from dataclasses import dataclass
from typing import Any, Callable

from simulator.core.exceptions import SimulatorError
from simulator.interfaces.board import Board

_ADDRESS_MASK = 0xFFFFFFFE
_CORE_REGISTER_COUNT = 16


@dataclass(frozen=True)
class StopReason:
    """Why execution stopped."""

    reason: str  # "step" | "breakpoint" | "halt" | "limit" | "fault"
    address: int | None = None
    detail: str | None = None


def _bytes_to_hex(data: bytes) -> str:
    return binascii.hexlify(data).decode("ascii")


def _hex_to_bytes(data_hex: str) -> bytes:
    return binascii.unhexlify(data_hex.encode("ascii"))


class DebugSession:
    """Thread-safe debug session bound to a single board.

    ``lock`` should be shared with anything else that touches the board
    (for example the GUI backend) so a debugger and the GUI never step the
    CPU at the same time.
    """

    def __init__(self, board: Board, lock: threading.RLock | None = None):
        self.board = board
        self.breakpoints: set[int] = set()
        self.needs_reset = False
        self._halt = threading.Event()
        self._lock = lock or threading.RLock()

    # -- control ---------------------------------------------------------
    def request_halt(self) -> None:
        """Ask a running :meth:`run` loop to stop (callable from any thread)."""
        self._halt.set()

    def clear_halt(self) -> None:
        self._halt.clear()

    def reset(self) -> None:
        with self._lock:
            self.board.reset()
            self.needs_reset = False

    def _ensure_runtime_reset(self) -> None:
        if self.needs_reset:
            self.board.reset()
            self.needs_reset = False

    # -- breakpoints -----------------------------------------------------
    def add_breakpoint(self, address: int) -> None:
        self.breakpoints.add(address & _ADDRESS_MASK)

    def remove_breakpoint(self, address: int) -> None:
        self.breakpoints.discard(address & _ADDRESS_MASK)

    # -- registers -------------------------------------------------------
    def read_register(self, index: int) -> int:
        with self._lock:
            return self.board.cpu.get_register(index) & 0xFFFFFFFF

    def write_register(self, index: int, value: int) -> None:
        with self._lock:
            self.board.cpu.set_register(index, value & 0xFFFFFFFF)

    def pc(self) -> int:
        """Program counter with the Thumb bit cleared."""
        return self.read_register(15) & _ADDRESS_MASK

    def set_pc(self, address: int) -> None:
        """Set PC; the Thumb bit is always set (Cortex-M is Thumb-only)."""
        self.write_register(15, address | 1)

    def read_core_registers(self) -> list[int]:
        """Return r0-r15 followed by xPSR."""
        with self._lock:
            values = [
                self.board.cpu.get_register(i) & 0xFFFFFFFF
                for i in range(_CORE_REGISTER_COUNT)
            ]
            snapshot = self.board.cpu.get_snapshot()
        xpsr = next((r.value for r in snapshot.registers if r.name == "XPSR"), 0)
        values.append(xpsr & 0xFFFFFFFF)
        return values

    # -- memory ----------------------------------------------------------
    def read_memory(self, address: int, size: int) -> bytes:
        """Read ``size`` bytes; raises ``SimulatorError``/``ValueError``."""
        with self._lock:
            return bytes(self.board.read(address + i, 1) for i in range(size))

    def write_memory(self, address: int, data: bytes) -> None:
        """Write bytes; raises ``SimulatorError``/``ValueError``.

        Writes that touch flash schedule a reset before the next execution.
        """
        with self._lock:
            for offset, value in enumerate(data):
                self.board.write(address + offset, 1, value)
            self._mark_reset_needed_if_flash_write(address, len(data))

    def _mark_reset_needed_if_flash_write(self, address: int, length: int) -> None:
        flash = self.board.address_space.flash
        write_end = address + max(length - 1, 0)
        if address <= flash.base + flash.size - 1 and write_end >= flash.base:
            self.needs_reset = True

    # -- execution -------------------------------------------------------
    def _step_once(self) -> StopReason | None:
        """Execute one instruction; return a ``fault`` stop on failure."""
        pc = self.pc()
        try:
            self.board.step(1)
        except (SimulatorError, ValueError) as exc:
            return StopReason(reason="fault", address=pc, detail=str(exc))
        return None

    def step(self) -> StopReason:
        """Execute exactly one instruction."""
        self.clear_halt()
        with self._lock:
            self._ensure_runtime_reset()
            fault = self._step_once()
            if fault:
                return fault
            return StopReason(reason="step", address=self.pc())

    def run(self, max_steps: int | None = None) -> StopReason:
        """Run until a breakpoint, halt request, fault or ``max_steps``.

        The first instruction always executes, so continuing from an address
        that has a breakpoint moves past it.
        """
        self.clear_halt()
        steps = 0
        while True:
            with self._lock:
                if steps == 0:
                    self._ensure_runtime_reset()
                else:
                    pc = self.pc()
                    if pc in self.breakpoints:
                        return StopReason(reason="breakpoint", address=pc)
                fault = self._step_once()
                if fault:
                    return fault
                steps += 1
                if max_steps is not None and steps >= max_steps:
                    pc = self.pc()
                    reason = "breakpoint" if pc in self.breakpoints else "limit"
                    return StopReason(reason=reason, address=pc)
            if self._halt.is_set():
                return StopReason(reason="halt", address=self.pc())

    # -- JSON request front end (CMSIS-DAP proxy) -----------------------
    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle one JSON command; never raises, errors are in the reply."""
        req_id = request.get("id")
        cmd = request.get("cmd")
        handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "hello": self._cmd_hello,
            "reset": self._cmd_reset,
            "read_mem": self._cmd_read_mem,
            "write_mem": self._cmd_write_mem,
            "read_reg": self._cmd_read_reg,
            "write_reg": self._cmd_write_reg,
            "run": self._cmd_run,
            "step": self._cmd_step,
            "halt": self._cmd_halt,
            "set_bp": self._cmd_set_bp,
            "clear_bp": self._cmd_clear_bp,
        }
        try:
            handler = handlers.get(cmd) if isinstance(cmd, str) else None
            if handler is None:
                raise ValueError(f"Unknown command '{cmd}'")
            return {"id": req_id, "ok": True, "result": handler(request)}
        except (SimulatorError, ValueError, KeyError, TypeError) as exc:
            return {"id": req_id, "ok": False, "error": str(exc)}

    def _cmd_hello(self, _request: dict[str, Any]) -> dict[str, Any]:
        return {"version": 1, "board": self.board.name}

    def _cmd_reset(self, _request: dict[str, Any]) -> dict[str, Any]:
        self.reset()
        return {"status": "ok"}

    def _cmd_read_mem(self, request: dict[str, Any]) -> dict[str, Any]:
        data = self.read_memory(int(request["address"]), int(request["size"]))
        return {"data": _bytes_to_hex(data)}

    def _cmd_write_mem(self, request: dict[str, Any]) -> dict[str, Any]:
        self.write_memory(int(request["address"]), _hex_to_bytes(request["data"]))
        return {"status": "ok"}

    def _cmd_read_reg(self, request: dict[str, Any]) -> dict[str, Any]:
        return {"value": self.read_register(int(request["index"]))}

    def _cmd_write_reg(self, request: dict[str, Any]) -> dict[str, Any]:
        self.write_register(int(request["index"]), int(request["value"]))
        return {"status": "ok"}

    def _cmd_run(self, request: dict[str, Any]) -> dict[str, Any]:
        max_steps = request.get("max_steps")
        stop = self.run(max_steps=None if max_steps is None else int(max_steps))
        return stop.__dict__

    def _cmd_step(self, _request: dict[str, Any]) -> dict[str, Any]:
        return self.step().__dict__

    def _cmd_halt(self, _request: dict[str, Any]) -> dict[str, Any]:
        self.request_halt()
        return {"status": "ok"}

    def _cmd_set_bp(self, request: dict[str, Any]) -> dict[str, Any]:
        self.add_breakpoint(int(request["address"]))
        return {"status": "ok"}

    def _cmd_clear_bp(self, request: dict[str, Any]) -> dict[str, Any]:
        self.remove_breakpoint(int(request["address"]))
        return {"status": "ok"}
