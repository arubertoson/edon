from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

if TYPE_CHECKING:
    from edon_ui.graphics.view import GraphicsView


class MainWindow(QWidget):
    MARGIN = 8

    def __init__(self, view: "GraphicsView"):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setMinimumSize(200, 200)
        self.resize(1000, 800)

        # Layout and canvas
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = view
        self.scene = view.scene()

        layout.addWidget(self.view)
        self.setLayout(layout)

        # Window movement and resize state
        self._resizing = False
        self._resize_edge = Qt.Edges()  # Store Qt.Edges

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resize_edge = self._detect_edge(event.position().toPoint())
            if self._resize_edge != Qt.Edges():  # Check if any edge was detected
                self._resizing = True
                self.windowHandle().startSystemResize(self._resize_edge)

                return event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = Qt.Edges()  # Reset

            return event.accept()
        super().mouseReleaseEvent(event)

    def _detect_edge(self, pos):
        rect = self.rect()
        margin = self.MARGIN
        edges = Qt.Edges()

        if pos.x() <= rect.x() + margin:
            edges |= Qt.LeftEdge
        if pos.x() >= rect.x() + rect.width() - margin:
            edges |= Qt.RightEdge
        if pos.y() <= rect.y() + margin:
            edges |= Qt.TopEdge
        if pos.y() >= rect.y() + rect.height() - margin:
            edges |= Qt.BottomEdge
        return edges

    def is_position_on_resize_edge(self, global_pos: QPointF) -> bool:
        """Checks if a global position is on one of the window's resize edges."""
        pos_in_local_coords = self.mapFromGlobal(global_pos).toPoint()  # Convert QPointF to QPoint
        return self._detect_edge(pos_in_local_coords) != Qt.Edges()

    def contextMenuEvent(self, event):
        """Override to prevent default context menu from interfering"""
        # This ensures our custom context menu handling works correctly in the GraphicsView
        event.accept()
