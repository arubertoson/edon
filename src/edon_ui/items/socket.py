"""Defines visual components related to node sockets in the UI.

This module includes classes for individual socket connection points (`SocketCircleItem`)
and rows that can contain a socket circle, label, and widget (`SocketRowItem`),
along with a protocol (`SocketComponent`) for items within a socket row.
"""

from typing import Protocol, runtime_checkable

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QHoverEvent, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
)

from edon.graph import SocketAddress
from edon.socket import SocketRole
from edon_ui import theme


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


class SocketLinkItem(QGraphicsEllipseItem):
    """Represents the interactive circular connection point of a socket.

    Its (0,0) is its visual and logical center. It is linked to a logical
    socket entity via its name and parent node entity ID.

    Attributes:
        visual_type_key: A string key to determine visual styling from the theme.
    """

    def __init__(
        self,
        parent: QGraphicsItem | None,
        visual_type_key: str = "default",
    ) -> None:
        self._radius = theme.SOCKET_RADIUS
        ellipse_rect = QRectF(-self._radius, -self._radius, 2 * self._radius, 2 * self._radius)
        super().__init__(ellipse_rect, parent)

        self.visual_type_key = visual_type_key
        self._original_fill_color: QColor = theme.SOCKET_FILL_COLORS.get(
            self.visual_type_key, theme.SOCKET_FILL_COLOR_DEFAULT
        )
        self._hover_fill_color: QColor = self._original_fill_color.lighter(150)
        self._drop_target_highlight_color: QColor = QColor(Qt.GlobalColor.green).lighter(
            120
        )  # Placeholder: bright green

        self._is_hovered: bool = False
        self._is_drop_target: bool = False
        self._is_valid_drop_target: bool = False

        pen = QPen(theme.SOCKET_BORDER_COLOR)
        pen.setWidthF(1.0)

        self.setPen(pen)
        self.setBrush(QBrush(self._original_fill_color))
        self.setAcceptHoverEvents(True)

    @property
    def role(self) -> SocketRole:
        return self.parentItem().role

    @property
    def address(self) -> SocketAddress:
        return self.parentItem().socket_address

    @property
    def item(self) -> "SocketItem":
        socket_item = self.parentItem()
        assert isinstance(socket_item, SocketItem)

        return socket_item

    def _update_brush(self) -> None:
        """Updates the socket's fill brush based on its current state (hover, drop target)."""
        if self._is_drop_target:
            self.setBrush(QBrush(self._drop_target_highlight_color))
        elif self._is_hovered:
            self.setBrush(QBrush(self._hover_fill_color))
        else:
            self.setBrush(QBrush(self._original_fill_color))
        self.update()

    def set_not_valid_drop_target(self, disabled: bool) -> None:
        self._is_valid_drop_target = disabled
        self.setOpacity(0.3 if disabled else 1.0)

    def set_drop_target_highlight(self, highlight: bool) -> None:
        if self._is_valid_drop_target:
            return

        if not self._is_drop_target == highlight:
            self._is_drop_target = highlight
            self._update_brush()

    def hoverEnterEvent(self, event: QHoverEvent) -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = True
            self._update_brush()

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QHoverEvent) -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = False
            self._update_brush()

        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            parent_item = self.parentItem()
            logger.debug(f"SocketCircleItem in {parent_item.socket_address} pressed at {event.scenePos()}")
            self.scene().start_edge_drag(parent_item.socket_address, event.scenePos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.scene().is_dragging_edge():
            self.scene().update_dragged_edge(event.scenePos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug(
                f"SocketCircleItem '{self.parentItem().node_entity_id}::{self.parentItem().socket_entity_name}' released at {event.scenePos()}"
            )
            if self.scene().is_dragging_edge():
                self.scene().finish_edge_drag(event.scenePos())
                event.accept()

        super().mouseReleaseEvent(event)


class SocketItem(QGraphicsObject):
    """A composable row for a socket, containing optional label, circle, and widget.

    This item manages the layout of its child components (label, circle, widget)
    based on whether it's an input or output socket and its connection state.
    """

    layoutChanged: Signal = Signal()

    def __init__(
        self,
        role: SocketRole,
        socket_entity_name: str,
        node_entity_id: str,
        label: SocketComponent | None = None,
        socket: SocketLinkItem | None = None,
        widget: SocketComponent | None = None,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.label_item = label
        self.link_item = socket
        self.widget_item = widget

        # XXX: Do we handle these as privates? Or do we work under the contract that
        # "Hey do not change these"
        self.role = role
        self.socket_entity_name = socket_entity_name
        self.node_entity_id = node_entity_id

        for item in (self.label_item, self.link_item, self.widget_item):
            if item is not None and isinstance(item, QGraphicsItem):  # Ensure it's a QGraphicsItem
                item.setParentItem(self)

        # XXX: We should create a custom protocol for the SockeRowitemLable which contains this
        # method.
        if self.label_item and hasattr(self.label_item, "set_text_alignment"):
            # Assuming SocketComponent might have this method if it's a text label.
            # This requires self.label to have a 'set_text_alignment' method.
            # Consider adding 'set_text_alignment' to SocketComponent protocol if it's a common need.
            alignment = Qt.AlignmentFlag.AlignLeft
            if self.role == SocketRole.SOURCE:
                alignment = Qt.AlignmentFlag.AlignRight
            self.label_item.set_text_alignment(alignment)

        self._width: float = 0
        self._height: float = 0

        self._update_bounding_rect()

    @property
    def socket_address(self) -> SocketAddress:
        return SocketAddress(self.node_entity_id, self.socket_entity_name)

    def update_layout(self, available_width: float) -> None:
        self._update_bounding_rect()
        self._do_layout(available_width)
        self.update()

    def boundingRect(self) -> QRectF:
        """Returns the bounding rectangle of the row, containing all laid-out child
        components
        """
        return QRectF(0, 0, self._width, self._height)

    def set_link_state(self, linked: bool) -> None:
        if not self.widget_item or self.role == SocketRole.SOURCE:
            return

        if linked:
            # Socket is in a "read-only" state and receives it's value
            # from a source socket.
            self.widget_item.hide()
        else:
            self.widget_item.show()

        self._update_bounding_rect()
        self.layoutChanged.emit()

    def _update_bounding_rect(self) -> None:
        """Updates the internal bounding rectangle of the row based on its current layout.
        Sets self._width to the maximum width of visible label and widget, and self._height to their combined heights.
        """
        self.prepareGeometryChange()  # Needs to be called when we change boundingRect

        visible_widgets = [w for w in (self.label_item, self.widget_item) if w and w.isVisible()]
        if not visible_widgets:
            self._width = 0
            self._height = 0
            return

        self._width = max(w.boundingRect().width() for w in visible_widgets)
        self._height = sum(w.boundingRect().height() for w in visible_widgets)

    def _do_layout(self, available_width: float) -> None:  # Modified signature
        """Layout the label, circle, and widget according to the mode and available_width.

        The available_width parameter is provided by the parent NodeItem since it has access to all socket rows
        and can determine the maximum width needed across all rows. This ensures consistent alignment
        of socket components (labels, widgets) across all rows in the node, even though each row
        handles its own internal layout independently.
        """
        padding: float = theme.SOCKET_HORIZONTAL_PADDING

        circle_diameter: float = (
            self.link_item.boundingRect().height() if self.link_item and self.link_item.isVisible() else 0
        )
        circle_radius: float = circle_diameter / 2

        # Heights of primary components
        label_h = (
            self.label_item.get_required_component_height() if self.label_item and self.label_item.isVisible() else 0
        )
        widget_h = (
            self.widget_item.get_required_component_height()
            if self.widget_item and self.widget_item.isVisible()
            else 0
        )

        if self.role == SocketRole.TARGET:
            # [circle][padding][label OR widget]
            # If label and widget are both visible (e.g. disconnected input), label is above widget.
            current_y = 0

            # Calculate vertical center for the circle, we want the circle to line up with the
            # label if it exists, otherwise we use the widget.
            if self.link_item and self.link_item.isVisible():
                circle_y_pos = (label_h if label_h else widget_h) / 2
                circle_x_pos = -circle_radius - padding
                self.link_item.setPos(circle_x_pos, circle_y_pos)

            if self.label_item and self.label_item.isVisible():
                self.label_item.setPos(0, current_y)

            if self.widget_item and self.widget_item.isVisible():
                # If label was also visible, widget is below it.
                current_y += label_h
                self.widget_item.setPos(0, current_y)

        else:
            # Output socket: [content (label/widget)] [padding] [circle]
            # Content is left-aligned, circle is right-aligned within available_width.
            current_y = 0

            label_w = (
                self.label_item.get_required_component_width()
                if self.label_item and self.label_item.isVisible()
                else 0
            )
            widget_w = (
                self.widget_item.get_required_component_width()
                if self.widget_item and self.widget_item.isVisible()
                else 0
            )

            # Most of the time, an output will just consist of a label and a circle.
            if self.label_item and self.label_item.isVisible():
                self.label_item.setPos(available_width - label_w, current_y)
                current_y += self.label_item.get_required_component_height()

            if self.widget_item and self.widget_item.isVisible():  # Widget takes precedence
                self.widget_item.setPos(available_width - widget_w, current_y)  # Widget starts at left
                current_y += self.widget_item.get_required_component_height()

            if self.link_item and self.link_item.isVisible():
                # Circle is positioned at the far right of the available_width
                circle_x_pos = available_width + circle_radius + padding
                self.link_item.setPos(
                    circle_x_pos,
                    (
                        self.label_item.get_required_component_height()
                        if self.label_item and self.label_item.isVisible()
                        else widget_h
                    )
                    / 2,
                )
