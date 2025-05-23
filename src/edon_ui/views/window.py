"""
Defines the main window for the Edon application.

This module contains the `MainWindow` class, which serves as the primary
top-level window, handling user interactions like resizing and providing
a container for the main graphics view.
"""
from typing import TYPE_CHECKING

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from edon_ui.views.scene import GraphicsScene
    from edon_ui.views.viewer import GraphicsView


class MainWindow(QMainWindow):
    """
    Main application window for Edon.

    This window is frameless and handles custom resizing logic. It contains
    the main graphics view where nodes and edges are displayed.
    """
    MARGIN: int = 8

    def __init__(self, view: "GraphicsView") -> None:
        """
        Initializes the MainWindow.

        Args:
            view: The graphics view to display in this window.
        """
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(200, 200)
        self.resize(1000, 800)

        # Layout and canvas
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view: "GraphicsView" = view
        self.view.setParent(central_widget)
        self.scene: "GraphicsScene" = view.scene()

        layout.addWidget(self.view)
        self.setCentralWidget(central_widget)

        # Window movement and resize state
        self._resizing: bool = False
        self._resize_edge: Qt.Edges = Qt.Edges()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse press events, primarily for initiating window resizing.

        If the left mouse button is pressed on a resize edge, system resizing
        is started.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._resize_edge = self._detect_edge(event.position().toPoint())
            if self._resize_edge != Qt.Edges():
                self._resizing = True
                self.windowHandle().startSystemResize(self._resize_edge)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse release events, primarily for finalizing window resizing.

        If resizing was active, it's stopped on left mouse button release.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = Qt.Edges()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _detect_edge(self, pos: QPoint) -> Qt.Edges:
        """
        Detects if a given point is on one of the window's resize edges.

        Args:
            pos: The point in local widget coordinates.

        Returns:
            A Qt.Edges enum indicating which edge(s) the point is on,
            or Qt.Edges() if none.
        """
        rect = self.rect()
        margin = self.MARGIN
        edges = Qt.Edges()

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
        """
        Checks if a global position is on one of the window's resize edges.

        Args:
            global_pos: The position in global screen coordinates.

        Returns:
            True if the position is on a resize edge, False otherwise.
        """
        pos_in_local_coords: QPoint = self.mapFromGlobal(global_pos).toPoint()
        return self._detect_edge(pos_in_local_coords) != Qt.Edges()

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Overrides the context menu event to prevent default Qt context menus
        from interfering with custom application context menus.

        Args:
            event: The context menu event.
        """
        event.accept()
