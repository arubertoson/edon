from PySide6.QtCore import QRectF, Qt  # Qt needed for painter.setPen(Qt.red) if debugging
from PySide6.QtGui import QPainter, QPen, QBrush, QColor  # QColor not directly used if only using theme
from PySide6.QtWidgets import QGraphicsObject, QGraphicsRectItem

from edon_ui import theme


class SocketCircleItem(QGraphicsObject):
    """Represents the interactive circular connection point of a socket.
    Its (0,0) is its visual and logical center.
    It is linked to a logical socket entity via its name and parent node entity ID.
    """

    def __init__(
        self,
        parent,
        is_input: bool,
        socket_entity_name: str,
        parent_node_entity_id: str,
        visual_type_key: str = "default",
    ):
        super().__init__(parent)

        self.is_input = is_input
        self.socket_entity_name = socket_entity_name
        self.parent_node_entity_id = parent_node_entity_id
        self.visual_type_key = visual_type_key

        self._radius = theme.SOCKET_RADIUS
        self.setAcceptHoverEvents(True)

        self._original_fill_color = theme.SOCKET_FILL_COLORS.get(self.visual_type_key, theme.SOCKET_FILL_COLOR_DEFAULT)
        # General hover makes the color lighter
        self._hover_fill_color = self._original_fill_color.lighter(150)
        # Color for when this socket is a valid drop target during a connection drag
        self._drop_target_highlight_color = QColor(Qt.green).lighter(120)  # Placeholder: bright green

        self._current_fill_color = self._original_fill_color
        self._is_hovered = False
        self._is_drop_target = False

    def _update_current_fill_color(self):
        if self._is_drop_target:
            self._current_fill_color = self._drop_target_highlight_color
        elif self._is_hovered:
            self._current_fill_color = self._hover_fill_color
        else:
            self._current_fill_color = self._original_fill_color
        self.update()

    def set_drop_target_highlight(self, highlight: bool):
        if self._is_drop_target != highlight:
            self._is_drop_target = highlight
            self._update_current_fill_color()

    def boundingRect(self) -> QRectF:
        return QRectF(-self._radius, -self._radius, 2 * self._radius, 2 * self._radius)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(theme.SOCKET_BORDER_COLOR)
        pen.setWidthF(1.0)
        painter.setPen(pen)
        painter.setBrush(QBrush(self._current_fill_color))
        painter.drawEllipse(self.boundingRect())

    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self._update_current_fill_color()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self._update_current_fill_color()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Use new identifiers for logging
            print(
                f"SocketCircleItem '{self.parent_node_entity_id}::{self.socket_entity_name}' pressed at {event.scenePos()}"
            )
            if self.scene():
                self.scene().start_edge_drag(self, event.scenePos())
            event.accept()
        else:
            super().mousePressEvent(event)  # Pass to parent if not left button

    def mouseMoveEvent(self, event):
        if self.scene().is_dragging_edge():
            self.scene().update_dragged_edge(event.scenePos())
            event.accept()
        else:
            super().mouseMoveEvent(event)  # Pass to parent if not dragging

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Use new identifiers for logging
            print(
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

    HORIZONTAL_PADDING = 5.0
    CONTENT_CIRCLE_SPACING = 8.0  # Renamed from LABEL_CIRCLE_SPACING
    CONTENT_ITEM_FIXED_WIDTH = 70.0
    CONTENT_ITEM_VERTICAL_MARGIN = 4.0  # Small margin for the placeholder rect within the row

    def __init__(
        self,
        parent,
        is_input: bool,
        socket_entity_name: str,
        parent_node_entity_id: str,
        socket_visual_type: str = "default",
        label_text: str = "",  # label_text will eventually come from the logical socket
    ):
        super().__init__(parent)
        self.is_input = is_input
        # Store for potential direct access if needed, though primarily used for child SocketCircleItem
        self.socket_entity_name = socket_entity_name
        self.parent_node_entity_id = parent_node_entity_id

        # Create placeholder content item (was label_item)
        self.visual_content_item = QGraphicsRectItem(self)
        content_height = self.get_required_height() - self.CONTENT_ITEM_VERTICAL_MARGIN * 2
        self.visual_content_item.setRect(0, 0, self.CONTENT_ITEM_FIXED_WIDTH, content_height)
        self.visual_content_item.setBrush(QBrush(QColor(70, 70, 70, 200)))  # Semi-transparent dark gray
        self.visual_content_item.setPen(QPen(QColor(90, 90, 90), 0.8))  # Slightly lighter border

        self.socket_circle = SocketCircleItem(
            self,
            is_input=self.is_input,
            socket_entity_name=self.socket_entity_name,  # Pass new ID info
            parent_node_entity_id=self.parent_node_entity_id,  # Pass new ID info
            visual_type_key=socket_visual_type,
        )
        self._layout_socket_row()

    def get_required_height(self) -> float:
        return theme.SOCKET_ROW_HEIGHT

    def get_required_width(self) -> float:
        content_item_w = self.visual_content_item.rect().width()
        circle_diameter = self.socket_circle._radius * 2
        return content_item_w + circle_diameter

    def _layout_socket_row(self):
        """Positions child items (placeholder content, socket circle) within this row item."""
        row_center_y = self.get_required_height() / 2

        circle_radius = self.socket_circle._radius
        content_width = self.visual_content_item.rect().width()

        if self.is_input:
            # Input: Circle [Space] ContentPlaceholder
            offset_x = circle_radius + self.HORIZONTAL_PADDING

            self.socket_circle.setPos(0, row_center_y)
            self.visual_content_item.setPos(offset_x, self.CONTENT_ITEM_VERTICAL_MARGIN)
        else:
            # Output: ContentPlaceholder [Space] Circle
            circle_center_x = content_width + self.HORIZONTAL_PADDING + circle_radius

            self.visual_content_item.setPos(0, self.CONTENT_ITEM_VERTICAL_MARGIN)
            self.socket_circle.setPos(circle_center_x, row_center_y)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.get_required_width(), self.get_required_height())

    def paint(self, painter: QPainter, option, widget=None):
        # Optionally draw the bounding rect of the SocketRowItem itself for debugging
        # painter.setPen(QPen(Qt.yellow, 0.5))
        # painter.drawRect(self.boundingRect())
        pass  # Child items (placeholder rect, circle) handle their own painting
