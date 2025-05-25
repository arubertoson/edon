"""Defines the main graphical canvas for the node editor and related UI components.

This module provides the `GraphicsScene` class, which serves as the interactive
workspace for displaying and manipulating nodes and edges. It also includes
helper classes for managing edge dragging operations (`DragPrepInfo`, `DragContext`)
and for displaying instructional text when the scene is empty (`EmptySceneTextItem`).
"""

from collections.abc import Mapping
from dataclasses import dataclass
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
from edon_ui.items.socket import SocketItem, SocketLinkItem

if TYPE_CHECKING:
    from PySide6.QtCore import QObject

    from edon_ui.graph import GraphController


@dataclass
class DragPrepInfo:
    """
    Encapsulates the data needed to initiate an edge drag operation.

    Contains the resolved source socket information after handling edge lifting
    logic, along with precomputed valid and invalid drop targets for efficient
    visual feedback during the drag operation.
    """

    source_socket_addr: SocketAddress
    source_socket_item: SocketItem
    is_lifted_edge: bool
    valid_targets: Mapping[SocketAddress, SocketItem]
    invalid_targets: Mapping[SocketAddress, SocketItem]


@dataclass
class DragContext:
    """
    Manages the state of an active edge drag operation within the graphics scene.

    Consolidates drag-related state that was previously scattered across multiple
    instance variables, providing a single point of truth for the current drag
    operation's visual and logical state.
    """

    temp_edge: DraggingEdgeItem
    source_socket_item: SocketItem
    valid_targets: Mapping[SocketAddress, SocketItem]
    invalid_targets: Mapping[SocketAddress, SocketItem]
    highlighted_socket: SocketLinkItem | None = None

    def reset_highlight(self) -> None:
        self.highlighted_socket.set_drop_target_highlight(False)
        self.highlighted_socket = None

    def set_highlight_item(self, item: SocketItem) -> None:
        item.set_drop_target_highlight(True)
        self.highlighted_socket = item

    def apply_target_socket_visuals(self) -> None:
        """Applies visual feedback by marking invalid drop target sockets."""
        if not self.invalid_targets:
            return

        for socket_item in self.invalid_targets.values():
            if socket_item and socket_item.link_item:
                socket_item.link_item.set_not_valid_drop_target(True)

    def cleanup_visuals(self, scene: "GraphicsScene") -> None:
        """Resets all visual feedback states applied during the drag operation."""
        if self.highlighted_socket:
            self.highlighted_socket.set_drop_target_highlight(False)

        for socket_item in self.invalid_targets.values():
            if socket_item and socket_item.link_item:
                socket_item.link_item.set_not_valid_drop_target(False)


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

        self._drag_context: DragContext | None = None

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
        # edge.target_socket_item is now a SocketItem directly
        socket_item: SocketItem = edge.target_socket_item
        socket_item.set_link_state(True)

        super().addItem(edge)

    def remove_edge(self, edge: EdgeItem):
        # We let the SocketItem know that it's linked to trigger read-only/editable
        # socket widgets
        # edge.target_socket_item is now a SocketItem directly
        socket_item: SocketItem = edge.target_socket_item
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
        return self._drag_context is not None

    def initiate_dragging_edge(self, clicked_socket_address: SocketAddress, drag_start_scene_pos: QPointF):
        """
        Initiates an edge drag operation from the specified socket.

        Delegates the edge lifting and validation logic to the controller,
        then sets up the visual drag state based on the returned information.
        """
        drag_info = self.controller.prepare_drag_operation(clicked_socket_address)
        if not drag_info:
            logger.error(f"Could not prepare drag operation for {clicked_socket_address}")
            return

        temp_edge = DraggingEdgeItem(drag_info.source_socket_item, drag_start_scene_pos)
        super().addItem(temp_edge)

        # Create the drag context and update the visuals on potential target sockets.
        self._drag_context = DragContext(
            temp_edge, drag_info.source_socket_item, drag_info.valid_targets, drag_info.invalid_targets
        )
        self._drag_context.apply_target_socket_visuals()

        logger.debug(
            f"Started {'lifted' if drag_info.is_lifted_edge else 'new'} edge drag from {drag_info.source_socket_addr}"
        )

    def update_dragging_edge(self, current_scene_pos: QPointF):
        """Updates the temporary edge position and manages socket highlighting during drag."""
        if not self._drag_context:
            return

        # Update temp edge position
        self._drag_context.temp_edge.update_target_position(current_scene_pos)

        # Handle socket highlighting
        target_socket_item = self._get_socket_at_pos(current_scene_pos)
        old_highlighted = self._drag_context.highlighted_socket

        # Here we check whether we had a highlight, or if we are already highlighting
        # the target item. If not, we need to reset.
        if old_highlighted and old_highlighted != target_socket_item:
            self._drag_context.reset_highlight()

        # We check whether the target item is in the `DragContext` valid targets and highlight
        # the object if it is.
        if target_socket_item:
            if target_socket_item.socket_address in self._drag_context.valid_targets:
                self._drag_context.set_highlight_item(target_socket_item)

    def finalize_dragging_edge(self, event_scene_pos: QPointF):
        """
        Completes the edge drag operation by attempting to create a connection.

        Handles role swapping for reverse connections and ensures all visual
        state is properly cleaned up regardless of connection success.
        """
        if not self._drag_context:
            return

        target_socket_item = self._get_socket_at_pos(event_scene_pos)
        if target_socket_item and target_socket_item.socket_address in self._drag_context.valid_targets:
            source_addr = self._drag_context.source_socket_item.socket_address
            target_addr = target_socket_item.socket_address

            # Handle role swapping for reverse connections
            if self._drag_context.source_socket_item.role == SocketRole.TARGET:
                source_addr, target_addr = target_addr, source_addr

            self.controller.handle_ui_edge_link_request(source_addr, target_addr)

        # Cleanup everything
        super().removeItem(self._drag_context.temp_edge)
        self._drag_context.cleanup_visuals(self)
        self._drag_context = None

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

    def _calculate_node_bounds(self, nodes: list[NodeItem], padding: float) -> QRectF:
        """Calculate the bounding rectangle for a list of nodes with padding."""
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        for node in nodes:
            pos = node.pos()
            rect = node.boundingRect()
            min_x = min(min_x, pos.x())
            min_y = min(min_y, pos.y())
            max_x = max(max_x, pos.x() + rect.width())
            max_y = max(max_y, pos.y() + rect.height())

        return QRectF(
            min_x - padding,
            min_y - padding,
            (max_x + padding) - (min_x - padding),
            (max_y + padding) - (min_y - padding),
        )

    def _expand_bounds_only(self, current_rect: QRectF, new_bounds: QRectF) -> QRectF:
        """Expand current bounds to include new bounds, but never shrink."""
        final_left = min(current_rect.left(), new_bounds.left())
        final_top = min(current_rect.top(), new_bounds.top())
        final_right = max(current_rect.right(), new_bounds.right())
        final_bottom = max(current_rect.bottom(), new_bounds.bottom())

        return QRectF(final_left, final_top, final_right - final_left, final_bottom - final_top)

    @Slot()
    def _update_active_area_rect(self):
        """
        Updates the active area rectangle based on node positions.

        If nodes are selected by the user, it expands the current active area to
        include these selected nodes. If no nodes are selected, it recalculates
        the active area based on all nodes (e.g., for initial setup or after
        a full recalculation request).
        """
        if not self.node_items:
            # This case should ideally be handled by _update_scene_content_display
            # which would hide the active_area. If called directly, just return.
            return

        padding = 100.0
        current_active_rect = self.active_area.rect()

        selected_nodes = [item for item in self.selectedItems() if isinstance(item, NodeItem)]
        nodes_to_consider = selected_nodes if selected_nodes else self.node_items

        if not nodes_to_consider:
            return

        bounds = self._calculate_node_bounds(nodes_to_consider, padding)

        if selected_nodes:
            final_bounds = self._expand_bounds_only(current_active_rect, bounds)
        else:
            # No selection: use bounds calculated from all nodes (initial or full recalc)
            final_bounds = bounds

        width = max(final_bounds.width(), 400.0)
        height = max(final_bounds.height(), 400.0)

        self.active_area.setRect(final_bounds.x(), final_bounds.y(), width, height)
        logger.trace(f"Active area updated to: {self.active_area.rect()}")

    def recalculate_active_area(self) -> None:
        """
        Recalculates the active area to optimally fit all nodes.

        This method can be called to shrink the active area when nodes
        have been moved closer together or deleted.
        """
        if not self.node_items:
            return

        # Force recalculation by temporarily clearing selection
        # or just calculate from all nodes directly
        bounds = self._calculate_node_bounds(self.node_items, 100)

        width = max(bounds.width(), 400)
        height = max(bounds.height(), 400)

        self.active_area.setRect(bounds.x(), bounds.y(), width, height)

        logger.debug("Active area recalculated to optimal size")

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

    def _get_socket_at_pos(self, scene_pos: QPointF) -> SocketItem | None:
        items_at_pos = self.items(scene_pos)
        for item in items_at_pos:
            if isinstance(item, SocketLinkItem):
                return item.parent
        return None
