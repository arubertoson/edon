"""Defines visual components related to node sockets in the UI.

This module includes classes for individual socket connection points (`SocketCircleItem`)
and rows that can contain a socket circle, label, and widget (`SocketRowItem`),
along with a protocol (`SocketComponent`) for items within a socket row.
"""

from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
)

from edon.graph import SocketAddress
from edon.socket import SocketRole
from edon_ui import theme

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsSceneHoverEvent

    from edon_ui.views.scene import GraphicsScene


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
    def boundingRect(self) -> QRectF: ...
    def isVisible(self) -> bool: ...
    def show(self) -> None: ...
    def hide(self) -> None: ...

    def get_required_component_width(self) -> float:
        """Returns the intrinsic width this component requires for layout."""
        ...

    def get_required_component_height(self) -> float:
        """Returns the intrinsic height this component requires for layout."""
        ...


@runtime_checkable
class SocketTextComponent(SocketComponent, Protocol):
    """
    Protocol defining the interface for a visual text component within a SocketItem.
    """

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        """Sets the alignment for the text component"""
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
    def parent(self) -> "SocketItem":
        socket_item: SocketItem = cast(SocketItem, self.parentItem())
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

    def hoverEnterEvent(self, event: "QGraphicsSceneHoverEvent") -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = True
            self._update_brush()

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: "QGraphicsSceneHoverEvent") -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = False
            self._update_brush()

        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent.handle_link_press(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        # Check if a drag is active before attempting to call the parent's handler.
        # The parent's handler might assume a drag is in progress.
        scene = cast("GraphicsScene", self.scene())
        if scene.is_dragging_edge():
            self.parent.handle_link_move(event)
            event.accept()
        else:
            # It's important to call the base class implementation if we're not handling the event,
            # especially for events like mouseMove that might be used by QGraphicsItem for other purposes.
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Similar to mouseMoveEvent, only delegate if a drag was active.
            scene = cast("GraphicsScene", self.scene())
            if scene.is_dragging_edge():
                self.parent.handle_link_release(event)
                event.accept()
            else:
                # If no drag was active, perhaps the press was consumed elsewhere or it was a simple click
                # without initiating a drag. Call super to ensure normal event processing.
                super().mouseReleaseEvent(event)
        else:
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
        entity_name: str,
        node_entity_id: str,
        label: SocketTextComponent | None = None,
        socket: SocketLinkItem | None = None,
        widget: SocketComponent | None = None,
        parent: QGraphicsObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.label_item = label
        self.link_item = socket
        self.widget_item = widget

        self.role = role
        self.entity_name = entity_name
        self.node_entity_id = node_entity_id

        for item in (self.label_item, self.link_item, self.widget_item):
            if item is not None and isinstance(item, QGraphicsItem):  # Ensure it's a QGraphicsItem
                item.setParentItem(self)

        if self.label_item:
            alignment = Qt.AlignmentFlag.AlignLeft
            if self.role == SocketRole.SOURCE:
                alignment = Qt.AlignmentFlag.AlignRight
            self.label_item.set_text_alignment(alignment)

        self._width: float = 0
        self._height: float = 0
        self._address: SocketAddress | None = None

        self._update_bounding_rect()

    @property
    def _scene(self) -> "GraphicsScene":
        return cast("GraphicsScene", self.scene())

    def handle_link_press(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles mouse press events forwarded from the SocketLinkItem."""
        logger.debug(f"SocketItem link in {self.socket_address} pressed at {event.scenePos()}")

        self._scene.initiate_dragging_edge(self.socket_address, event.scenePos())

    def handle_link_move(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles mouse move events forwarded from the SocketLinkItem during a drag."""
        # The scene's update_dragging_edge method typically doesn't need the socket_address,
        # just the current mouse position.
        self._scene.update_dragging_edge(event.scenePos())

    def handle_link_release(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handles mouse release events forwarded from the SocketLinkItem."""
        logger.debug(f"SocketItem link '{self.node_entity_id}::{self.entity_name}' released at {event.scenePos()}")

        self._scene.finalize_dragging_edge(event.scenePos())

    @property
    def socket_address(self) -> SocketAddress:
        if not self._address:
            self._address = SocketAddress(self.node_entity_id, self.entity_name)
        return self._address

    def update_layout(self, available_width: float) -> None:
        self._update_bounding_rect()
        self._do_layout(available_width)
        self.update()

    def boundingRect(self) -> QRectF:
        """Returns the bounding rectangle of the row, containing all laid-out child components."""
        return QRectF(0, 0, self._width, self._height)

    def set_drop_target_highlight(self, highlight: bool) -> None:
        """Forwards the drop target highlight state to the underlying SocketLinkItem."""
        if self.link_item:
            self.link_item.set_drop_target_highlight(highlight)
        else:
            logger.warning(f"SocketItem {self.socket_address} has no link_item to set drop target highlight.")

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
