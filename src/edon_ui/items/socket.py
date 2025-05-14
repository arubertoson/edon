from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsObject, QGraphicsItem

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
        if self.parentItem():
            self.parentItem().set_connected_state(True)

    def remove_edge(self, edge_item):
        self._connected_edges.discard(edge_item)
        if self.parentItem():
            if not self._connected_edges:
                self.parentItem().set_connected_state(False)

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
    """A composable row for a socket, containing optional label, circle, and widget.

    Args:
        label: The type label (optional).
        circle: The connection circle (optional).
        widget: The input/output widget (optional).
        layout_mode: 'input' or 'output' (affects layout).
        parent: The parent QGraphicsItem.
    """

    layoutChanged: Signal = Signal()

    def __init__(
        self,
        label: QGraphicsItem | None = None,
        circle: QGraphicsItem | None = None,
        widget: QGraphicsItem | None = None,
        socket_entity_name: str | None = None,
        parent_entity_node_id: str | None = None,
        is_input: bool = True,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.label = label
        self.circle = circle
        self.widget = widget
        self.is_input = is_input
        self.socket_entity_name = socket_entity_name
        self.parent_entity_node_id = parent_entity_node_id

        for item in (self.label, self.circle, self.widget):
            if item is not None:
                item.setParentItem(self)

        if self.label:
            if self.is_input:
                self.label.set_alignment(Qt.AlignmentFlag.AlignLeft)
            else:
                self.label.set_alignment(Qt.AlignmentFlag.AlignRight)

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
            if self.circle:
                x = -circle_radius - padding
                self.circle.setPos(x, row_height / 2)
                x += circle_radius + padding
            if self.label:
                self.label.setPos(x, 0)
                y = self.label.boundingRect().height()
            if self.widget:
                self.widget.setPos(x, y)
        # Layout for output: [label][padding][circle]
        else:
            if self.label:
                self.label.setPos(0, 0)
                x += self.label.boundingRect().width() + padding
            if self.circle:
                y = self.label.boundingRect().height() / 2
                x += circle_radius
                self.circle.setPos(x, y)
            if self.widget:
                self.widget.setPos(0, 0)
                # x += self.widget.boundingRect().width() + padding

        children = [item for item in (self.label, self.widget, self.circle) if item is not None and item.isVisible()]

        min_x = min(child.pos().x() for child in children)
        min_y = min(child.pos().y() for child in children)
        max_x = max(child.pos().x() + child.boundingRect().width() for child in children)
        max_y = max(child.pos().y() + child.boundingRect().height() for child in children)

        new_width = max_x - min_x
        new_height = max_y - min_y

        if self._width != new_width or self._height != new_height:
            self.prepareGeometryChange()
            self._width = new_width
            self._height = new_height
            self.update()

        self.layoutChanged.emit()

    def get_effective_width(self) -> float:
        """Returns the effective width of the row, accounting for label and widget widths."""
        if self.label:
            return self.label.boundingRect().width()
        if self.widget:
            return self.widget.boundingRect().width()
        return 0

    def get_required_width(self) -> float:
        """Returns the total width required by the row.

        Returns:
            The total width required by the row, including all components and padding.
        """
        width: float = 0
        padding: float = theme.SOCKET_HORIZONTAL_PADDING
        for item in (self.label, self.widget, self.circle):
            if item is not None:
                width += item.boundingRect().width() + padding
        return max(width - padding, 0)  # Remove last padding

    def get_required_height(self) -> float:
        """Returns the maximum height required by the row.

        Returns:
            The maximum height required by the row, based on its components.
        """
        heights: list[float] = [
            item.boundingRect().height() for item in (self.label, self.widget, self.circle) if item is not None
        ]
        return max(heights) if heights else 0

    def boundingRect(self) -> QRectF:
        """Returns the bounding rectangle of the row.

        Returns:
            The bounding rectangle covering the entire row.
        """
        return QRectF(0, 0, self._width, self._height)

    def _swap_to_label(self):
        if not self.is_input:
            return

        self.widget.hide()
        self.widget.setParentItem(None)
        self._do_layout()

    def _swap_to_editable(self):
        if not self.is_input:
            return

        self.widget.show()
        self.widget.setParentItem(self)
        self._do_layout()

    def set_connected_state(self, connected: bool):
        """Swap between editable widget and label depending on connection state (for input sockets only). Emits layoutChanged."""
        if not self.is_input:
            return

        if connected:
            self._swap_to_label()
        else:
            self._swap_to_editable()
