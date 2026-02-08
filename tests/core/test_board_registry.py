import pytest

from simulator.core.board import (
    BoardRegistry,
    create_board,
    get_board,
    list_available_boards,
    register_board,
    verify_boards_registered,
)


class DummyBoard:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_board_registry_basic_operations():
    registry = BoardRegistry()
    registry.register("dummy", DummyBoard)
    assert registry.get("dummy") is DummyBoard
    assert registry.list_boards() == ["dummy"]

    instance = registry.create("dummy", foo=1)
    assert isinstance(instance, DummyBoard)
    assert instance.kwargs == {"foo": 1}

    with pytest.raises(ValueError):
        registry.register("dummy", DummyBoard)

    with pytest.raises(ValueError):
        registry.get("missing")


def test_global_registry_functions(monkeypatch):
    registry = BoardRegistry()
    monkeypatch.setattr("simulator.core.board._REGISTRY", registry)

    register_board("dummy", DummyBoard)
    assert get_board("dummy") is DummyBoard
    assert list_available_boards() == ["dummy"]
    instance = create_board("dummy", bar=2)
    assert isinstance(instance, DummyBoard)
    assert instance.kwargs == {"bar": 2}


def test_verify_boards_registered(monkeypatch):
    registry = BoardRegistry()
    monkeypatch.setattr("simulator.core.board._REGISTRY", registry)

    with pytest.raises(RuntimeError):
        verify_boards_registered()

    registry.register("dummy", DummyBoard)
    verify_boards_registered()
