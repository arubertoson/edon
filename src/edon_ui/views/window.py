# ensure that this fiel follows our guidelines AI!
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from edon_ui.views.viewer import GraphicsView


class MainWindow(QMainWindow):
    MARGIN = 8

    def __init__(self, view: "GraphicsView"):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.FramelessWindowHint)  # type: ignore
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(200, 200)
        self.resize(1000, 800)

        # Layout and canvas
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = view
        self.view.setParent(central_widget)
        self.scene = view.scene()

        layout.addWidget(self.view)
        self.setCentralWidget(central_widget)

        # Window movement and resize state
        self._resizing = False
        self._resize_edge = Qt.Edges()  # type: ignore

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._resize_edge = self._detect_edge(event.position().toPoint())
            if self._resize_edge != Qt.Edges():  # type: ignore
                self._resizing = True
                self.windowHandle().startSystemResize(self._resize_edge)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = Qt.Edges()  # type: ignore
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _detect_edge(self, pos):
        rect = self.rect()
        margin = self.MARGIN
        edges = Qt.Edges()  # type: ignore

        if pos.x() <= rect.x() + margin:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= rect.x() + rect.width() - margin:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= rect.y() + margin:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= rect.y() + rect.height() - margin:
            edges |= Qt.Edge.BottomEdge
        return edges

    def is_position_on_resize_edge(self, global_pos: QPointF) -> bool:
        """Checks if a global position is on one of the window's resize edges."""
        pos_in_local_coords = self.mapFromGlobal(global_pos).toPoint()  # Convert QPointF to QPoint
        return self._detect_edge(pos_in_local_coords) != Qt.Edges()  # type: ignore

    def contextMenuEvent(self, event):
        """Override to prevent default context menu from interfering"""
        event.accept()
