"""
Provides the custom QGraphicsScene implementation for the node editor.

This module defines the GraphicsScene class, which manages the visual workspace
for the node graph. It handles adding and removing visual items (nodes, edges),
drawing the background and grid, managing the active area, and processing
low-level UI events related to item interaction and dragging.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
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

    from edon_ui.views.viewer import GraphicsView


@dataclass
class EdgeDragContext:
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
    highlighted_socket: SocketItem | None = None

    def apply_target_socket_highlight(self, item: SocketItem | None) -> None:
        # Here we check whether we had a highlight, or if we are already highlighting
        # the target item. If not, we need to reset.
        if self.highlighted_socket and not self.highlighted_socket == item:
            self.highlighted_socket.set_drop_target_highlight(False)
            self.highlighted_socket = None

        # We check whether the target item is in the `DragContext` valid targets and highlight
        # the object if it is.
        if item and item.address in self.valid_targets:
            item.set_drop_target_highlight(True)
            self.highlighted_socket = item

    def apply_target_socket_visuals(self) -> None:
        """Applies visual feedback by marking invalid drop target sockets."""
        if not self.invalid_targets:
            return

        for socket_item in self.invalid_targets.values():
            if socket_item and socket_item.link_item:
                socket_item.link_item.set_not_valid_drop_target(True)

    def cleanup_visuals(self) -> None:
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

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
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
        drawing_rect1 = QRectF(
            overall_br.left(), y1_pos, overall_br.width(), line1_metrics_rect.height()
        )
        painter.drawText(drawing_rect1, Qt.AlignmentFlag.AlignCenter, self.line1_text)

        # --- Draw Line 2 ---
        painter.setFont(self._font2)
        painter.setPen(self.line2_color)

        line2_metrics_rect = self._get_line_metrics(self.line2_text, self._font2)

        # Top-left y for line2 text block, relative to item's (0,0) origin
        # Positioned after line1 and spacing
        y2_pos = y1_pos + line1_metrics_rect.height() + self.line_spacing_px

        drawing_rect2 = QRectF(
            overall_br.left(), y2_pos, overall_br.width(), line2_metrics_rect.height()
        )
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

    # Node Signals
    node_redraw_ui_request = Signal(str, object)

    # Edge Signals
    edge_drag_initiation_request = Signal(SocketAddress, QPointF, object)
    edge_link_request = Signal(SocketAddress, SocketAddress, object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self._drag_context: DragContext | None = None

        self.active_area_size = 2000  # Initial size, can be smaller if preferred
        self.setSceneRect(
            -self.active_area_size / 2,
            -self.active_area_size / 2,
            self.active_area_size,
            self.active_area_size,
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

        self.selectionChanged.connect(self._handle_selection_changed)

    @property
    def _view(self) -> GraphicsView:
        views = self.views()
        assert len(views) == 1, (
            "CORRUPTION: There should be exactly one view for each scene, instead got {len(views)}"
        )

        return cast(GraphicsView, views[0])

    def clear(self) -> None:
        super().clear()
        self.empty_scene_text = EmptySceneTextItem()
        self.empty_scene_text.setVisible(False)
        super().addItem(self.empty_scene_text)

    def add_node(self, node: NodeItem):
        # A node needs to be able to redraw itself when e.g. a socket is updated, or a widget
        # is hidden.
        # XXX: This might actually remove the need for hte _update_edges_for_node, as that
        # should be chained called either way.
        # what do we need to do:
        #   - When we add/remove sockets we need to removed edges if it has connection.
        #   - we then need to create/delete any widgets that has been changed on the item
        #   - then we need to update the position of any edges that are still connected.
        # node.node_redraw_signal.connect(self._update_redraw_node_item)
        super().addItem(node)

        node._on_socket_row_layout_changed()
        self._update_active_area_rect()

    def remove_node(self, node: NodeItem):
        super().removeItem(node)

    def add_edge(self, edge: EdgeItem):
        """Adds a visual EdgeItem to the scene.

        The logical linking and state updates on SocketItems are handled by the GraphController.
        """
        socket_item: SocketItem = edge.target_socket_item
        socket_item.transition_to(True)

        super().addItem(edge)

    def remove_edge(self, edge: EdgeItem):
        """Removes a visual EdgeItem from the scene.

        The logical unlinking and state updates on SocketItems are handled by the GraphController.
        """
        socket_item: SocketItem = edge.target_socket_item
        socket_item.transition_to(False)

        super().removeItem(edge)

    def is_dragging_edge(self) -> bool:
        return self._drag_context is not None

    def edge_drag_create_action(self, drag_context: EdgeDragContext, pos: QPointF):
        """
        Initiates an edge drag operation from the specified socket.

        Delegates the edge lifting and validation logic to the controller,
        then sets up the visual drag state based on the returned information.
        """
        temp_edge = DraggingEdgeItem(drag_context.source_socket_item, pos)
        super().addItem(temp_edge)

        # Create the drag context and update the visuals on potential target sockets.
        self._drag_context = DragContext(
            temp_edge,
            drag_context.source_socket_item,
            drag_context.valid_targets,
            drag_context.invalid_targets,
        )
        self._drag_context.apply_target_socket_visuals()

        logger.debug(
            f"Started {'lifted' if drag_context.is_lifted_edge else 'new'} edge drag from {drag_context.source_socket_addr}"
        )

    def edge_drag_action(self, current_scene_pos: QPointF):
        """Updates the temporary edge position and manages socket highlighting during drag."""
        if not self._drag_context:
            return

        # Update temp edge position
        self._drag_context.temp_edge.update_target_position(current_scene_pos)

        # Handle socket highlighting
        target_socket_item = self._get_socket_at_pos(current_scene_pos)
        self._drag_context.apply_target_socket_highlight(target_socket_item)

    def edge_drop_action(self, event_scene_pos: QPointF):
        """
        Completes the edge drag operation by attempting to create a connection.

        Handles role swapping for reverse connections and ensures all visual
        state is properly cleaned up regardless of connection success.
        """
        if not self._drag_context:
            return

        target_socket_item = self._get_socket_at_pos(event_scene_pos)
        if target_socket_item and target_socket_item.address in self._drag_context.valid_targets:
            source_addr = self._drag_context.source_socket_item.address
            target_addr = target_socket_item.address

            # Handle role swapping for reverse connections
            if self._drag_context.source_socket_item.role == SocketRole.TARGET:
                source_addr, target_addr = target_addr, source_addr

            self.edge_link_request.emit(source_addr, target_addr, self)

        # Cleanup everything
        super().removeItem(self._drag_context.temp_edge)
        self._drag_context.cleanup_visuals()
        self._drag_context = None

    def _handle_selection_changed(self):
        # XXX: We should keep an eye on this function as it could potentially be recursed and cause a crash/lock.
        # If that happens we need to look into temporarily disconnecting the signal and reconnecting it.
        current_selected_items = self.selectedItems()
        nodes_are_present_in_selection = any(
            isinstance(item, NodeItem) for item in current_selected_items
        )

        if nodes_are_present_in_selection:
            # If any node is selected, iterate through a copy of the selected items and deselect any EdgeItem.
            # We iterate a copy because setSelected(False) will modify the list returned by selectedItems() live.
            # This might not be necessary if we are careful with the logic of the edge item selection.
            for item in list(current_selected_items):
                if isinstance(item, EdgeItem):
                    item.setSelected(False)

    def _calculate_node_bounds(self, nodes: Iterable[NodeItem], padding: float) -> QRectF:
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

    def _update_active_area_rect(self):
        """
        Updates the active area rectangle based on node positions.

        If nodes are selected by the user, it expands the current active area to
        include these selected nodes. If no nodes are selected, it recalculates
        the active area based on all nodes (e.g., for initial setup or after
        a full recalculation request).
        """
        node_items = [item for item in self.items() if isinstance(item, NodeItem)]
        assert node_items, (
            "CORRUPTION: Update active area should only happen if we have nodes in the scene."
        )

        padding = 0
        current_active_rect = self.active_area.rect()

        selected_nodes = [item for item in self.selectedItems() if isinstance(item, NodeItem)]
        nodes_to_consider = selected_nodes if selected_nodes else node_items

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

    def set_active(self, active: bool) -> None:
        """
        Updates the scene display based on whether nodes are present.
        """
        if active:
            self.empty_scene_text.setVisible(False)
            if not self.active_area.scene() == self:
                super().addItem(self.active_area)

            self._update_active_area_rect()
        else:
            if self.active_area.scene() == self:
                super().removeItem(self.active_area)
            self.empty_scene_text.setVisible(True)

    def _get_socket_at_pos(self, scene_pos: QPointF) -> SocketItem | None:
        items_at_pos = self.items(scene_pos)
        for item in items_at_pos:
            if isinstance(item, SocketLinkItem):
                return item._socket_item
        return None
