"""Defines visual components related to node sockets in the UI.

This module includes classes for individual socket connection points (`SocketCircleItem`)
and rows that can contain a socket circle, label, and widget (`SocketRowItem`),
along with a protocol (`SocketComponent`) for items within a socket row.
"""

from collections.abc import Set  # Import Set from collections.abc
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QHoverEvent, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
)

from edon_ui import theme

# from .socket_widgets import SocketWidgetAdaptor # SocketWidgetAdaptor is unused

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
        parent_node_entity_id: The ID of the parent node's logical entity.
        visual_type_key: A string key to determine visual styling from the theme.
    """

    def __init__(
        self,
        parent: QGraphicsItem | None,
        socket_entity_name: str,
        parent_node_entity_id: str,
        visual_type_key: str = "default",
    ) -> None:
        self._radius = theme.SOCKET_RADIUS
        ellipse_rect = QRectF(-self._radius, -self._radius, 2 * self._radius, 2 * self._radius)
        super().__init__(ellipse_rect, parent)

        self.socket_entity_name = socket_entity_name
        self.parent_node_entity_id = parent_node_entity_id
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
        self.update()

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
                f"SocketCircleItem '{self.parent_node_entity_id}::{self.socket_entity_name}' "
                f"pressed at {event.scenePos()}"
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
                f"SocketCircleItem '{self.parent_node_entity_id}::{self.socket_entity_name}' "
                f"released at {event.scenePos()}"
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
        self._do_layout()

    def _do_layout(self) -> None:
        """Layout the label, circle, and widget according to the mode. Emits layoutChanged."""
        padding: float = theme.SOCKET_HORIZONTAL_PADDING
        x: float = 0
        y: float = 0

        circle_diameter: float = self.circle.boundingRect().height() if self.circle else 0
        circle_radius: float = circle_diameter / 2
        row_height: float = theme.SOCKET_ROW_HEIGHT

        # Layout for input:     [circle][padding][label]
        #                               [padding][widget]
        # Layout for connected: [padding][label]
        if self.is_input:
            if self.label:
                self.label.setPos(0, 0)
                y = self.label.get_required_component_height()
            if self.circle:
                self.circle.setPos(-circle_radius - padding, row_height / 2)
            if self.widget:
                self.widget.setPos(0, y)
        # Layout for output: [label/widget][padding][circle]
        else:
            if self.label:
                self.label.setPos(0, 0)
                x += self.label.get_required_component_width() + padding
            if self.circle:
                y = self.label.get_required_component_height() / 2
                x += circle_diameter
                self.circle.setPos(x, y)
            if self.widget:
                self.widget.setPos(0, 0)

        # Circle should not be part of this calculation.
        children = [item for item in (self.label, self.widget) if item is not None and item.isVisible()]

        min_x = min(child.pos().x() for child in children)
        min_y = min(child.pos().y() for child in children)
        max_x = max(child.pos().x() + child.get_required_component_width() for child in children)
        max_y = max(child.pos().y() + child.get_required_component_height() for child in children)

        new_width = max_x - min_x
        new_height = max_y - min_y

        if self._width != new_width or self._height != new_height:
            self.prepareGeometryChange()
            self._width = new_width
            self._height = new_height
            self.update()

        self.layoutChanged.emit()

    def boundingRect(self) -> QRectF:
        """Returns the bounding rectangle of the row.

        Returns:
            The bounding rectangle covering all laid-out child components.
        """
        return QRectF(0, 0, self._width, self._height)

    # XXX: Change name / Read Only
    def _swap_to_label(self) -> None:
        """Swaps to a label-only view, typically when an input socket is connected.

        Hides the widget if it exists and is part of this item.
        Emits layoutChanged via _do_layout.
        """
        if not self.is_input:
            return

        if self.widget:
            self.widget.hide()

        if self.label:
            self.label.show()

        self._do_layout()

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

        if self.label:
            self.label.show()

        self._do_layout()

    def set_connected_state(self, connected: bool) -> None:
        """Swaps between editable widget and label view based on connection state.

        This is primarily for input sockets. Emits layoutChanged via _do_layout.

        Args:
            connected: True if the socket is connected, False otherwise.
        """
        if not self.is_input:
            return  # Only input sockets typically change appearance on connection

        logger.debug(f"SocketRow '{self.socket_entity_name}' connected state: {connected}")

        if connected:
            self._swap_to_label()
        else:
            self._swap_to_editable()
