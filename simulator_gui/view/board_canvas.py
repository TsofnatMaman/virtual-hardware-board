"""Board canvas with background image and component overlay."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from simulator_gui.config import GuiBoardConfig, Rect
from simulator_gui.layout import FlowLayoutEngine
from simulator_gui.registry import ComponentInstance


class BoardCanvas(QtWidgets.QGraphicsView):
    def __init__(self, config: GuiBoardConfig, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._config = config
        self._scene = QtWidgets.QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        self._background_item: QtWidgets.QGraphicsPixmapItem | None = None
        self._components: list[ComponentInstance] = []

        self._load_background()

    def _load_background(self) -> None:
        path = Path(self._config.background_image)
        if path.exists():
            pixmap = QtGui.QPixmap(str(path))
        else:
            pixmap = QtGui.QPixmap(self._config.canvas.width, self._config.canvas.height)
            pixmap.fill(QtGui.QColor("#1f1f1f"))

        self._scene.clear()
        self._background_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(
            QtCore.QRectF(0, 0, pixmap.width(), pixmap.height())
        )

    def set_components(self, components: list[ComponentInstance]) -> None:
        self._components = components
        for comp in components:
            self._scene.addItem(comp.view)  # type: ignore[arg-type]

        self._apply_layout()

    def _apply_layout(self) -> None:
        # Components with explicit positions
        missing = []
        for comp in self._components:
            if comp.config.position is not None:
                comp.view.set_rect(comp.config.position)  # type: ignore[attr-defined]
            else:
                missing.append(comp)

        if not missing:
            return

        fallback = self._config.fallback_layout
        if fallback.area is None:
            scene_rect = self._scene.sceneRect()
            area = Rect(
                x=scene_rect.width() * 0.05,
                y=scene_rect.height() * 0.80,
                width=scene_rect.width() * 0.9,
                height=scene_rect.height() * 0.15,
            )
        else:
            area = fallback.area

        layout = FlowLayoutEngine()
        positions = layout.layout(
            [comp.config for comp in missing],
            bounds=area,
            item_size=fallback.item_size,
            spacing=fallback.spacing,
        )

        for comp in missing:
            rect = positions.get(comp.config.id)
            if rect:
                comp.view.set_rect(rect)  # type: ignore[attr-defined]

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if self._config.canvas.scale_mode == "fit":
            self.fitInView(self._scene.sceneRect(), QtCore.Qt.KeepAspectRatio)
        elif self._config.canvas.scale_mode == "stretch":
            self.fitInView(self._scene.sceneRect(), QtCore.Qt.IgnoreAspectRatio)
