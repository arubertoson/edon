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
from edon.socket import SocketRole
from edon_ui import theme
from edon_ui.items.edge import DraggingEdgeItem, EdgeItem
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketLinkItem, SocketItem

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

    scene_node_count_changed = Signal(int)

    def __init__(self, controller: "GraphController", parent: "QObject | None" = None):
        super().__init__(parent)
        self.controller: "GraphController" = controller

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
        self.empty_scene_text.setVisible(False)
        super().addItem(self.empty_scene_text)

        self._temp_edge: DraggingEdgeItem | None = None
        self._currently_highlighted_target_socket: SocketLinkItem | None = None
        self._cached_drag_valid_targets: set[SocketAddress] = set()  # Cache for valid drop targets during drag

        self.selectionChanged.connect(self._handle_selection_changed)

    @property
    def node_items(self) -> list[NodeItem]:
        return list(self.controller.node_map.values())

    def add_node(self, node: NodeItem):
        node.node_position_update_signal.connect(self._update_edges_for_node)
        node.node_position_update_signal.connect(self._update_active_area_rect)
        node.node_redraw_signal.connect(self._update_edges_for_node)

        super().addItem(node)
        # XXX: Keep an eye on, I don't think we need to update paths here, it's a new node, should have no connections.
        # self._refresh_scene_edge_paths()

        self._update_scene_content_display()
        self.scene_node_count_changed.emit(len(self.node_items))
        self._update_active_area_rect()

    def remove_node(self, node: NodeItem):
        try:
            node.node_position_update_signal.disconnect(self._update_edges_for_node)
            node.node_position_update_signal.disconnect(self._update_active_area_rect)
        except RuntimeError:  # Signal was not connected or already disconnected
            pass
        try:
            node.node_redraw_signal.disconnect(self._update_edges_for_node)
        except RuntimeError:  # Signal was not connected or already disconnected
            pass

        super().removeItem(node)
        self._update_scene_content_display()
        self.scene_node_count_changed.emit(len(self.node_items))

    def add_edge(self, edge: EdgeItem):
        # We let the SocketItem know that it's linked to trigger read-only/editable
        # socket widgets
        socket_item: SocketItem = edge.target_socket_item.item
        socket_item.set_link_state(True)

        super().addItem(edge)

    def remove_edge(self, edge: EdgeItem):
        # We let the SocketItem know that it's linked to trigger read-only/editable
        # socket widgets
        socket_item: SocketItem = edge.target_socket_item.item
        socket_item.set_link_state(False)

        super().removeItem(edge)

    def clear_graph_elements(self) -> None:
        logger.debug("GraphicsScene: Clearing all graph elements (nodes and edges).")

        # Temporarily disable updates on all views attached to this scene
        # to prevent visual artifacts during bulk item removal.
        associated_views = self.views()
        for view in associated_views:
            view.setUpdatesEnabled(False)

        try:
            items_to_remove = [item for item in self.items() if isinstance(item, (NodeItem, EdgeItem))]

            for item in items_to_remove:
                # For NodeItem, ensure signals it might have connected to the scene are disconnected
                # or that its removal from scene handles this.
                if isinstance(item, NodeItem):
                    try:
                        # Assuming NodeItem might connect these, attempt disconnection
                        item.node_position_update_signal.disconnect(self._update_edges_for_node)
                    except (RuntimeError, TypeError):  # TypeError if signal was never connected
                        pass
                    try:
                        item.node_redraw_signal.disconnect(self._update_edges_for_node)
                    except (RuntimeError, TypeError):
                        pass

                super().removeItem(item)

            self._update_scene_content_display()
        finally:
            # Re-enable updates on all views
            for view in associated_views:
                view.setUpdatesEnabled(True)
            logger.trace("GraphicsScene: View updates re-enabled after clearing graph elements.")

    def is_dragging_edge(self) -> bool:
        return self._temp_edge is not None

    def initiate_dragging_edge(self, clicked_socket_address: SocketAddress, drag_start_scene_pos: QPointF):
        """Initiates a new edge drag.

        If an existing edge is connected to a clicked input socket, that edge is "lifted"
        by creating a new temporary drag from its original source.
        Otherwise, a new temporary edge is created from the clicked socket.
        """
        socket_item = self.controller.socket_addr_socket_item_map.get(clicked_socket_address)

        if not socket_item or not socket_item.link_item:
            logger.error(
                f"Could not find UI socket item or link_item for address {clicked_socket_address} to start edge drag."
            )
            return

        linked_edge_items = self.controller.find_edge_items_at_socket(clicked_socket_address)

        if socket_item.role == SocketRole.TARGET and linked_edge_items:
            # Lifting an existing edge from an input socket.
            # An input socket should only have one edge due to controller logic.
            lifted_edge_item = next(iter(linked_edge_items))
            source_link_item_of_lifted_edge = lifted_edge_item.source_socket_item

            logger.debug(
                f"Scene: Lifting existing edge from input {clicked_socket_address}. "
                f"Original source: {source_link_item_of_lifted_edge.address}"
            )

            # Remove the old EdgeItem logically and from UI
            self.controller.handle_ui_edge_deletion_request([lifted_edge_item])

            # Create a new DraggingEdgeItem starting from the *other* end of the lifted edge
            self._temp_edge = DraggingEdgeItem(source_link_item_of_lifted_edge, drag_start_scene_pos)
        else:
            # Standard drag from an output, or an input socket with no existing connections.
            logger.debug(f"Scene: Starting new drag from socket: {clicked_socket_address}")
            self._temp_edge = DraggingEdgeItem(socket_item.link_item, drag_start_scene_pos)

        super().addItem(self._temp_edge)  # Add the new/repurposed temp_edge to the scene.
        self._temp_edge.setZValue(theme.EDGE_Z_VALUE_DRAGGING)  # Ensure it's on top

        # Cache valid drop targets based on the actual source of the drag
        # This requires SocketLinkItem to have a 'socket_address' property.
        actual_drag_source_address = self._temp_edge.source_socket_item.address
        valid, invalid = self.controller.partition_socket_drop_targets(actual_drag_source_address)
        self._cached_drag_valid_targets = valid
        logger.debug(f"Cached valid drop targets for {actual_drag_source_address}: {self._cached_drag_valid_targets}")

        self.update_socket_drop_targets(self._temp_edge.source_socket_item)

    def update_dragging_edge(self, current_scene_pos: QPointF):
        """Updates the end point of the temporary edge being dragged."""

        # This should not happen, start_edge_drag should setup the correct scene state for edge drag.
        assert self._temp_edge

        self._temp_edge.update_target_position(current_scene_pos)
        potential_target_socket = self._get_socket_at_pos(current_scene_pos)

        hl_socket = self._currently_highlighted_target_socket

        # Reset previously highlighted socket if it's no longer the potential target or no target exists
        if hl_socket and hl_socket != potential_target_socket:
            hl_socket.set_drop_target_highlight(False)
            self._currently_highlighted_target_socket = None

        if not potential_target_socket:
            return

        is_valid = potential_target_socket.address in self._cached_drag_valid_targets

        if is_valid:
            if hl_socket != potential_target_socket:
                # If there was a different highlighted socket, turn its highlight off
                if hl_socket:
                    hl_socket.set_drop_target_highlight(False)

                potential_target_socket.set_drop_target_highlight(True)
                self._currently_highlighted_target_socket = potential_target_socket

    def finalize_dragging_edge(self, event_scene_pos: QPointF):
        """
                Attempts to finalize the edge connection at the given scene position.

        This method handles both standard connections (output → input) and reverse connections
                (input → output) by swapping source and target sockets when needed to maintain consistent
                connection logic. It delegates the actual connection attempt to the graph_manager and
                always cleans up the temporary edge regardless of connection success.

                Args:
                    event_scene_pos: The scene position where the edge drag ended
        """
        # NOTE: we have the assert for self._temp_edge in update_dragged_edge and can
        # avoid any cleanup. If we readch this point without a temporary edge something
        # has gone terribly wrong and any resulting crash should happen.

        target_socket_item = self._get_socket_at_pos(event_scene_pos)
        source_socket_item = self._temp_edge.source_socket_item
        if source_socket_item.role == SocketRole.TARGET:
            source_socket_item, target_socket_item = target_socket_item, source_socket_item

        if source_socket_item and target_socket_item:
            # Retrieve SocketAddress instances for the controller method
            source_addr = source_socket_item.parentItem().socket_address
            target_addr = target_socket_item.parentItem().socket_address
            if source_addr and target_addr:
                self.controller.handle_ui_edge_link_request(source_addr, target_addr)
            else:
                logger.error("Could not retrieve socket addresses to finalize edge drag.")
        else:
            logger.error("Could not retrieve socket items to finalize edge drag.")

        # Reset the currently highlighted target socket.
        if self._currently_highlighted_target_socket:
            self._currently_highlighted_target_socket.set_drop_target_highlight(False)
            self._currently_highlighted_target_socket = None

        # Remove the temporary edge.
        source_socket_addr_for_log = self._temp_edge.source_socket_item.address
        logger.debug(
            f"Scene: Removing temporary edge from '{source_socket_addr_for_log.node_id}::{source_socket_addr_for_log.socket_name}'"
        )
        super().removeItem(self._temp_edge)

        self._temp_edge = None

        # Reset the cached valid targets and their visual state.
        if self._cached_drag_valid_targets is not None:  # Check if it was ever populated
            for item in self.items():
                if isinstance(item, SocketLinkItem):
                    # Reset the 'not_valid_drop_target' state for all SocketLinkItems
                    item.set_not_valid_drop_target(False)
        self._cached_drag_valid_targets = set()

    def update_socket_drop_targets(self, source_socket: SocketLinkItem):
        """
        Grays out all sockets that cannot be connected to from the given source_socket,
        including those that would create a cycle. Uses GraphController for validation.
        Uses cached targets if available during an active drag.
        """
        if self._cached_drag_valid_targets is None:
            logger.warning(
                "GraphicsScene: update_socket_drop_targets called but _cached_drag_valid_targets is None. "
                "This might happen if not in an active drag sequence initiated by start_edge_drag."
            )
            # Reset all to default state as we don't have valid targets.
            for item in self.items():
                if isinstance(item, SocketLinkItem):
                    item.set_not_valid_drop_target(False)
            return

        logger.debug("Using cached valid drop targets for global socket update.")

        for item in self.items():
            if not isinstance(item, SocketLinkItem):  # Simplified check
                continue

            socket_link = item  # item is already a SocketLinkItem
            if socket_link == source_socket:
                socket_link.set_not_valid_drop_target(False)
            else:
                # Ensure parentItem() and socket_address exist before checking membership
                parent_item = socket_link.parentItem()
                if hasattr(parent_item, "socket_address"):
                    is_valid_target = parent_item.socket_address in self._cached_drag_valid_targets
                    # set_not_valid_drop_target(True) means it's disabled / grayed out
                    # So if it's NOT a valid target, we disable it.
                    socket_link.set_not_valid_drop_target(not is_valid_target)
                else:
                    # If no socket_address, assume it's not a valid target for safety
                    socket_link.set_not_valid_drop_target(True)

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

    @Slot()
    def _update_active_area_rect(self):
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
    def _update_scene_content_display(self):
        """
        If we don't have any elements in the scene we also don't need an active area,
        a simple non interactive viewport that explains your first step is all we need.
        """
        # XXX: This is just relevant for add/remove node. We need either signlas
        # or direct calls to this. Signals for things such as node move, direct calls
        # for add/remove node.
        if not self.node_items:
            logger.warning("interaction scene? 2222")
            if self.active_area.scene() == self:
                super().removeItem(self.active_area)

            self.empty_scene_text.setVisible(True)
            return
        else:
            logger.warning("interaction scene? 2223")
            if self.empty_scene_text.isVisible():
                self.empty_scene_text.setVisible(False)

            if not self.active_area.scene() == self:
                super().addItem(self.active_area)

                # Updating the active area after we've added a node is necessary.
                self._update_active_area_rect()

    @Slot(str)
    def _update_edges_for_node(self, updated_node_id: str):
        """
        Updates the visual paths of all edges connected to the specified node.

        This method is called when a node's position changes or when its internal
        layout/size changes (e.g., due to socket widget modifications that might
        affect socket positions). It ensures that edges remain correctly connected
        visually.
        """
        logger.trace(f"Scene: Updating edges for node {updated_node_id}")

        node = self.controller.node_map.get(updated_node_id)
        for socket_item in node.source_sockets + node.target_sockets:
            edges = self.controller.find_edge_items_at_socket(socket_item.socket_address)
            for edge in edges:
                edge.update_path()

    def _get_socket_at_pos(self, scene_pos: QPointF) -> SocketLinkItem | None:
        items_at_pos = self.items(scene_pos)
        for item in items_at_pos:
            if isinstance(item, SocketLinkItem):
                return item
        return None
