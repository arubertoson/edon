from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsObject

from edon_ui import theme

if TYPE_CHECKING:
    from edon_ui.items.edge import EdgeItem


class SocketCircleItem(QGraphicsEllipseItem):
    """Represents the interactive circular connection point of a socket.
    Its (0,0) is its visual and logical center.
    It is linked to a logical socket entity via its name and parent node entity ID.
    """

    def __init__(
        self,
        parent,
        socket_entity_name: str,
        parent_node_entity_id: str,
        visual_type_key: str = "default",
    ):
        self._radius = theme.SOCKET_RADIUS
        ellipse_rect = QRectF(-self._radius, -self._radius, 2 * self._radius, 2 * self._radius)
        super().__init__(ellipse_rect, parent)

        self.socket_entity_name = socket_entity_name
        self.parent_node_entity_id = parent_node_entity_id
        self.visual_type_key = visual_type_key

        self.setAcceptHoverEvents(True)

        self._original_fill_color = theme.SOCKET_FILL_COLORS.get(self.visual_type_key, theme.SOCKET_FILL_COLOR_DEFAULT)
        self._hover_fill_color = self._original_fill_color.lighter(150)
        self._drop_target_highlight_color = QColor(Qt.GlobalColor.green).lighter(120)  # Placeholder: bright green

        self._is_hovered = False
        self._is_drop_target = False
        self._is_disabled = False
        self._connected_edges: set["EdgeItem"] = set()

        pen = QPen(theme.SOCKET_BORDER_COLOR)
        pen.setWidthF(1.0)
        self.setPen(pen)
        self.setBrush(QBrush(self._original_fill_color))

    def add_edge(self, edge_item):
        self._connected_edges.add(edge_item)

    def remove_edge(self, edge_item):
        self._connected_edges.discard(edge_item)

    @property
    def connected_edges(self) -> set["EdgeItem"]:
        return self._connected_edges

    @property
    def is_input(self) -> bool:
        """Get the is_input flag from the parent SocketRowItem"""
        if self.parentItem():
            return self.parentItem().is_input
        return False

    def _update_brush(self):
        if self._is_drop_target:
            self.setBrush(QBrush(self._drop_target_highlight_color))
        elif self._is_hovered:
            self.setBrush(QBrush(self._hover_fill_color))
        else:
            self.setBrush(QBrush(self._original_fill_color))
        self.update()

    def set_drop_target_highlight(self, highlight: bool):
        if self._is_disabled:
            return

        if self._is_drop_target != highlight:
            self._is_drop_target = highlight
            self._update_brush()

    def set_disabled_visual(self, disabled: bool):
        """
        Visually indicate that this socket is not a valid drop target (e.g., gray out).
        """
        logger.debug(f"Setting socket {self.socket_entity_name} disabled state to {disabled}")
        self._is_disabled = disabled
        self.setOpacity(0.3 if disabled else 1.0)
        self.update()

    def hoverEnterEvent(self, event):
        if not self._is_disabled:
            self._is_hovered = True
            self._update_brush()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._is_disabled:
            self._is_hovered = False
            self._update_brush()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug(
                f"SocketCircleItem '{self.parent_node_entity_id}::{self.socket_entity_name}' pressed at {event.scenePos()}"
            )

            self.scene().start_edge_drag(self, event.scenePos())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.scene().is_dragging_edge():
            self.scene().update_dragged_edge(event.scenePos())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            logger.debug(
                f"SocketCircleItem '{self.parent_node_entity_id}::{self.socket_entity_name}' released at {event.scenePos()}"
            )
            if self.scene().is_dragging_edge():
                self.scene().finish_edge_drag(event.scenePos())
                event.accept()
            else:
                # If not dragging (e.g. simple click), still accept to consume event
                # or pass to super if other release behaviors are desired.
                super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)  # Pass to parent if not left button


class SocketRowItem(QGraphicsObject):
    """Represents a full row for a socket, including its placeholder content and connection circle.
    Its (0,0) is its top-left corner.
    It is linked to a logical socket entity via its name and parent node entity ID.
    """

    def __init__(
        self,
        parent,
        is_input: bool,
        socket_entity_name: str,
        parent_node_entity_id: str,
        socket_widget: QGraphicsObject,
        socket_circle: SocketCircleItem | None = None,
    ):
        super().__init__(parent)
        self.is_input = is_input
        self.socket_entity_name = socket_entity_name
        self.parent_node_entity_id = parent_node_entity_id

        self.socket_widget = socket_widget
        self.socket_circle = socket_circle
        self.socket_widget.setParentItem(self)
        self.socket_circle.setParentItem(self)

        self._layout_socket_row()

    # XXX: Handler if SocketRowItem needs to react directly to value changes
    # def on_content_value_changed(self, value):
    #     logger.debug(f"SocketRowItem ({self.parent_node_entity_id}::{self.socket_entity_name}) detected value change: {value}")
    # Potentially emit another signal or interact with GraphManager

    def get_required_height(self) -> float:
        # The row height should be the max of the socket circle diameter and the widget's height
        widget_height = self.socket_widget.boundingRect().height()
        circle_diameter = self.socket_circle._radius * 2
        return max(widget_height, circle_diameter)

    def get_required_width(self) -> float:
        widget_width = self.socket_widget.boundingRect().width()
        circle_diameter = self.socket_circle._radius * 2

        # Plus any horizontal padding you want between circle and widget
        return circle_diameter + theme.SOCKET_HORIZONTAL_PADDING + widget_width

    def _layout_socket_row(self):
        row_center_y = self.get_required_height() / 2
        circle_radius = self.socket_circle._radius
        content_width = self.socket_widget.boundingRect().width()

        if self.is_input:
            # Input: Circle [Space] ContentPlaceholder
            offset_x = circle_radius + theme.SOCKET_HORIZONTAL_PADDING

            self.socket_circle.setPos(0, row_center_y)
            self.socket_widget.setPos(offset_x, 0)
        else:
            # Output: ContentPlaceholder [Space] Circle
            circle_center_x = content_width + theme.SOCKET_HORIZONTAL_PADDING + circle_radius

            self.socket_circle.setPos(circle_center_x, row_center_y)
            self.socket_widget.setPos(0, 0)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.get_required_width(), self.get_required_height())
