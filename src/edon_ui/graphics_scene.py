from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QStyleOptionGraphicsItem,
    QWidget,
)

from edon_ui import theme
from edon_ui.item.edge import EdgeItem
from edon_ui.item.node import NodeItem
from edon_ui.item.socket import SocketCircleItem


class EmptySceneTextItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        # Define text and styles for each line
        self.line1_text = "There's nothing here!"
        self.line1_font_family = "Arial"
        self.line1_font_size_px = 18
        self.line1_color = QColor("#b4b4b4")
        self.line1_italic = False

        self.line2_text = "(ctrl+space to start adding nodes)"
        self.line2_font_family = "Arial"
        self.line2_font_size_px = 14
        self.line2_color = QColor("#909090")
        self.line2_italic = True

        self.line_spacing_px = 4  # Additional spacing between lines in pixels

        # Prepare fonts (can also be done in paint, but here is fine too)
        self._font1 = QFont(self.line1_font_family)
        self._font1.setPixelSize(self.line1_font_size_px)  # Use pixelSize for consistency
        self._font1.setItalic(self.line1_italic)

        self._font2 = QFont(self.line2_font_family)
        self._font2.setPixelSize(self.line2_font_size_px)
        self._font2.setItalic(self.line2_italic)

        # Cache bounding rect calculation
        self._cached_bounding_rect = self._calculate_bounding_rect()

    def _get_line_metrics(self, text, font):
        fm = QFontMetricsF(font)
        # boundingRect(text) gives a tight rect around the text.
        # Alternatively, height() gives ascent+descent, width(text) gives advance width.
        return fm.boundingRect(text)  # QRectF

    def _calculate_bounding_rect(self) -> QRectF:
        rect1 = self._get_line_metrics(self.line1_text, self._font1)
        rect2 = self._get_line_metrics(self.line2_text, self._font2)

        max_width = max(rect1.width(), rect2.width())
        total_height = rect1.height() + self.line_spacing_px + rect2.height()

        # We want the item's origin (0,0) to be its visual center for easy scene placement
        return QRectF(-max_width / 2, -total_height / 2, max_width, total_height)

    def boundingRect(self) -> QRectF:
        return self._cached_bounding_rect

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        painter.setRenderHint(QPainter.TextAntialiasing)

        overall_br = self.boundingRect()  # This is already centered around (0,0)

        # --- Draw Line 1 ---
        painter.setFont(self._font1)
        painter.setPen(self.line1_color)

        # Calculate rect for line 1, centered horizontally within overall_br
        # and positioned at the top part of overall_br
        line1_metrics_rect = self._get_line_metrics(self.line1_text, self._font1)

        # Top-left y for line1 text block, relative to item's (0,0) origin
        y1_pos = overall_br.top()

        # Create a drawing rectangle for line1 that spans the full width of the item
        # Qt.AlignCenter will then center the text within this drawing_rect1.
        drawing_rect1 = QRectF(overall_br.left(), y1_pos, overall_br.width(), line1_metrics_rect.height())
        painter.drawText(drawing_rect1, Qt.AlignCenter, self.line1_text)

        # --- Draw Line 2 ---
        painter.setFont(self._font2)
        painter.setPen(self.line2_color)

        line2_metrics_rect = self._get_line_metrics(self.line2_text, self._font2)

        # Top-left y for line2 text block, relative to item's (0,0) origin
        # Positioned after line1 and spacing
        y2_pos = y1_pos + line1_metrics_rect.height() + self.line_spacing_px

        drawing_rect2 = QRectF(overall_br.left(), y2_pos, overall_br.width(), line2_metrics_rect.height())
        painter.drawText(drawing_rect2, Qt.AlignCenter, self.line2_text)


class GraphicsScene(QGraphicsScene):
    """A custom QGraphicsScene subclass designed for a node-based editor interface.

    This scene manages the visual workspace where nodes can be placed and manipulated.
    It provides:
    - A defined active area with visual boundaries
    - Dynamic scene resizing based on node positions
    - Empty state handling with helper text
    - Node tracking and management
    - Visual grid lines for alignment
    - Custom background and styling

    The scene automatically adjusts its boundaries as nodes are added, moved, or
    removed to maintain an appropriate workspace size. It also provides visual
    feedback when empty to guide users on how to begin using the editor.
    """

    scene_changed = Signal()
    edge_drag_updated = Signal(QPointF)
    edge_connection_attempted = Signal(SocketCircleItem, SocketCircleItem)
    edge_disconnection_requested = Signal(EdgeItem)  # New signal for edge disconnection

    def __init__(self, parent=None):
        super().__init__(parent)

        self.active_area_size = 2000  # Initial size, can be smaller if preferred
        self.setSceneRect(
            -self.active_area_size / 2, -self.active_area_size / 2, self.active_area_size, self.active_area_size
        )
        self.setBackgroundBrush(QBrush(theme.SCENE_BACKGROUND))

        # Active area - initialized without specific rect, will be set by _update_scene_appearance
        self.active_area = QGraphicsRectItem()
        self.active_area.setBrush(QBrush(theme.SCENE_ACTIVE_AREA_BACKGROUND))
        self.active_area.setPen(QPen(theme.SCENE_ACTIVE_AREA_BORDER, 1))
        self.active_area.setZValue(-100)  # Ensure it's behind all other items

        self.empty_scene_text = EmptySceneTextItem()
        super().addItem(self.empty_scene_text)
        self.empty_scene_text.setVisible(False)

        self.node_items = []
        self.edge_items = []
        self.temp_edge: EdgeItem | None = None
        self._currently_highlighted_target_socket: SocketCircleItem | None = None

        self._update_scene_appearance()

    def addNode(self, node: NodeItem):
        if node in self.node_items:
            return

        self.node_items.append(node)
        node.positionChanged.connect(self._update_scene_appearance)

        super().addItem(node)
        self._update_scene_appearance()

    def add_new_node_at(self, scene_pos: QPointF):
        # XXX: This is a temporary method to add a new node at a specific scene position.
        # It should be removed once the node is added via the GraphUIManager.
        node_title = f"Node {len(self.node_items) + 1}"
        new_node = NodeItem(title=node_title, x=scene_pos.x(), y=scene_pos.y())
        self.addNode(new_node)

    def removeNode(self, node: NodeItem):
        if node not in self.node_items:
            return

        # Also remove connections associated with this node
        edges_to_remove = [
            edge
            for edge in self.edge_items
            if edge.source_socket_item.parent_node_entity_id == node.node_entity_id
            or (edge.target_socket_item and edge.target_socket_item.parent_node_entity_id == node.node_entity_id)
        ]
        for edge in edges_to_remove:
            self.edge_items.remove(edge)
            super().removeItem(edge)
            del edge

        self.node_items.remove(node)
        super().removeItem(node)
        self._update_scene_appearance()

    def addEdge(self, edge: EdgeItem):
        if edge in self.edge_items:
            return

        self.edge_items.append(edge)
        super().addItem(edge)
        self._update_scene_appearance()

    def removeEdge(self, edge: EdgeItem):
        if edge not in self.edge_items:
            return

        self.edge_items.remove(edge)
        super().removeItem(edge)
        self._update_scene_appearance()

    def _calculate_active_area_rect(self):
        """Calculate the active area rectangle based on the current node positions"""
        if not self.node_items:
            return

        # XXX: As a side note we should only resize the active area so it's bigger
        # if the user has moved the nodes around. If the nodes are within the current
        # active area, we should not resize it. There should be a feature to "recalculate"
        # it so it's optimized around the nodes as well.

        padding = 100
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        for node in self.node_items:
            pos = node.pos()
            rect = node.boundingRect()
            min_x = min(min_x, pos.x())
            min_y = min(min_y, pos.y())
            max_x = max(max_x, pos.x() + rect.width())
            max_y = max(max_y, pos.y() + rect.height())

        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding

        width = max(max_x - min_x, 400)
        height = max(max_y - min_y, 400)
        self.active_area.setRect(min_x, min_y, width, height)

    def _update_scene_appearance(self):
        # To ensure that the active area is only visible when there are nodes in the scene
        # and the empty scene text is only visible when there are no nodes in the scene.
        if not self.node_items:
            if self.active_area.scene() == self:
                super().removeItem(self.active_area)
            self.empty_scene_text.setVisible(True)

            self.scene_changed.emit()
            return

        # If there are nodes in the scene, ensure the active area is visible and displayed
        # correctly.
        self.empty_scene_text.setVisible(False)
        if not self.active_area.scene() == self:
            super().addItem(self.active_area)
        self._calculate_active_area_rect()

        # Update the temporary connection if it's being dragged
        if self.temp_edge:
            # Its _target_pos is the mouse cursor. update_path() will use the
            # current _source_socket_item.scenePos() and this _target_pos.
            self.temp_edge.update_path()
        else:
            for edge_item in self.edge_items:
                edge_item.update_path()

        # Emit the general scene_changed signal whenever this update logic runs.
        self.scene_changed.emit()

    # --- Connection Management Methods ---

    def _get_socket_at_pos(self, scene_pos: QPointF) -> SocketCircleItem | None:
        items_at_pos = self.items(scene_pos)
        for item in items_at_pos:
            if isinstance(item, SocketCircleItem):
                return item
        return None

    def is_dragging_edge(self) -> bool:
        return self.temp_edge is not None

    def _is_valid_connection_target(
        self, source_socket: SocketCircleItem, target_socket: SocketCircleItem | None
    ) -> bool:
        if not source_socket or not target_socket or target_socket == source_socket:
            return False
        # Basic validation: different sockets, different input/output type
        if target_socket.is_input != source_socket.is_input:
            # Prevent self-connection on the same node via parent check of NodeItem
            # SocketCircleItem -> SocketRowItem -> NodeItem
            if target_socket.parentItem().parentItem() != source_socket.parentItem().parentItem():
                return True
            # Allow connection on same node if it's input to output or vice-versa (different SocketRowItem)
            elif target_socket.parentItem() != source_socket.parentItem():
                return True
        return False

    def start_edge_drag(self, clicked_socket_item: SocketCircleItem, drag_start_scene_pos: QPointF):
        """Initiates a new edge drag. If an existing edge starts from the
        clicked_socket_item (and it's an output), that edge is lifted and becomes
        the temporary edge. Otherwise, a new temporary edge is created.
        """
        if self.temp_edge:  # If a drag is already in progress, clean it up first
            self.cleanup_edge_drag()

        # Try to lift an existing edge only if dragging from an OUTPUT socket
        # if not clicked_socket_item.is_input:
        if clicked_socket_item.is_input:
            for edge in list(self.edge_items):  # Iterate over a COPY for safe removal
                if edge.source_socket_item == clicked_socket_item or edge.target_socket_item == clicked_socket_item:
                    self.temp_edge = edge

                    original_target_info = "None"
                    if self.temp_edge.target_socket_item:
                        original_target_info = f"{self.temp_edge.target_socket_item.parent_node_entity_id}::{self.temp_edge.target_socket_item.socket_entity_name}"

                    print(
                        f"Scene: Lifting existing edge from {clicked_socket_item.parent_node_entity_id}::{clicked_socket_item.socket_entity_name} (was connected to {original_target_info})"
                    )

                    # Request disconnection of the edge in the logical graph
                    self.edge_disconnection_requested.emit(self.temp_edge)
                    print("  Requested disconnection of logical connection for this edge.")

                    self.removeEdge(self.temp_edge)  # Removes from self.edge_items and from scene

                    self.temp_edge.clear_target_socket()  # Make its end float
                    # Ensure the lifted edge's source snaps to the socket, and target is the mouse
                    self.temp_edge.set_target_pos(drag_start_scene_pos)
                    self.temp_edge.setZValue(theme.EDGE_Z_VALUE_DRAGGING)  # Ensure it's on top
                    break  # Found and processed the edge to lift
            else:
                # No edge was lifted. Create a new temporary edge.
                # This handles both starting new from an output, or starting new from an input (reverse drag).
                self.temp_edge = EdgeItem(clicked_socket_item, drag_start_scene_pos)
        else:
            # If an output socket was clicked, create a new edge from the socket to the mouse cursor.
            self.temp_edge = EdgeItem(clicked_socket_item, drag_start_scene_pos)

        if self.temp_edge:  # Should be true if lifted_an_edge is true
                super().addItem(self.temp_edge)  # Add back to QGraphicsScene only, not self.edge_items

        # if lifted_an_edge:
        #     # The self.temp_edge was removed from the scene by removeEdge. Re-add it for dragging.
        #     if self.temp_edge:  # Should be true if lifted_an_edge is true
        #         super().addItem(self.temp_edge)  # Add back to QGraphicsScene only, not self.edge_items
        # else:
        #     # No edge was lifted. Create a new temporary edge.
        #     # This handles both starting new from an output, or starting new from an input (reverse drag).
        #     self.temp_edge = EdgeItem(clicked_socket_item, drag_start_scene_pos)
        #     super().addItem(self.temp_edge)  # Add new temp edge to QGraphicsScene only

        #     if clicked_socket_item.is_input:
        #         print(
        #             f"Scene: Started new edge (reverse drag) from INPUT {clicked_socket_item.parent_node_entity_id}::{clicked_socket_item.socket_entity_name}"
        #         )
        #     else:
        #         print(
        #             f"Scene: Started new edge from OUTPUT {clicked_socket_item.parent_node_entity_id}::{clicked_socket_item.socket_entity_name}"
        #         )

        # Common logic after self.temp_edge is set and in scene
        # self.edge_drag_started.emit(clicked_socket_item) # This signal is currently unused

    def update_dragged_edge(self, current_scene_pos: QPointF):
        """Updates the end point of the temporary edge being dragged."""
        if not self.temp_edge:
            return

        self.temp_edge.set_target_pos(current_scene_pos)
        self.edge_drag_updated.emit(current_scene_pos)

        potential_target_socket = self._get_socket_at_pos(current_scene_pos)
        source_socket = self.temp_edge.source_socket_item

        is_valid_target = self._is_valid_connection_target(source_socket, potential_target_socket)

        # If there was a previously highlighted socket and it's not the current one, or current is not valid
        if self._currently_highlighted_target_socket and (
            self._currently_highlighted_target_socket != potential_target_socket or not is_valid_target
        ):
            self._currently_highlighted_target_socket.set_drop_target_highlight(False)
            self._currently_highlighted_target_socket = None

        # If the current potential target is valid and not already highlighted as such (or is a new one)
        if (
            is_valid_target
            and potential_target_socket
            and self._currently_highlighted_target_socket != potential_target_socket
        ):
            potential_target_socket.set_drop_target_highlight(True)
            self._currently_highlighted_target_socket = potential_target_socket

    def finish_edge_drag(self, event_scene_pos: QPointF):
        """Attempts to finalize the edge to a target socket at the given scene position."""
        if not self.temp_edge:
            return

        # This is a bit of a hack to make the logic of the edge connection work in both
        # directions. We do a swap to make the logic of the edge connection consistent.
        target_socket_item = self._get_socket_at_pos(event_scene_pos)
        source_socket_item = self.temp_edge.source_socket_item
        if source_socket_item.is_input:
            source_socket_item, target_socket_item = target_socket_item, source_socket_item

        if self._is_valid_connection_target(source_socket_item, target_socket_item) and target_socket_item:
            print(
                f"Scene: UI Valid Connection. Emitting edge_connection_attempted for GFXUIManager: {source_socket_item.parent_node_entity_id}::{source_socket_item.socket_entity_name} to {target_socket_item.parent_node_entity_id}::{target_socket_item.socket_entity_name}"
            )
            self.edge_connection_attempted.emit(source_socket_item, target_socket_item)

        # We will always call cleanup_edge_drag here, because we are cleaning up the edge,
        # whover is the receiver of the edge_connection_attempted signal will be responsible for
        # creating the edge item and if it succeeds.
        self.cleanup_edge_drag()

    def cleanup_edge_drag(self):
        """Cancels the current edge drag operation."""
        if self._currently_highlighted_target_socket:
            self._currently_highlighted_target_socket.set_drop_target_highlight(False)
            self._currently_highlighted_target_socket = None

        if self.temp_edge:
            source_socket = self.temp_edge.source_socket_item
            print(
                f"Scene: Cancelling edge from '{source_socket.parent_node_entity_id}::{source_socket.socket_entity_name}'"
            )
            super().removeItem(self.temp_edge)
            self.temp_edge = None
