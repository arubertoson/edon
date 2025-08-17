from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from edon_ui.views.scene import GraphicsScene
from edon_ui.widgets.node_spawner import NodeSpawningPanel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow, QWidget


class AppContextMenu(QMenu):
    def __init__(
        self,
        main_window: QMainWindow,
        position: QPoint,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.menu_position = position
        self.main_window = main_window

        from edon_ui.views.viewer import GraphicsView

        self.view = cast(GraphicsView, parent)

        self._add_file_actions()
        self.addSeparator()
        self._add_node_actions()

    def _add_file_actions(self):
        quit_action = QAction("Close", self)
        quit_action.triggered.connect(self.main_window.close)
        self.addAction(quit_action)

    def _add_node_actions(self):
        add_node_action = QAction("Add New Node", self)
        if self.menu_position is None or self.view is None:
            add_node_action.setEnabled(False)
        else:
            add_node_action.triggered.connect(self._request_node_spawner)
        self.addAction(add_node_action)

    def _request_node_spawner(self) -> None:
        """
        Handles the request to show the NodeSpawningPanel.
        """
        if not self.view or not self.menu_position:
            return

        # self.menu_position is the global click position.
        # NodeSpawningPanel's spawn_position needs to be in scene coordinates.
        # First, map the global menu position to view coordinates.
        spawn_position_view: QPoint = self.view.mapFromGlobal(self.menu_position)
        # Then, map the view coordinates to scene coordinates.
        spawn_position_scene: QPointF = self.view.mapToScene(spawn_position_view)
        panel_display_position_global: QPointF = QPointF(self.menu_position)

        # Parent the panel to the view for proper lifecycle management
        node_spawner = NodeSpawningPanel(
            controller=self.view._controller,
            spawn_position=spawn_position_scene,
            parent=self.view,
        )
        node_spawner.show_panel(panel_display_position_global)

    # Removed _request_add_new_node and _quit_application as they are now handled by emitting signals
    # and the connections will be made by the creator of this menu.

    # Example of how you might add other sections:
    # def _add_edit_actions(self):
    #     undo_action = QAction("Undo (Placeholder)", self)
    #     # undo_action.triggered.connect(self.parent_widget.some_undo_slot)
    #     self.addAction(undo_action)

    # def _add_node_actions(self):
    #     add_node_action = QAction("Add Node (Placeholder)", self)
    #     # add_node_action.triggered.connect(self.parent_widget.canvas.some_add_node_slot)
    #     self.addAction(add_node_action)
