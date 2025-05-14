from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QStyleOptionGraphicsItem,
    QWidget,
)
from loguru import logger

from edon_ui import theme
from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketCircleItem

if TYPE_CHECKING:
    from PySide6.QtCore import QObject
    from edon_ui.graph_controller import GraphController


class EmptySceneTextItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

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

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

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
        painter.drawText(drawing_rect1, Qt.AlignmentFlag.AlignCenter, self.line1_text)

        # --- Draw Line 2 ---
        painter.setFont(self._font2)
        painter.setPen(self.line2_color)

        line2_metrics_rect = self._get_line_metrics(self.line2_text, self._font2)

        # Top-left y for line2 text block, relative to item's (0,0) origin
        # Positioned after line1 and spacing
        y2_pos = y1_pos + line1_metrics_rect.height() + self.line_spacing_px

        drawing_rect2 = QRectF(overall_br.left(), y2_pos, overall_br.width(), line2_metrics_rect.height())
        painter.drawText(drawing_rect2, Qt.AlignmentFlag.AlignCenter, self.line2_text)


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

    def __init__(self, controller: "GraphController | None" = None, parent: "QObject | None" = None):
        super().__init__(parent)
        self.controller = controller

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

        self.node_items: list[NodeItem] = []
        self.edge_items: list[EdgeItem] = []
        self.temp_edge: EdgeItem | None = None
        self._currently_highlighted_target_socket: SocketCircleItem | None = None

        self._update_scene_appearance()

    def addNode(self, node: NodeItem):
        if node in self.node_items:
            return

        self.node_items.append(node)
        node.positionChanged.connect(self._update_scene_appearance)
        node.sizeChanged.connect(self._handle_node_resize, Qt.ConnectionType.QueuedConnection)

        super().addItem(node)
        self._update_scene_appearance()

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
            self.removeEdge(edge)

        self.node_items.remove(node)
        super().removeItem(node)
        self._update_scene_appearance()

    def addEdge(self, edge: EdgeItem):
        if edge in self.edge_items:
            return

        self.edge_items.append(edge)
        edge.source_socket_item.add_edge(edge)
        edge.target_socket_item.add_edge(edge)

        super().addItem(edge)
        self._update_scene_appearance()

    def removeEdge(self, edge: EdgeItem):
        if edge not in self.edge_items:
            return

        self.edge_items.remove(edge)
        edge.source_socket_item.remove_edge(edge)
        edge.target_socket_item.remove_edge(edge)

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

    def _update_common_scene_elements(self):
        """Updates common visual elements of the scene like active area and empty text."""
        if not self.node_items:
            if self.active_area.scene() == self:
                super().removeItem(self.active_area)
            self.empty_scene_text.setVisible(True)
            return

        self.empty_scene_text.setVisible(False)
        if not self.active_area.scene() == self:
            super().addItem(self.active_area)

        self._calculate_active_area_rect()

    def _handle_node_resize(self, resized_node_id: str):
        """Handles updates when a specific node (identified by resized_node_id) resizes."""
        logger.debug(f"Scene: Handling resize for node {resized_node_id}")
        self._update_common_scene_elements()

        # Update edges connected to the specific resized node
        for edge_item in self.edge_items:
            is_source_node = edge_item.source_socket_item.parent_node_entity_id == resized_node_id
            is_target_node = (
                edge_item.target_socket_item and edge_item.target_socket_item.parent_node_entity_id == resized_node_id
            )
            if is_source_node or is_target_node:
                logger.debug(f"Updating edge connected to resized node: {edge_item}")
                edge_item.update_path()

        self.scene_changed.emit()

    def _update_scene_appearance(self):
        # This method is now primarily for general updates (node moves, add/remove item)
        logger.trace("Scene: General appearance update.")
        self._update_common_scene_elements()

        # Optimization: if dragging a temp_edge, only update it for performance during drag.
        # Otherwise, update all committed edges.
        if self.temp_edge:
            self.temp_edge.update_path()
        else:
            for edge_item in self.edge_items:
                edge_item.update_path()

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

    def start_edge_drag(self, clicked_socket_item: SocketCircleItem, drag_start_scene_pos: QPointF):
        """Initiates a new edge drag. If an existing edge starts from the
        clicked_socket_item (and it's an output), that edge is lifted and becomes
        the temporary edge. Otherwise, a new temporary edge is created.
        """
        connected_edges: set[EdgeItem] = clicked_socket_item.connected_edges
        if clicked_socket_item.is_input and connected_edges:
            # If this is an input we can assumem that it should only have one connection
            # our internal logic will prevent more than one connection to an input.
            self.temp_edge = next(iter(connected_edges))

            logger.debug(
                f"Scene: Lifting existing edge from {clicked_socket_item.parent_node_entity_id}::{clicked_socket_item.socket_entity_name}"
            )

            self.controller.handle_ui_edge_deletion_request([self.temp_edge])
            # self.graph_manager.handle_ui_edge_disconnection_request(self.temp_edge)
            logger.debug("Requested disconnection of logical connection for this edge.")

            # self.removeEdge(self.temp_edge)  # Removes from self.edge_items and from scene

            self.temp_edge.clear_target_socket()  # Make its end float
            # Ensure the lifted edge's source snaps to the socket, and target is the mouse
            self.temp_edge.set_target_pos(drag_start_scene_pos)
            self.temp_edge.setZValue(theme.EDGE_Z_VALUE_DRAGGING)  # Ensure it's on top
        else:
            # If an output socket was clicked, create a new edge from the socket to the mouse cursor.
            self.temp_edge = EdgeItem(clicked_socket_item, drag_start_scene_pos)

        super().addItem(self.temp_edge)
        self.update_socket_drop_targets(self.temp_edge.source_socket_item)

    def update_dragged_edge(self, current_scene_pos: QPointF):
        """Updates the end point of the temporary edge being dragged."""

        self.temp_edge.set_target_pos(current_scene_pos)

        potential_target_socket = self._get_socket_at_pos(current_scene_pos)
        if not potential_target_socket:
            if self._currently_highlighted_target_socket:
                self._currently_highlighted_target_socket.set_drop_target_highlight(False)
                self._currently_highlighted_target_socket = None
            return

        # XXX: This is potentially heavy, and we should look into caching when performance takes a hit.
        source_socket = self.temp_edge.source_socket_item
        valid_targets = self.controller.request_edge_drop_targets(source_socket)

        is_valid = (
            potential_target_socket.parent_node_entity_id,
            potential_target_socket.socket_entity_name,
        ) in valid_targets
        if is_valid:
            potential_target_socket.set_drop_target_highlight(True)
            self._currently_highlighted_target_socket = potential_target_socket

    def finish_edge_drag(self, event_scene_pos: QPointF):
        """
        Attempts to finalize the edge connection at the given scene position.

        This method handles both standard connections (output → input) and reverse connections
        (input → output) by swapping source and target sockets when needed to maintain consistent
        connection logic. It delegates the actual connection attempt to the graph_manager and
        always cleans up the temporary edge regardless of connection success.

        Args:
            event_scene_pos: The scene position where the edge drag ended
        """
        # This is a bit of a hack to make the logic of the edge connection work in both
        # directions. We do a swap to make the logic of the edge connection consistent.
        target_socket_item = self._get_socket_at_pos(event_scene_pos)
        source_socket_item = self.temp_edge.source_socket_item
        if source_socket_item.is_input:
            source_socket_item, target_socket_item = target_socket_item, source_socket_item

        if source_socket_item and target_socket_item:
            self.controller.handle_ui_edge_connection_attempt(source_socket_item, target_socket_item)

        # We will always call cleanup_edge_drag here, because we are cleaning up the edge,
        # graph manager will handle making the edge persistent.
        self.cleanup_edge_drag()

    def cleanup_edge_drag(self):
        """Cancels the current edge drag operation."""
        if self._currently_highlighted_target_socket:
            self._currently_highlighted_target_socket.set_drop_target_highlight(False)
            self._currently_highlighted_target_socket = None

        if self.temp_edge:
            source_socket = self.temp_edge.source_socket_item
            logger.debug(
                f"Scene: Cancelling edge from '{source_socket.parent_node_entity_id}::{source_socket.socket_entity_name}'"
            )
            super().removeItem(self.temp_edge)
            self.temp_edge = None

        self.reset_socket_drop_targets()

    def update_socket_drop_targets(self, source_socket):
        """
        Grays out all sockets that cannot be connected to from the given source_socket,
        including those that would create a cycle. Uses GraphController for validation.
        """
        if self.controller is None:
            logger.warning("Warning: GraphicsScene has no graph_manager set!")
            return

        valid_targets = self.controller.request_edge_drop_targets(source_socket)
        for item in self.items():
            if not isinstance(item, SocketCircleItem):
                continue

            socket_circle = item

            node_id = socket_circle.parent_node_entity_id
            socket_name = socket_circle.socket_entity_name

            # Only consider input sockets as drop targets
            if socket_circle == source_socket:
                socket_circle.set_disabled_visual(False)
                continue

            if (node_id, socket_name) in valid_targets:
                socket_circle.set_disabled_visual(False)
            else:
                socket_circle.set_disabled_visual(True)

    def reset_socket_drop_targets(self):
        for item in self.items():
            if isinstance(item, SocketCircleItem):
                item.set_disabled_visual(False)
