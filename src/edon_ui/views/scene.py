from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt, Signal, Slot
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QStyleOptionGraphicsItem,
    QWidget,
)

from edon.graph import SocketAddress
from edon_ui import theme
from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketLinkItem

if TYPE_CHECKING:
    from PySide6.QtCore import QObject

    from edon_ui.graph import GraphController


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
        - Empty state handling with helper text
        - A defined active area with visual boundaries
        - Dynamic scene resizing based on node positions
        - Node and Edge Tracking
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
        self._currently_highlighted_target_socket: SocketLinkItem | None = None
        self._cached_drag_valid_targets: set[SocketAddress] | None = None  # Cache for valid drop targets during drag

        self.selectionChanged.connect(self._handle_selection_changed)

        self._refresh_scene_edge_paths()

    def _handle_selection_changed(self):
        # XXX: We should keep an eye on this function as it could potentially be recursed and cause a crash/lock.
        # If that happens we need to look into temporarily disconnecting the signal and reconnecting it.
        current_selected_items = self.selectedItems()
        nodes_are_present_in_selection = any(isinstance(item, NodeItem) for item in current_selected_items)

        if nodes_are_present_in_selection:
            # If any node is selected, iterate through a copy of the selected items and deselect any EdgeItem.
            # We iterate a copy because setSelected(False) will modify the list returned by selectedItems() live.
            # This might not be necessary if we are careful with the logic of the edge item selection.
            for item in list(current_selected_items):
                if isinstance(item, EdgeItem):
                    item.setSelected(False)

    def add_node(self, node: NodeItem):
        if node in self.node_items:
            return

        self.node_items.append(node)
        node.node_position_update_signal.connect(self._refresh_scene_edge_paths)
        node.node_redraw_signal.connect(self._refresh_scene_node_size, Qt.ConnectionType.QueuedConnection)

        super().addItem(node)
        self._refresh_scene_edge_paths()

    def remove_node(self, node: NodeItem):
        if node not in self.node_items:
            return

        # Also remove connections associated with this node
        edges_to_remove = [
            edge
            for edge in self.edge_items
            if edge.source_socket_item.node_entity_id == node.node_entity_id
            or (edge.target_socket_item and edge.target_socket_item.node_entity_id == node.node_entity_id)
        ]
        for edge in edges_to_remove:
            self.remove_edge(edge)

        self.node_items.remove(node)
        super().removeItem(node)
        self._refresh_scene_edge_paths()

    def add_edge(self, edge: EdgeItem):
        if edge in self.edge_items:
            return

        self.edge_items.append(edge)
        edge.source_socket_item.add_edge(edge)
        edge.target_socket_item.add_edge(edge)



        super().addItem(edge)
        self._refresh_scene_edge_paths()

    def remove_edge(self, edge: EdgeItem):
        if edge not in self.edge_items:
            return

        self.edge_items.remove(edge)
        edge.source_socket_item.remove_edge(edge)
        edge.target_socket_item.remove_edge(edge)

        super().removeItem(edge)
        self._refresh_scene_edge_paths()

    @Slot()
    def _refresh_scene_active_area_rect(self):
        """Calculate the active area rectangle based on the current node positions"""
        # XXX: this slot needs to ensure that our scene is having a size that can contain
        # all our elements and the main window of the application. It's an interactive scene
        # where we move things around, so ensuring that we have a "container" is just nice
        # style.
        #
        # So we need to think about when we need to about when we require this:
        # - Node move events
        # - Edge Drag events (not updating the rect but limiting movement at least)
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

    @Slot()
    def _refresh_scene_interaction_state(self):
        """
        If we don't have any elements in the scene we also don't need an active area,
        a simple non interactive viewport that explains your first step is all we need.
        """
        # XXX: This is just relevant for add/remove node. We need either signlas
        # or direct calls to this. Signals for things such as node move, direct calls
        # for add/remove node.
        if not self.node_items:
            if self.active_area.scene() == self:
                super().removeItem(self.active_area)

            self.empty_scene_text.setVisible(True)
            return
        else:
            if self.empty_scene_text.isVisible():
                self.empty_scene_text.setVisible(False)

            if not self.active_area.scene() == self:
                super().addItem(self.active_area)

                # Updating the active area after we've added a node is necessary.
                self._refresh_scene_active_area_rect()

    @Slot(str)
    def _refresh_scene_node_size(self, updated_node_id: str):
        """
        This is necessary when we pick up drop an edge on a socket, this will trigger a
        node resize as the widgets within it might be put to read only. At that point we
        want to redraw any edges that have links to this node as otherwise they will
        hang in the "air".
        """
        logger.trace(f"Scene: handle redrawing of esdges for {updated_node_id}")

        # XXX: I don't really like this api,we should look into it
        node = self.controller.node_map[updated_node_id]
        for socket_circle in node.so

        for edge_item in self.edge_items:
            is_source_node = edge_item.source_socket_item.node_entity_id == updated_node_id
            is_target_node = (
                edge_item.target_socket_item and edge_item.target_socket_item.node_entity_id == updated_node_id
            )
            if is_source_node or is_target_node:
                logger.debug(f"Updating Edge: {edge_item.node_entity_id}")
                edge_item.update_path()

        # XXX: this is not necessary here, interactive viewport is only necessary if we don't have any nodes
        # in the scene. Add/Remove node
        # self.scene_changed.emit()

    @Slot(str)
    def _refresh_scene_edge_paths(self, updated_node_id: str):
        logger.trace(f"Scene: refresh scene edge paths for {updated_node_id}")

        # XXX: We need to have a better management of the cached items in the scene
        # we don't have a good way of reaching the different relating elements.
        # We either need a good way to get to the items, or direct references
        # to our scene items from our targets, so we can write something like this:
        # node_item = self.node_items[updated_node_id]
        # ---
        # for socket in node_item.source_socket_item + node_item.target_socket_item:
        #     for edge_item in socket.links:
        #         edge_item.update_path()
        # ---
        # Right now we have a brute force solution that will work, but this needs work :)
        if self.temp_edge:
            self.temp_edge.update_path()
        else:
            for edge_item in self.edge_items:
                edge_item.update_path()

        # XXX: This is only relevant if we need to update the interaction, this signal needs a better name
        # needs a better name! Do we need to update anything else after path redraws?
        # self.scene_changed.emit()

    # --- Connection Management Methods ---

    def _get_socket_at_pos(self, scene_pos: QPointF) -> SocketLinkItem | None:
        items_at_pos = self.items(scene_pos)
        for item in items_at_pos:
            if isinstance(item, SocketLinkItem):
                return item
        return None

    # XXX: Should the below really be managed by the scene?

    def is_dragging_edge(self) -> bool:
        return self.temp_edge is not None

    def start_edge_drag(self, clicked_socket_address: SocketAddress, drag_start_scene_pos: QPointF):
        """Initiates a new edge drag. If an existing edge starts from the
        clicked_socket_item (and it's an output), that edge is lifted and becomes
        the temporary edge. Otherwise, a new temporary edge is created.
        """
        socket_row = self.controller.socket_addr_row_map.get(clicked_socket_address)
        if not socket_row or not hasattr(socket_row, "circle") or socket_row.circle is None:
            logger.error(f"Could not find UI socket circle for address {clicked_socket_address} to start edge drag.")
            return
        clicked_socket_item = socket_row.circle

        connected_edges: set[EdgeItem] = clicked_socket_item.connected_edges
        if clicked_socket_item.is_input and connected_edges:
            # If this is an input we can assume that it should only have one connection
            # our internal logic will prevent more than one connection to an input.
            self.temp_edge = next(iter(connected_edges))

            logger.debug(
                f"Scene: Lifting existing edge from {clicked_socket_item.node_entity_id}::{clicked_socket_item.socket_entity_name}"
            )

            # When an edge is lifted, its logical connection needs to be severed in the model.
            # The GraphController handles this, which in turn updates the EntityGraph.
            # The visual EdgeItem is kept (as self.temp_edge) and removed from the scene's
            # persistent edge_items list.
            # Note: handle_ui_edge_deletion_request expects a sequence of EdgeItem.
            self.controller.handle_ui_edge_deletion_request([self.temp_edge])
            logger.debug("Requested deletion of logical connection for this edge.")

            # Make the end of the edge float and ensure the lifted edge's source snaps to the
            # socket, and target is the mouse.
            self.temp_edge.clear_target_socket()
            self.temp_edge.set_target_pos(drag_start_scene_pos)
            self.temp_edge.setZValue(theme.EDGE_Z_VALUE_DRAGGING)
        else:
            # If an output socket was clicked, or an input socket with no existing connections,
            # create a new temporary edge from the socket to the mouse cursor.
            self.temp_edge = EdgeItem(clicked_socket_item, drag_start_scene_pos)

        super().addItem(self.temp_edge)  # New temp_edge always needs to be added.

        # The cache is calculated when we start the drag, and we don't need to recalculate it
        # during the drag.
        self._cached_drag_valid_targets = self.controller.request_edge_drop_targets(self.temp_edge.source_socket_item)
        logger.debug(f"Cached valid drop targets: {self._cached_drag_valid_targets}")
        self.update_socket_drop_targets(self.temp_edge.source_socket_item)

    def update_dragged_edge(self, current_scene_pos: QPointF):
        """Updates the end point of the temporary edge being dragged."""
        assert self.temp_edge is not None

        self.temp_edge.set_target_pos(current_scene_pos)
        potential_target_socket = self._get_socket_at_pos(current_scene_pos)

        hl_socket = self._currently_highlighted_target_socket

        # Reset previously highlighted socket if it's no longer the potential target or no target exists
        if hl_socket and hl_socket != potential_target_socket:
            hl_socket.set_drop_target_highlight(False)
            self._currently_highlighted_target_socket = None

        if not potential_target_socket:
            return

        is_valid = (
            SocketAddress(
                potential_target_socket.node_entity_id,
                potential_target_socket.socket_entity_name,
            )
            in self._cached_drag_valid_targets
        )

        if is_valid:
            if hl_socket != potential_target_socket:
                # If there was a different highlighted socket, turn its highlight off
                if hl_socket:
                    hl_socket.set_drop_target_highlight(False)

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
            # Retrieve SocketAddress instances for the controller method
            source_addr = source_socket_item.parentItem().socket_address
            target_addr = target_socket_item.parentItem().socket_address
            if source_addr and target_addr:
                self.controller.handle_ui_edge_link_request(source_addr, target_addr)
            else:
                logger.error("Could not retrieve socket addresses to finalize edge drag.")

        # Reset the currently highlighted target socket.
        if self._currently_highlighted_target_socket:
            self._currently_highlighted_target_socket.set_drop_target_highlight(False)
            self._currently_highlighted_target_socket = None

        # Remove the temporary edge.
        if self.temp_edge:
            source_socket = self.temp_edge.source_socket_item
            logger.debug(
                f"Scene: Removing temporary edge from '{source_socket.node_entity_id}::{source_socket.socket_entity_name}'"
            )
            # The edge is not part of the entity graph at this point so we avoid calling
            # the controller.
            super().removeItem(self.temp_edge)
            self.temp_edge = None

        # Reset the cached valid targets and their visual state.
        self._cached_drag_valid_targets = set()
        for item in self.items():
            if isinstance(item, SocketLinkItem):
                item.set_not_valid_drop_target(False)

    def update_socket_drop_targets(self, source_socket: SocketLinkItem):
        """
        Grays out all sockets that cannot be connected to from the given source_socket,
        including those that would create a cycle. Uses GraphController for validation.
        Uses cached targets if available during an active drag.
        """
        assert self.controller is not None and self._cached_drag_valid_targets is not None
        logger.debug("Using cached valid drop targets for global socket update.")

        for item in self.items():
            if not isinstance(item, SocketLinkItem):
                continue

            socket_circle = item
            if socket_circle == source_socket:
                socket_circle.set_not_valid_drop_target(False)
                continue

            current_socket_addr = SocketAddress(socket_circle.node_entity_id, socket_circle.socket_entity_name)
            if current_socket_addr in self._cached_drag_valid_targets:
                socket_circle.set_not_valid_drop_target(False)
            else:
                socket_circle.set_not_valid_drop_target(True)
