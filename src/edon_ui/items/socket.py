"""Defines visual components related to node sockets in the UI.

This module includes classes for individual socket connection points (`SocketCircleItem`)
and rows that can contain a socket circle, label, and widget (`SocketRowItem`),
along with a protocol (`SocketComponent`) for items within a socket row.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
)

from edon.types import SocketAddress, SocketDisplayState, SocketRole
from edon_ui import theme
from edon_ui.widgets.adaptors import SocketTextAdaptor, SocketWidgetAdaptor

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsSceneHoverEvent

    from edon_ui.items.node import NodeItem
    from edon_ui.views.scene import GraphicsScene


@runtime_checkable
class SocketComponent(Protocol):
    """
    Protocol defining the interface for a visual component within a SocketRowItem.

    Extends QGraphicsItem to inherit all the standard Qt graphics functionality,
    and adds the specific layout methods needed for socket components.
    """

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


@dataclass
class SocketComponents:
    """Pure data structure holding socket visual components."""

    link: SocketLinkItem
    label: SocketTextAdaptor
    widget: SocketWidgetAdaptor
    display_state: SocketDisplayState

    def __post_init__(self):
        self.transition_to(self.display_state)

    def height(self) -> float:
        return sum(
            [_.get_required_component_height() for _ in self.visible() if _ is not self.link]
        )

    def width(self) -> float:
        return max(
            [_.get_required_component_width() for _ in self.visible() if _ is not self.link]
        )

    def transition_to(self, state: SocketDisplayState) -> None:
        match state:
            case SocketDisplayState.ALL:
                self.link.show()
                self.label.show()
                self.widget.show()
            case SocketDisplayState.LINK_LABEL:
                self.link.show()
                self.label.show()
                self.widget.hide()
            case SocketDisplayState.LINK_WIDGET:
                self.link.show()
                self.label.hide()
                self.widget.show()
            case SocketDisplayState.LABEL:
                self.label.show()
                self.link.hide()
                self.widget.hide()
            case SocketDisplayState.WIDGET:
                self.link.hide()
                self.label.hide()
                self.widget.show()

    def __iter__(self) -> Iterator[SocketComponent]:
        return iter([self.link, self.label, self.widget])

    def visible(self) -> list[SocketWidgetAdaptor]:
        return [c for c in self if c.isVisible()]


def _layout_target_socket(
    components: SocketComponents, padding: float = theme.SOCKET_HORIZONTAL_PADDING
) -> None:
    """Layout components for TARGET role: [circle][padding][content]
    Content (label/widget) is stacked vertically and starts at x=0.
    Circle is positioned to the left of content, vertically centered with the primary content component.
    """
    current_y = 0.0

    label, label_visble = components.label, components.label.isVisible()
    widget, widget_visble = components.widget, components.widget.isVisible()
    link, link_visble = components.link, components.link.isVisible()

    assert label_visble or widget_visble, (
        "CORRUPTION: At least one of label and widget needs to be visible."
    )

    logger.error(f"VISIBLE: {label_visble}::{widget_visble}::{link_visble}")

    primary_content_height = 0.0
    if label_visble:
        primary_content_height = label.get_required_component_height()
    elif widget_visble:
        primary_content_height = widget.get_required_component_height()

    if link_visble:
        circle_radius = link.get_required_component_height() / 2.0
        circle_y_center = primary_content_height / 2.0
        circle_x_pos = -circle_radius - padding
        link.setPos(QPointF(circle_x_pos, circle_y_center))

    if label_visble:
        label.setPos(QPointF(0, current_y))
        current_y += components.label.get_required_component_height()

    if widget_visble:
        widget.setPos(QPointF(0, current_y))


def _layout_source_socket(
    components: SocketComponents,
    available_width: float,
    padding: float = theme.SOCKET_HORIZONTAL_PADDING,
) -> None:
    """Layout components for SOURCE role: [content][padding][circle]
    Content (label/widget) is stacked vertically and right-aligned within available_width.
    Circle is positioned to the right of content, vertically centered with the primary content component.
    """
    current_content_y = 0.0

    label, label_visble = components.label, components.label.isVisible()
    widget, widget_visble = components.widget, components.widget.isVisible()
    link, link_visble = components.link, components.link.isVisible()

    assert label_visble or widget_visble, (
        "CORRUPTION: At least one of label and widget needs to be visible."
    )

    primary_content_height = 0.0
    if label_visble:
        primary_content_height = label.get_required_component_height()
    elif widget_visble:
        primary_content_height = widget.get_required_component_height()

    if label_visble:
        label_width = label.get_required_component_width()
        label.setPos(QPointF(available_width - label_width, current_content_y))
        current_content_y += label.get_required_component_height()

    if widget_visble:
        widget_width = widget.get_required_component_width()
        widget.setPos(QPointF(available_width - widget_width, current_content_y))

    if link_visble:
        circle_radius = link.get_required_component_height() / 2.0
        circle_y_center = primary_content_height / 2.0
        circle_x_pos = available_width + circle_radius + padding
        link.setPos(QPointF(circle_x_pos, circle_y_center))


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
    def _socket_item(self) -> SocketItem:
        socket_item = cast(SocketItem, self.parentItem())
        assert isinstance(socket_item, SocketItem), (
            "CORRUPTION: parent item of {self} is not of type `SocketItem`"
        )

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

    def get_required_component_width(self) -> float:
        return self.boundingRect().width()

    def get_required_component_height(self) -> float:
        return self.boundingRect().height()

    def set_not_valid_drop_target(self, disabled: bool) -> None:
        self._is_valid_drop_target = disabled
        self.setOpacity(0.3 if disabled else 1.0)

    def set_drop_target_highlight(self, highlight: bool) -> None:
        if self._is_valid_drop_target:
            return

        if not self._is_drop_target == highlight:
            self._is_drop_target = highlight
            self._update_brush()

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = True
            self._update_brush()

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = False
            self._update_brush()

        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._socket_item.handle_link_press(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        # Check if a drag is active before attempting to call the parent's handler.
        # The parent's handler might assume a drag is in progress.
        scene = cast("GraphicsScene", self.scene())
        if scene.is_dragging_edge():
            self._socket_item.handle_link_move(event)
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
                self._socket_item.handle_link_release(event)
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

    def __init__(
        self,
        role: SocketRole,
        entity_name: str,
        node_entity_id: str,
        components: SocketComponents,
        parent: QGraphicsObject | None = None,
    ) -> None:
        super().__init__(parent)

        self.role = role
        self.entity_name = entity_name
        self.node_entity_id = node_entity_id

        self.components = components
        for item in self.components:
            item.setParentItem(self)

        alignment = Qt.AlignmentFlag.AlignLeft
        if self.role == SocketRole.SOURCE:
            alignment = Qt.AlignmentFlag.AlignRight
        self.components.label.set_text_alignment(alignment)

        self._width: float = 0.0
        self._height: float = 0.0
        self._address: SocketAddress | None = None

        self._calculate_bounding_rect()

    @property
    def link_item(self) -> SocketLinkItem:
        """Provides access to the socket's connection circle (SocketLinkItem)."""
        return self.components.link

    @property
    def address(self) -> SocketAddress:
        if not self._address:
            self._address = SocketAddress(self.node_entity_id, self.entity_name, self.role)
        return self._address

    @property
    def _node_item(self) -> NodeItem:
        from edon_ui.items.node import NodeItem

        node_item = cast(NodeItem, self.parentItem())
        assert isinstance(node_item, NodeItem), (
            "CORRUPTION: parent item of {self} is not of type `NodeItem`"
        )

        return node_item

    @property
    def _scene(self) -> GraphicsScene:
        from edon_ui.views.scene import GraphicsScene

        scene = cast(GraphicsScene, self.scene())
        assert isinstance(scene, GraphicsScene), (
            "CORRUPTION: parent item of {self} is not of type `GraphicsScene`"
        )

        return scene

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def handle_link_press(self, event: QGraphicsSceneMouseEvent) -> None:
        logger.debug(f"SocketItem link in {self.address} pressed at {event.scenePos()}")

        self._scene.edge_drag_initiation_request.emit(self.address, event.scenePos(), self._scene)

    def handle_link_move(self, event: QGraphicsSceneMouseEvent) -> None:
        # The scene's update_dragging_edge method typically doesn't need the socket_address,
        # just the current mouse position.
        self._scene.edge_drag_action(event.scenePos())

    def handle_link_release(self, event: QGraphicsSceneMouseEvent) -> None:
        logger.debug(
            f"SocketItem link '{self.node_entity_id}::{self.entity_name}' released at {event.scenePos()}"
        )

        self._scene.edge_drop_action(event.scenePos())

    def update_layout(self, available_width: float) -> None:
        """Updates the layout of socket components based on role and available width."""
        self._calculate_bounding_rect()

        if self.role == SocketRole.TARGET:
            _layout_target_socket(self.components, theme.SOCKET_HORIZONTAL_PADDING)
        else:
            _layout_source_socket(
                self.components, available_width, theme.SOCKET_HORIZONTAL_PADDING
            )

        self.update()

    def set_drop_target_highlight(self, highlight: bool) -> None:
        """Forwards the drop target highlight state to the underlying SocketLinkItem."""
        self.components.link.set_drop_target_highlight(highlight)

    def transition_to(self, linked: bool) -> None:
        if self.role == SocketRole.SOURCE:
            return

        if linked:
            self.components.transition_to(SocketDisplayState.LINK_LABEL)
        else:
            self.components.transition_to(self.components.display_state)

        self._calculate_bounding_rect()
        self._node_item._on_socket_row_layout_changed()

    def _calculate_bounding_rect(self) -> None:
        """Calculates the bounding rectangle for the SocketItem's main content area.
        This area is defined by the stacked label and/or widget components.
        The SocketItem's own (0,0) is considered the top-left of this label/widget block.
        """
        self.prepareGeometryChange()

        components = self.components.visible()
        assert components, (
            f"CORRUPTION: Node should always have at least one component. {self.components}"
        )

        self._width = self.components.width()
        self._height = self.components.height()

    # def paint(
    #     self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    # ) -> None:
    #     """Overrides the pure virtual paint method from QGraphicsObject.
    #
    #     This method must be implemented, even if it does nothing, to prevent
    #     a pure virtual function call error at runtime when Qt attempts to paint
    #     this QGraphicsObject. In this adaptor, painting is handled by the
    #     child QGraphicsTextItem, so this method intentionally does nothing.
    #     """
    #     pass
