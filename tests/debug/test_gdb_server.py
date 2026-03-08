from simulator.debug.gdb_server import GdbRemoteServer, GdbTarget


class DummySnapshotRegister:
    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value


class DummySnapshot:
    def __init__(self, xpsr: int):
        self.registers = [DummySnapshotRegister("XPSR", xpsr)]


class DummyCPU:
    def __init__(self):
        self.regs = {idx: 0 for idx in range(16)}
        self.regs[15] = 0x1001

    def get_register(self, index: int) -> int:
        return self.regs[index]

    def set_register(self, index: int, value: int) -> None:
        self.regs[index] = value

    def get_snapshot(self):
        return DummySnapshot(0x01000000)


class DummyBoard:
    def __init__(self):
        self.cpu = DummyCPU()
        self.memory = {}
        self.steps = 0

    def read(self, address: int, size: int = 4) -> int:
        return self.memory.get(address, 0)

    def write(self, address: int, size: int, value: int) -> None:
        self.memory[address] = value & 0xFF

    def step(self, cycles: int = 1) -> None:
        self.steps += cycles
        self.cpu.set_register(15, (self.cpu.get_register(15) + 2) | 1)


def test_register_roundtrip_and_breakpoint_continue():
    target = GdbTarget(board=DummyBoard(), max_continue_steps=10)
    server = GdbRemoteServer(target)

    g_response = server._handle_packet("g")
    assert len(bytes.fromhex(g_response)) == 17 * 4  # nosec B101

    new_payload = (b"\x11\x00\x00\x00" * 17).hex()
    assert server._handle_packet(f"G{new_payload}") == "OK"  # nosec B101
    assert target.board.cpu.get_register(0) == 0x11  # nosec B101

    assert server._handle_packet("Z0,1004,2") == "OK"  # nosec B101
    target.board.cpu.set_register(15, 0x1001)
    assert server._handle_packet("c") == "T05thread:1;"  # nosec B101


def test_memory_read_write_packets():
    target = GdbTarget(board=DummyBoard())
    server = GdbRemoteServer(target)

    assert server._handle_packet("M2000,4:01020304") == "OK"  # nosec B101
    assert server._handle_packet("m2000,4") == "01020304"  # nosec B101


def test_query_packets():
    target = GdbTarget(board=DummyBoard())
    server = GdbRemoteServer(target)

    assert "PacketSize" in server._handle_packet(
        "qSupported:multiprocess+"
    )  # nosec B101
    assert server._handle_packet("qfThreadInfo") == "m1"  # nosec B101
    assert server._handle_packet("qsThreadInfo") == "l"  # nosec B101
