"""Debug session for external debugger integration."""

from __future__ import annotations

import binascii
import threading
from dataclasses import dataclass
from typing import Any, Callable, Literal

from simulator.interfaces.board import Board

WatchAccess = Literal["read", "write", "access"]


@dataclass(frozen=True)
class StopReason:
    reason: str
    address: int | None = None
    detail: str | None = None
    watch_id: int | None = None


def _bytes_to_hex(data: bytes) -> str:
    return binascii.hexlify(data).decode("ascii")


def _hex_to_bytes(data_hex: str) -> bytes:
    return binascii.unhexlify(data_hex.encode("ascii"))


class DebugSession:
    """Synchronous debug session bound to a single board."""

    def __init__(self, board: Board, lock: threading.RLock | None = None):
        self.board = board
        self._halt_requested = False
        self._lock = lock or threading.RLock()

    @property
    def cpu(self):
        return self.board.cpu

    def request_halt(self) -> None:
        self._halt_requested = True

    def clear_halt(self) -> None:
        self._halt_requested = False

    def reset(self) -> None:
        with self._lock:
            self.board.reset()

    def read_memory(self, address: int, size: int) -> bytes:
        with self._lock:
            mmio = self.board.address_space.mmio
            if mmio.contains(address):
                return bytes(
                    self.board.address_space.read(address + offset, 1)
                    for offset in range(size)
                )
            return self.cpu.engine.read_memory(address, size)

    def write_memory(self, address: int, data: bytes) -> None:
        with self._lock:
            mmio = self.board.address_space.mmio
            if mmio.contains(address):
                for offset, value in enumerate(data):
                    self.board.address_space.write(address + offset, 1, value)
                return

            flash = self.board.address_space.flash
            sram = self.board.address_space.sram
            if flash.contains(address):
                flash.program(address, data)
                self.cpu.engine.write_memory(address, data)
                return
            if sram.contains(address):
                for offset, value in enumerate(data):
                    sram.write(address + offset, 1, value)
                self.cpu.engine.write_memory(address, data)
                return

            # Fallback to AddressSpace for alignment checks / errors
            for offset, value in enumerate(data):
                self.board.address_space.write(address + offset, 1, value)

    def read_register(self, index: int) -> int:
        with self._lock:
            return self.cpu.get_register(index)

    def write_register(self, index: int, value: int) -> None:
        with self._lock:
            self.cpu.set_register(index, value)

    def set_breakpoint(self, address: int) -> None:
        with self._lock:
            self.cpu.add_breakpoint(address)

    def clear_breakpoint(self, address: int) -> None:
        with self._lock:
            self.cpu.remove_breakpoint(address)

    def set_watchpoint(self, address: int, size: int, access: WatchAccess) -> int:
        with self._lock:
            return self.cpu.add_watchpoint(address, size, access)

    def clear_watchpoint(self, watch_id: int) -> bool:
        with self._lock:
            return self.cpu.remove_watchpoint(watch_id)

    def step(self) -> StopReason:
        self.clear_halt()
        with self._lock:
            pc = self.cpu.get_register(15)
            if self.cpu.is_breakpoint(pc):
                return StopReason(reason="breakpoint", address=pc)

            try:
                self.cpu.step()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                return StopReason(reason="fault", address=pc, detail=str(exc))

            hit = self.cpu.consume_watch_hit()
            if hit:
                return StopReason(reason="watchpoint", address=hit.address, watch_id=hit.id)

            pc_after = self.cpu.get_register(15)
            if self.cpu.is_breakpoint(pc_after):
                return StopReason(reason="breakpoint", address=pc_after)

            return StopReason(reason="step", address=pc_after)

    def run(self, max_steps: int | None = None) -> StopReason:
        self.clear_halt()
        steps = 0

        while True:
            if self._halt_requested:
                with self._lock:
                    pc = self.cpu.get_register(15)
                return StopReason(reason="halt", address=pc)

            with self._lock:
                pc = self.cpu.get_register(15)
                if self.cpu.is_breakpoint(pc):
                    return StopReason(reason="breakpoint", address=pc)

                try:
                    self.cpu.step()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    return StopReason(reason="fault", address=pc, detail=str(exc))

                hit = self.cpu.consume_watch_hit()
                if hit:
                    return StopReason(
                        reason="watchpoint", address=hit.address, watch_id=hit.id
                    )

                steps += 1
                if max_steps is not None and steps >= max_steps:
                    pc = self.cpu.get_register(15)
                    return StopReason(reason="limit", address=pc)

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        req_id = request.get("id")
        cmd = request.get("cmd")
        if not isinstance(cmd, str):
            raise ValueError("Command must be a string")

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
            "set_wp": self._cmd_set_wp,
            "clear_wp": self._cmd_clear_wp,
        }

        try:
            handler = handlers.get(cmd)
            if handler is None:
                raise ValueError(f"Unknown command '{cmd}'")
            result = handler(request)
            return {"id": req_id, "ok": True, "result": result}
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {"id": req_id, "ok": False, "error": str(exc)}

    def _cmd_hello(self, _request: dict[str, Any]) -> dict[str, Any]:
        return {
            "version": 1,
            "board": self.board.name,
        }

    def _cmd_reset(self, _request: dict[str, Any]) -> dict[str, Any]:
        self.reset()
        return {"status": "ok"}

    def _cmd_read_mem(self, request: dict[str, Any]) -> dict[str, Any]:
        address = int(request["address"])
        size = int(request["size"])
        data = self.read_memory(address, size)
        return {"data": _bytes_to_hex(data)}

    def _cmd_write_mem(self, request: dict[str, Any]) -> dict[str, Any]:
        address = int(request["address"])
        data = _hex_to_bytes(request["data"])
        self.write_memory(address, data)
        return {"status": "ok"}

    def _cmd_read_reg(self, request: dict[str, Any]) -> dict[str, Any]:
        index = int(request["index"])
        return {"value": self.read_register(index)}

    def _cmd_write_reg(self, request: dict[str, Any]) -> dict[str, Any]:
        index = int(request["index"])
        value = int(request["value"])
        self.write_register(index, value)
        return {"status": "ok"}

    def _cmd_run(self, request: dict[str, Any]) -> dict[str, Any]:
        max_steps = request.get("max_steps")
        stop = self.run(max_steps=max_steps if max_steps is None else int(max_steps))
        return stop.__dict__

    def _cmd_step(self, _request: dict[str, Any]) -> dict[str, Any]:
        stop = self.step()
        return stop.__dict__

    def _cmd_halt(self, _request: dict[str, Any]) -> dict[str, Any]:
        self.request_halt()
        return {"status": "ok"}

    def _cmd_set_bp(self, request: dict[str, Any]) -> dict[str, Any]:
        address = int(request["address"])
        self.set_breakpoint(address)
        return {"status": "ok"}

    def _cmd_clear_bp(self, request: dict[str, Any]) -> dict[str, Any]:
        address = int(request["address"])
        self.clear_breakpoint(address)
        return {"status": "ok"}

    def _cmd_set_wp(self, request: dict[str, Any]) -> dict[str, Any]:
        address = int(request["address"])
        size = int(request["size"])
        access = request.get("access", "access")
        watch_id = self.set_watchpoint(address, size, access)
        return {"watch_id": watch_id}

    def _cmd_clear_wp(self, request: dict[str, Any]) -> dict[str, Any]:
        watch_id = int(request["watch_id"])
        return {"removed": self.clear_watchpoint(watch_id)}
