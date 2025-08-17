"""
Node Spawning Panel widget for Edon UI.

This widget provides a searchable list of available node types
that can be instantiated onto the graph canvas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QLineEdit, QListWidget, QVBoxLayout, QWidget
from thefuzz import fuzz

if TYPE_CHECKING:
    from edon_ui.graph.controller import WorkspaceController


class NodeSpawningPanel(QWidget):
    """
    A panel that allows users to search for and select nodes to spawn onto the canvas.
    """

    def __init__(
        self,
        controller: WorkspaceController,
        spawn_position: QPointF,
        parent: QWidget | None = None,
    ):
        """
        Initialize the NodeSpawningPanel.

        Args:
            graph_controller: The main graph controller instance.
            spawn_position: The scene position where the new node should be spawned.
            parent: The parent widget.
        """
        super().__init__(parent)

        self.controller = controller
        self.spawn_position = spawn_position

        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # A basic size, can be refined later
        self.setMinimumSize(300, 400)

        # --- UI Elements ---
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search nodes...")

        self.node_list_widget = QListWidget(self)
        self.node_list_widget.setAlternatingRowColors(True)

        self._all_node_type_names: list[str] = []

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.search_bar)
        main_layout.addWidget(self.node_list_widget)
        self.setLayout(main_layout)

        # --- Connections and Initial State ---
        self._load_all_node_types()
        self._filter_node_list()  # Initial population and selection

        self.search_bar.textChanged.connect(self._filter_node_list)
        self.node_list_widget.itemClicked.connect(self._spawn_selected_node)

    def _load_all_node_types(self) -> None:
        """
        Loads all available node type names from the graph_controller's node_registry.
        """
        self._all_node_type_names = []
        if self.controller and self.controller.node_registry:
            self._all_node_type_names = sorted(list(self.controller.node_registry.keys()))

    def _filter_node_list(self) -> None:
        """
        Filters the node_list_widget based on the search_bar's text
        using fuzzy matching and selects the first item.
        """
        search_text = self.search_bar.text().lower()
        self.node_list_widget.clear()

        FUZZY_MATCH_THRESHOLD = 60  # Minimum score to be considered a match

        if not search_text:
            # If search text is empty, show all nodes
            for name in self._all_node_type_names:
                self.node_list_widget.addItem(name)
        else:
            scored_names: list[tuple[str, int]] = []
            for name in self._all_node_type_names:
                # Using partial_ratio for better matching of substrings or partial names
                score = fuzz.partial_ratio(search_text, name.lower())
                if score >= FUZZY_MATCH_THRESHOLD:
                    scored_names.append((name, score))

            # Sort by score in descending order
            scored_names.sort(key=lambda x: x[1], reverse=True)

            for name, _ in scored_names:
                self.node_list_widget.addItem(name)

        if self.node_list_widget.count() > 0:
            self.node_list_widget.setCurrentRow(0)

    def _spawn_selected_node(self) -> None:
        """
        Spawns the currently selected node in the list and closes the panel.
        """
        current_item = self.node_list_widget.currentItem()
        if not current_item:
            if self.node_list_widget.count() > 0:
                current_item = self.node_list_widget.item(0)
            else:
                return

        if not current_item:
            return

        node_type_hint = current_item.text()

        # Spawn the node. The controller will place its top-left at self.spawn_position initially.
        # self.spawn_position is the mouse click, intended as the center.
        node_item = self.controller.handle_ui_node_creation_request(
            node_type_hint=node_type_hint, scene_pos=self.spawn_position
        )

        # Now that we have the actual NodeItem, get its dimensions
        rect = node_item.boundingRect()
        offset = QPointF(rect.width() / 2.0, rect.height() / 2.4)

        # Calculate the correct top-left position for the node
        # so its center aligns with self.spawn_position.
        final_node_pos = self.spawn_position - offset
        node_item.setPos(final_node_pos)

        logger.info(
            f"Spawning node of type '{node_type_hint}'. Target center: {self.spawn_position}. Final top-left: {final_node_pos}"
        )
        self.close()

    def show_panel(self, position: QPointF) -> None:
        """
        Shows the panel at the given global position.
        The input position should be global screen coordinates.
        The panel will be centered horizontally on this position,
        and its vertical position adjusted so the search bar is centered on this position.
        """
        # Ensure the panel has its layout calculated to get correct dimensions
        self.adjustSize()  # Process layout and get initial size

        panel_width = self.width()
        search_bar_height = self.search_bar.height()

        # Calculate top-left position for the panel
        new_x = position.x() - panel_width / 2
        new_y = position.y() - search_bar_height / 2

        self.move(QPointF(new_x, new_y).toPoint())
        self.show()
        self.activateWindow()
        self.search_bar.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        list_widget = self.node_list_widget
        current_row = list_widget.currentRow()
        count = list_widget.count()

        if key == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        elif key == Qt.Key.Key_Down:
            if count > 0:
                next_row = (current_row + 1) % count
                list_widget.setCurrentRow(next_row)
            event.accept()
        elif key == Qt.Key.Key_Up:
            if count > 0:
                prev_row = (current_row - 1 + count) % count
                list_widget.setCurrentRow(prev_row)
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if list_widget.currentItem():
                self._spawn_selected_node()
            event.accept()
        else:
            # Allow search bar to process other key presses
            # self.search_bar.keyPressEvent(event) # This can cause double processing
            super().keyPressEvent(event)
