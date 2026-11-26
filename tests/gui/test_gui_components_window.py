"""Components, board canvas, main window and the application entry point (offscreen Qt)."""

from __future__ import annotations

import signal
import socket
import threading
import types
from pathlib import Path

import pytest
from PySide6 import QtCore, QtWidgets

from simulator_gui import app as gui_app
from simulator_gui.backend import BoardBackend
from simulator_gui.components.base import ComponentController
from simulator_gui.config import ComponentConfig, HardwareBinding, load_gui_config
from simulator_gui.controller import SimulationController, SimulationState
from simulator_gui.registry import ComponentRegistry, default_registry
from simulator_gui.view.main_window import MainWindow
from simulator_gui.view.register_panel import RegisterPanel

BOARDS = Path(__file__).resolve().parents[2] / "simulator_gui" / "boards"
GPIOF_DATA = 0x400253FC


def _component(ctype, direction="output", mask=0x02, address=GPIOF_DATA, **visual):
    cfg = ComponentConfig(
        "c", ctype, None, visual, HardwareBinding(address, mask, 4, False, direction)
    )
    return default_registry().create(cfg)


def test_registry_rejects_unknown_types_and_is_case_insensitive():
    reg = ComponentRegistry()
    reg.register("led", lambda cfg: "made")
    cfg = ComponentConfig("x", "LED", None, {}, HardwareBinding(0, 1))
    assert reg.create(cfg) == "made"  # nosec B101
    with pytest.raises(ValueError):
        reg.create(ComponentConfig("x", "KNOB", None, {}, HardwareBinding(0, 1)))


def test_led_follows_the_gpio_register(qapp, booted_board):
    board = booted_board("tm4c123")
    backend = BoardBackend(board)
    led = _component("LED", mask=0x02)
    ctrl = led.controller
    ctrl.attach_backend(backend)
    ctrl.update(backend)
    assert led.view._on is False  # nosec B101
    board.write(GPIOF_DATA, 4, 0x02)
    ctrl.update(backend)
    assert led.view._on is True  # nosec B101
    board.write(GPIOF_DATA, 4, 0x00)
    ctrl.update(backend)
    assert led.view._on is False  # nosec B101


def test_led_invert_and_no_mask(qapp, booted_board):
    board = booted_board("tm4c123")
    backend = BoardBackend(board)
    inverted = ComponentConfig(
        "i", "LED", None, {}, HardwareBinding(GPIOF_DATA, 0x02, 4, True, "output")
    )
    inst = default_registry().create(inverted)
    inst.controller.update(backend)
    assert inst.view._on is True  # nosec B101  (bit clear + invert = on)
    nomask = default_registry().create(
        ComponentConfig(
            "n", "LED", None, {}, HardwareBinding(GPIOF_DATA, 0, 4, False, "output")
        )
    )
    board.write(GPIOF_DATA, 4, 0x08)
    nomask.controller.update(backend)
    assert nomask.view._on is True  # nosec B101  (mask 0 = any bit)


def test_button_writes_the_pin_while_pressed(qapp, booted_board):
    board = booted_board("tm4c123")
    backend = BoardBackend(board)
    btn = _component("BUTTON", direction="input", mask=0x10)
    btn.controller.attach_backend(backend)
    btn.view.pressed.emit()
    assert board.read(GPIOF_DATA, 4) & 0x10  # nosec B101
    btn.view.released.emit()
    assert not board.read(GPIOF_DATA, 4) & 0x10  # nosec B101
    btn.controller.update(backend)  # momentary: nothing to poll


def test_button_ignores_output_bindings_and_missing_backend(qapp, booted_board):
    board = booted_board("tm4c123")
    out = _component("BUTTON", direction="output", mask=0x10)
    out.controller.attach_backend(BoardBackend(board))
    out.view.pressed.emit()
    assert board.read(GPIOF_DATA, 4) == 0  # nosec B101
    detached = _component("BUTTON", direction="input", mask=0x10)
    detached.view.pressed.emit()  # no backend attached: must not raise


def test_switch_toggles_the_pin_and_mirrors_outputs(qapp, booted_board):
    board = booted_board("tm4c123")
    backend = BoardBackend(board)
    sw = _component("SWITCH", direction="input", mask=0x01)
    sw.controller.attach_backend(backend)
    sw.view.toggled.emit(True)
    assert board.read(GPIOF_DATA, 4) & 0x01  # nosec B101
    sw.view.toggled.emit(False)
    assert not board.read(GPIOF_DATA, 4) & 0x01  # nosec B101
    out = _component("SWITCH", direction="output", mask=0x04)
    out.controller.attach_backend(backend)
    board.write(GPIOF_DATA, 4, 0x04)
    out.controller.update(backend)
    assert out.view._on is True  # nosec B101


def test_component_views_paint_without_errors(qapp):
    from PySide6 import QtGui

    image = QtGui.QImage(60, 60, QtGui.QImage.Format_ARGB32)
    painter = QtGui.QPainter(image)
    for ctype in ("LED", "BUTTON", "SWITCH"):
        inst = _component(ctype, direction="input" if ctype != "LED" else "output")
        inst.view.paint(painter, None)
        if hasattr(inst.view, "set_on"):
            inst.view.set_on(True)
            inst.view.paint(painter, None)
    painter.end()


def test_register_panel_shows_registers_and_flags(qapp, booted_board):
    panel = RegisterPanel()
    snap = booted_board("tm4c123").cpu.get_snapshot()
    panel.update_snapshot(snap)
    panel.update_snapshot(snap)  # second call reuses the rows
    assert panel._table.rowCount() == len(snap.registers)  # nosec B101
    assert panel._table.item(0, 1).text().startswith("0x")  # nosec B101
    assert panel._flags_label.text().startswith("FLAGS: ")  # nosec B101


@pytest.mark.parametrize("key", ["tm4c123", "stm32c031", "stm32f4"])
def test_main_window_ticks_and_shows_the_led_state(qapp, booted_board, key):
    board = booted_board(key)
    cfg = load_gui_config(BOARDS / f"{key}.yaml")
    registry = default_registry()
    instances = [registry.create(c) for c in cfg.components]
    controller = SimulationController(
        BoardBackend(board), [i.controller for i in instances]
    )
    window = MainWindow(controller, cfg, instances, cycles_per_tick=10, tick_ms=1000)
    assert window.windowTitle() == f"{cfg.board_name} Simulator"  # nosec B101
    assert controller.state == SimulationState.RUNNING  # nosec B101
    window._tick()
    window._tick()
    assert window._top_bar._state_label.text() == "Running"  # nosec B101
    assert window._register_panel._table.rowCount() > 0  # nosec B101
    window.resize(cfg.canvas.width + 300, cfg.canvas.height + 120)
    window.show()
    qapp.processEvents()
    window.close()


def test_main_window_external_clock_does_not_step(qapp, booted_board):
    board = booted_board("tm4c123")
    cfg = load_gui_config(BOARDS / "tm4c123.yaml")
    instances = [default_registry().create(c) for c in cfg.components]
    controller = SimulationController(
        BoardBackend(board), [i.controller for i in instances]
    )
    window = MainWindow(controller, cfg, instances, external_clock=True, tick_ms=1000)
    before = board.cpu.get_register(15)
    window._tick()
    assert controller.state == SimulationState.EXTERNAL  # nosec B101
    assert board.cpu.get_register(15) == before  # nosec B101  (debugger owns the clock)
    assert window._top_bar._state_label.text() == "External"  # nosec B101


def test_canvas_uses_fallback_layout_for_components_without_position(qapp):
    from simulator_gui.view.board_canvas import BoardCanvas

    cfg = load_gui_config(BOARDS / "tm4c123.yaml")
    unplaced = [
        ComponentConfig(
            f"u{i}",
            "LED",
            None,
            {},
            HardwareBinding(GPIOF_DATA, 1 << i, 4, False, "output"),
        )
        for i in range(3)
    ]
    instances = [default_registry().create(c) for c in unplaced]
    canvas = BoardCanvas(cfg)
    canvas.set_components(instances)
    xs = [inst.view.pos().x() for inst in instances]
    assert xs == sorted(xs) and len(set(xs)) == 3  # nosec B101
    canvas.resize(500, 400)
    canvas.show()
    qapp.processEvents()


def test_canvas_without_a_background_image_falls_back_to_a_blank_pixmap(qapp, tmp_path):
    from simulator_gui.view.board_canvas import BoardCanvas

    cfg = load_gui_config(BOARDS / "tm4c123.yaml")
    object.__setattr__(cfg, "background_image", str(tmp_path / "missing.png"))
    canvas = BoardCanvas(cfg)
    assert canvas.scene().sceneRect().width() == cfg.canvas.width  # nosec B101


# ---------------------------------------------------------------- application entry point
def test_parse_args_and_board_key_resolution():
    args = gui_app._parse_args(
        ["--board", "stm32f4", "--gdb-port", "4444", "--cycles", "5"]
    )
    assert (args.board, args.gdb_port, args.cycles) == (
        "stm32f4",
        4444,
        5,
    )  # nosec B101
    assert args.gdb_max_continue_steps == 0  # nosec B101  (unlimited: Ctrl+C stops)
    assert gui_app._resolve_board_key("tm4c123", "ignored") == "tm4c123"  # nosec B101
    assert gui_app._resolve_board_key(None, "STM32C031") == "stm32c031"  # nosec B101
    assert gui_app._resolve_board_key(None, "nope") is None  # nosec B101
    with pytest.raises(SystemExit):
        gui_app._parse_args(["--board", "no-such-board"])


def _fake_application(monkeypatch, exec_fn):
    """run_gui creates its own QApplication; reuse the session one and fake exec()."""

    class FakeApp:
        def exec(self):
            return exec_fn()

    monkeypatch.setattr(
        gui_app, "QtWidgets", types.SimpleNamespace(QApplication=lambda argv: FakeApp())
    )


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_run_gui_starts_gdb_server_hands_the_clock_to_the_debugger_and_quits_on_ctrl_c(
    qapp, monkeypatch, tmp_path
):
    captured = {}

    def fake_exec():
        # the GDB server thread is up and accepts connections while the GUI runs
        deadline = threading.Event()
        for _ in range(50):
            try:
                with socket.create_connection(
                    ("127.0.0.1", captured["port"]), timeout=0.5
                ):
                    captured["connected"] = True
                break
            except OSError:
                deadline.wait(0.05)
        captured["sigint"] = signal.getsignal(signal.SIGINT)
        captured["windows"] = [
            w.windowTitle()
            for w in QtWidgets.QApplication.topLevelWidgets()
            if w.isVisible()
        ]
        return 0

    port = _free_port()
    captured["port"] = port
    _fake_application(monkeypatch, fake_exec)
    previous = signal.getsignal(signal.SIGINT)
    try:
        code = gui_app.run_gui(
            ["--board", "tm4c123", "--gdb-port", str(port), "--tick-ms", "1000"]
        )
    finally:
        signal.signal(signal.SIGINT, previous)
    assert code == 0  # nosec B101
    assert captured.get("connected") is True  # nosec B101
    assert captured["sigint"] == signal.SIG_DFL  # nosec B101  (Ctrl+C quits the GUI)
    assert any("TM4C123" in t for t in captured["windows"])  # nosec B101


def test_run_gui_with_firmware_and_without_debugger(
    qapp, monkeypatch, tmp_path, booted_board, make_boot_image
):
    board = booted_board("stm32f4")
    image = tmp_path / "fw.bin"
    image.write_bytes(make_boot_image(board))
    _fake_application(monkeypatch, lambda: 7)
    previous = signal.getsignal(signal.SIGINT)
    try:
        assert (
            gui_app.run_gui(
                ["--board", "stm32f4", "--firmware", str(image), "--tick-ms", "1000"]
            )
            == 7
        )  # nosec B101
    finally:
        signal.signal(signal.SIGINT, previous)


def test_run_gui_accepts_an_external_board_lock_and_clock(
    qapp, monkeypatch, booted_board
):
    board = booted_board("tm4c123")
    lock = threading.RLock()
    _fake_application(monkeypatch, lambda: 0)
    previous = signal.getsignal(signal.SIGINT)
    try:
        code = gui_app.run_gui(
            ["--tick-ms", "1000"],
            board=board,
            board_key="tm4c123",
            lock=lock,
            external_clock=True,
        )
    finally:
        signal.signal(signal.SIGINT, previous)
    assert code == 0  # nosec B101
