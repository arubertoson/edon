"""Defines visual components related to node sockets in the UI.

This module includes classes for individual socket connection points (`SocketCircleItem`)
and rows that can contain a socket circle, label, and widget (`SocketRowItem`),
along with a protocol (`SocketComponent`) for items within a socket row.
"""

from collections.abc import Set
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt, Signal, QTimer
from PySide6.QtGui import QBrush, QColor, QHoverEvent, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
)

from edon_ui import theme

if TYPE_CHECKING:
    from edon_ui.items.edge import EdgeItem


@runtime_checkable
class SocketComponent(Protocol):
    """
    Protocol defining the interface for a visual component within a SocketRowItem.

    A SocketComponent is expected to be a QGraphicsItem or behave like one for layout purposes.
    It must be able to report its required size and position itself within an allocated rectangle.
    """

    def setParentItem(self, parent: QGraphicsItem | None) -> None: ...
    def setPos(self, pos: QPointF | float, y: float | None = None) -> None: ...
    def pos(self) -> QPointF: ...
    def isVisible(self) -> bool: ...
    def show(self) -> None: ...
    def hide(self) -> None: ...

    def get_required_component_width(self) -> float:
        """Returns the intrinsic width this component requires for layout."""
        ...

    def get_required_component_height(self) -> float:
        """Returns the intrinsic height this component requires for layout."""
        ...


class SocketCircleItem(QGraphicsEllipseItem):
    """Represents the interactive circular connection point of a socket.

    Its (0,0) is its visual and logical center. It is linked to a logical
    socket entity via its name and parent node entity ID.

    Attributes:
        socket_entity_name: The name of the logical socket entity.
        node_entity_id: The ID of the parent node's logical entity.
        visual_type_key: A string key to determine visual styling from the theme.
    """

    def __init__(
        self,
        parent: QGraphicsItem | None,
        socket_entity_name: str,
        node_entity_id: str,
        visual_type_key: str = "default",
    ) -> None:
        self._radius = theme.SOCKET_RADIUS
        ellipse_rect = QRectF(-self._radius, -self._radius, 2 * self._radius, 2 * self._radius)
        super().__init__(ellipse_rect, parent)

        self.socket_entity_name = socket_entity_name
        self.node_entity_id = node_entity_id
        self.visual_type_key = visual_type_key

        self.setAcceptHoverEvents(True)

        self._original_fill_color: QColor = theme.SOCKET_FILL_COLORS.get(
            self.visual_type_key, theme.SOCKET_FILL_COLOR_DEFAULT
        )
        self._hover_fill_color: QColor = self._original_fill_color.lighter(150)
        self._drop_target_highlight_color: QColor = QColor(Qt.GlobalColor.green).lighter(
            120
        )  # Placeholder: bright green

        self._is_hovered: bool = False
        self._is_drop_target: bool = False
        self._is_disabled: bool = False
        self._connected_edges: Set["EdgeItem"] = set()

        pen = QPen(theme.SOCKET_BORDER_COLOR)
        pen.setWidthF(1.0)
        self.setPen(pen)
        self.setBrush(QBrush(self._original_fill_color))

    def add_edge(self, edge_item: "EdgeItem") -> None:
        """Adds an edge to this socket's set of connected edges.

        Notifies the parent item (SocketRowItem) about the connection change.

        Args:
            edge_item: The EdgeItem instance to add.
        """
        self._connected_edges.add(edge_item)
        parent_row = self.parentItem()
        if parent_row and hasattr(parent_row, "set_connected_state"):
            parent_row.set_connected_state(True)

    def remove_edge(self, edge_item: "EdgeItem") -> None:
        """Removes an edge from this socket's set of connected edges.

        Notifies the parent item (SocketRowItem) if no edges remain connected.

        Args:
            edge_item: The EdgeItem instance to remove.
        """
        self._connected_edges.discard(edge_item)
        parent_row = self.parentItem()
        if parent_row and hasattr(parent_row, "set_connected_state"):
            if not self._connected_edges:
                parent_row.set_connected_state(False)

    @property
    def connected_edges(self) -> set["EdgeItem"]:
        return self._connected_edges

    @property
    def is_input(self) -> bool:
        """Determines if this socket is an input socket via its parent SocketRowItem.

        Returns:
            True if the parent SocketRowItem considers this an input socket,
            False otherwise or if no parent.
        """
        parent_row = self.parentItem()
        if parent_row and hasattr(parent_row, "is_input"):
            return parent_row.is_input
        return False  # Default if parent is not a SocketRowItem or unparented

    def _update_brush(self) -> None:
        """Updates the socket's fill brush based on its current state (hover, drop target)."""
        if self._is_drop_target:
            self.setBrush(QBrush(self._drop_target_highlight_color))
        elif self._is_hovered:
            self.setBrush(QBrush(self._hover_fill_color))
        else:
            self.setBrush(QBrush(self._original_fill_color))
        self.update()

    def set_drop_target_highlight(self, highlight: bool) -> None:
        """Sets or unsets the visual highlight indicating this socket is a valid drop target.

        Args:
            highlight: True to highlight as a drop target, False otherwise.
        """
        if self._is_disabled:
            return

        if self._is_drop_target != highlight:
            self._is_drop_target = highlight
            self._update_brush()

    def set_disabled_visual(self, disabled: bool) -> None:
        """
        Visually indicates that this socket is not a valid drop target (e.g., by reducing opacity).

        Args:
            disabled: True to set the disabled visual state, False to clear it.
        """
        self._is_disabled = disabled
        self.setOpacity(0.3 if disabled else 1.0)

    def hoverEnterEvent(self, event: QHoverEvent) -> None:
        """Handles mouse hover enter events to update visual state.

        Args:
            event: The QHoverEvent.
        """
        if not self._is_disabled:
            self._is_hovered = True
            self._update_brush()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QHoverEvent) -> None:
        """Handles mouse hover leave events to update visual state.

        Args:
            event: The QHoverEvent.
        """
        if not self._is_disabled:
            self._is_hovered = False
            self._update_brush()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles left mouse button press to initiate an edge drag.

        Args:
            event: The QGraphicsSceneMouseEvent.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug(
                f"SocketCircleItem '{self.node_entity_id}::{self.socket_entity_name}' pressed at {event.scenePos()}"
            )

            self.scene().start_edge_drag(self, event.scenePos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles mouse move events to update a dragged edge.

        Args:
            event: The QGraphicsSceneMouseEvent.
        """
        if self.scene().is_dragging_edge():
            self.scene().update_dragged_edge(event.scenePos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles left mouse button release to finalize an edge drag.

        Args:
            event: The QGraphicsSceneMouseEvent.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug(
                f"SocketCircleItem '{self.node_entity_id}::{self.socket_entity_name}' released at {event.scenePos()}"
            )
            if self.scene().is_dragging_edge():
                self.scene().finish_edge_drag(event.scenePos())
                event.accept()

        super().mouseReleaseEvent(event)


class SocketRowItem(QGraphicsObject):
    """A composable row for a socket, containing optional label, circle, and widget.

    This item manages the layout of its child components (label, circle, widget)
    based on whether it's an input or output socket and its connection state.

    Args:
        label: The type label (optional), conforming to SocketComponent.
        circle: The connection circle (optional), conforming to SocketComponent.
        widget: The input/output widget (optional), conforming to SocketComponent.
        socket_entity_name: The unique name of the socket entity.
        parent_entity_node_id: The unique ID of the parent node entity.
        is_input: True if this is an input socket, False for output.
        parent: The parent QGraphicsItem.

    Attributes:
        label: The visual component for the socket's label.
        circle: The visual component for the socket's connection circle.
        widget: The visual component for the socket's interactive widget.
        is_input: Boolean indicating if this is an input socket.
        socket_entity_name: Logical name of the socket.
        parent_entity_node_id: Logical ID of the parent node.
    """

    layoutChanged: Signal = Signal()

    def __init__(
        self,
        label: SocketComponent,
        circle: SocketCircleItem,
        widget: SocketComponent | None = None,
        socket_entity_name: str | None = None,
        parent_entity_node_id: str | None = None,
        is_input: bool = True,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.label: SocketComponent = label
        self.circle: SocketCircleItem | None = circle
        self.widget: SocketComponent | None = widget
        self.is_input: bool = is_input
        self.socket_entity_name: str | None = socket_entity_name
        self.parent_entity_node_id: str | None = parent_entity_node_id

        for item in (self.label, self.circle, self.widget):
            if item is not None and isinstance(item, QGraphicsItem):  # Ensure it's a QGraphicsItem
                item.setParentItem(self)

        if self.label and hasattr(self.label, "set_text_alignment"):
            # Assuming SocketComponent might have this method if it's a text label.
            # This requires self.label to have a 'set_text_alignment' method.
            # Consider adding 'set_text_alignment' to SocketComponent protocol if it's a common need.
            alignment = Qt.AlignmentFlag.AlignLeft if self.is_input else Qt.AlignmentFlag.AlignRight
            try:
                self.label.set_text_alignment(alignment)
            except AttributeError:
                logger.warning(
                    f"SocketRowItem's label of type {type(self.label).__name__} "
                    "does not have set_text_alignment method."
                )

        self._width: float = 0
        self._height: float = 0

        self.prepareGeometryChange()
        self._update_bounding_rect()

    def _update_bounding_rect(self) -> None:
        """Updates the internal bounding rectangle of the row based on its current layout.
        Sets self._width to the maximum width of visible label and widget, and self._height to their combined heights.
        """
        visible_widgets = [w for w in (self.label, self.widget) if w and w.isVisible()]
        if not visible_widgets:
            self._width = 0
            self._height = 0
            return
        # Largest width among visible label and widget
        self._width = max(w.boundingRect().width() for w in visible_widgets)
        # Combined height (stacked vertically)
        self._height = sum(w.boundingRect().height() for w in visible_widgets)

    def update_layout(self, available_width: float) -> None:
        self.prepareGeometryChange()
        self._update_bounding_rect()
        self._do_layout(available_width)
        self.update()

    def _do_layout(self, available_width: float) -> None:  # Modified signature
        """Layout the label, circle, and widget according to the mode and available_width.

        The available_width parameter is provided by the parent NodeItem since it has access to all socket rows
        and can determine the maximum width needed across all rows. This ensures consistent alignment
        of socket components (labels, widgets) across all rows in the node, even though each row
        handles its own internal layout independently.
        """
        padding: float = theme.SOCKET_HORIZONTAL_PADDING

        circle_diameter: float = self.circle.boundingRect().height() if self.circle and self.circle.isVisible() else 0
        circle_radius: float = circle_diameter / 2

        # Heights of primary components
        label_h = self.label.get_required_component_height() if self.label and self.label.isVisible() else 0
        widget_h = self.widget.get_required_component_height() if self.widget and self.widget.isVisible() else 0

        if self.is_input:
            # [circle][padding][label OR widget]
            # If label and widget are both visible (e.g. disconnected input), label is above widget.
            current_y = 0

            # Calculate vertical center for the circle, we want the circle to line up with the
            # label if it exists, otherwise we use the widget.
            if self.circle and self.circle.isVisible():
                circle_y_pos = (label_h if label_h else widget_h) / 2
                circle_x_pos = -circle_radius - padding
                self.circle.setPos(circle_x_pos, circle_y_pos)

            if self.label and self.label.isVisible():
                self.label.setPos(0, current_y)

            if self.widget and self.widget.isVisible():
                # If label was also visible, widget is below it.
                current_y += label_h
                self.widget.setPos(0, current_y)

        else:
            # Output socket: [content (label/widget)] [padding] [circle]
            # Content is left-aligned, circle is right-aligned within available_width.
            current_y = 0

            label_w = self.label.get_required_component_width() if self.label and self.label.isVisible() else 0
            widget_w = self.widget.get_required_component_width() if self.widget and self.widget.isVisible() else 0

            # Most of the time, an output will just consist of a label and a circle.
            if self.label and self.label.isVisible():
                self.label.setPos(available_width - label_w, current_y)
                current_y += self.label.get_required_component_height()

            if self.widget and self.widget.isVisible():  # Widget takes precedence
                self.widget.setPos(available_width - widget_w, current_y)  # Widget starts at left
                current_y += self.widget.get_required_component_height()

            if self.circle and self.circle.isVisible():
                # Circle is positioned at the far right of the available_width
                circle_x_pos = available_width + circle_radius + padding
                self.circle.setPos(
                    circle_x_pos,
                    (self.label.get_required_component_height() if self.label and self.label.isVisible() else widget_h)
                    / 2,
                )

    def boundingRect(self) -> QRectF:
        """Returns the bounding rectangle of the row.

        Returns:
            The bounding rectangle covering all laid-out child components.
        """
        return QRectF(0, 0, self._width, self._height)

    def _read_only(self) -> None:
        """Swaps to a label-only view, typically when an input socket is connected.

        Hides the widget if it exists and is part of this item.
        Emits layoutChanged via _do_layout.
        """
        if not self.is_input:
            return

        if self.widget:
            self.widget.hide()

    def _swap_to_editable(self) -> None:
        """Swaps to an editable view, typically when an input socket is disconnected.

        Shows the widget if it exists and is part of this item.
        May hide the label depending on desired behavior (currently shows both if both exist).
        Emits layoutChanged via _do_layout.
        """
        if not self.is_input:
            return

        if self.widget:
            self.widget.show()

    def set_connected_state(self, connected: bool) -> None:
        """Swaps between editable widget and label view based on connection state.

        This is primarily for input sockets. Emits layoutChanged via _do_layout.

        Args:
            connected: True if the socket is connected, False otherwise.
        """
        if not self.is_input:
            return  # Only input sockets typically change appearance on connection

        if connected:
            self._read_only()
        else:
            self._swap_to_editable()

        self._update_bounding_rect()
        self.layoutChanged.emit()
