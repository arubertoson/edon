from PySide6.QtCore import QPoint  # Added Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu


class AppContextMenu(QMenu):
    def __init__(self, parent=None, position: QPoint | None = None, main_window=None, view=None):
        super().__init__(parent)
        self.menu_position = position  # Store the global position where the menu was invoked
        self.main_window = main_window
        self.view = view

        self._add_file_actions()
        self.addSeparator()
        self._add_node_actions()
        # Add more sections as needed

    def _add_file_actions(self):
        quit_action = QAction("Close", self)
        quit_action.triggered.connect(self.main_window.close)
        self.addAction(quit_action)

    def _add_node_actions(self):
        add_node_action = QAction("Add New Node", self)
        if self.menu_position is None:
            add_node_action.setEnabled(False)  # Disable if we don't have a position
        else:
            add_node_action.triggered.connect(lambda: self.view.initiate_add_new_node_request(self.menu_position))
        self.addAction(add_node_action)

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
