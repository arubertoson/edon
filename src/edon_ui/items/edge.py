"""Graphical representation of socket connections.

Provides classes and utility functions to compute and render visual edges that
connect socket items in the scene.
"""

from collections.abc import Callable
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget

from edon.socket import SocketRole
from edon.graph import EdgeKey, SocketAddress
from edon_ui import theme
from edon_ui.items.socket import SocketItem, SocketLinkItem  # Added SocketItem

PathCalculatorType = Callable[[QPointF, QPointF, bool, SocketRole], QPainterPath]


def straight_line_path_calculator(
    p1: QPointF, p2: QPointF, active: bool, starting_socket_role: SocketRole
) -> QPainterPath:
    """
    Calculates a straight-line QPainterPath between two points.

    Returns a direct line connecting the start and end positions.
    """
    path = QPainterPath()
    path.moveTo(p1)
    path.lineTo(p2)

    return path


def bezier_path_calculator(p1: QPointF, p2: QPointF, active: bool, starting_socket_role: SocketRole) -> QPainterPath:
    """
    Calculates a cubic Bezier curve QPainterPath between two points.

    Returns a smooth curve computed using horizontal offsets from the endpoints.
    """
    path = QPainterPath()
    path.moveTo(p1)

    # Calculate horizontal offset between start and end
    dx = p2.x() - p1.x()
    # dy = p2.y() - p1.y() # Vertical distance, not directly used for this curve style

    # Configurable parameters (ideally from theme.py)
    horizontal_offset_factor = 0.6  # How far out control points extend, proportional to dx
    min_horizontal_offset = 30.0  # Minimum curve handle length in pixels
    max_horizontal_offset = 150.0  # Maximum curve handle length in pixels

    # Calculate absolute offset magnitude based on horizontal distance (dx)
    offset_magnitude_abs = abs(dx) * horizontal_offset_factor
    offset_magnitude_abs = max(min_horizontal_offset, offset_magnitude_abs)
    offset_magnitude_abs = min(max_horizontal_offset, offset_magnitude_abs)

    # Determine control point offset for the starting socket:
    # For TARGET role, control point extends to the left; otherwise, to the right.
    ctrl1_x_offset: float
    ctrl2_x_offset: float
    if starting_socket_role == SocketRole.TARGET:
        ctrl1_x_offset = -offset_magnitude_abs
    else:
        ctrl1_x_offset = offset_magnitude_abs

    # Determine control point offset for the target:
    # For an active (dragging) edge, the offset opposes the drag direction.
    # For a fixed target, the offset depends on the target socket's role.
    if active:
        if dx >= 0:
            ctrl2_x_offset = -offset_magnitude_abs
        else:
            ctrl2_x_offset = offset_magnitude_abs
    else:
        if starting_socket_role == SocketRole.TARGET:
            ctrl2_x_offset = offset_magnitude_abs
        else:
            ctrl2_x_offset = -offset_magnitude_abs

    ctrl1 = QPointF(p1.x() + ctrl1_x_offset, p1.y())
    ctrl2 = QPointF(p2.x() + ctrl2_x_offset, p2.y())

    path.cubicTo(ctrl1, ctrl2, p2)

    return path


class DraggingEdgeItem(QGraphicsPathItem):
    """
    Temporary visual edge used during socket connection dragging.

    Provides real-time feedback by updating its path as the mouse moves.
    """

    Type = QGraphicsItem.UserType + 2  # type: ignore[attr-defined]

    def __init__(
        self,
        source_socket_item: SocketItem,
        initial_mouse_scene_pos: QPointF,
        path_calculator: PathCalculatorType = straight_line_path_calculator,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(parent)

        self.source_socket_item: SocketItem = source_socket_item
        self._source_pos: QPointF = self.source_socket_item.link_item.scenePos()
        self._current_target_pos: QPointF = initial_mouse_scene_pos
        self._path_calculator: PathCalculatorType = path_calculator

        self.setZValue(theme.EDGE_Z_VALUE_DRAGGING)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

        self._pen: QPen = QPen(theme.EDGE_COLOR_DRAGGING, theme.EDGE_THICKNESS_DRAGGING)
        self._pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        self._update_internal_path()

    def _update_internal_path(self) -> None:
        self._source_pos = self.source_socket_item.link_item.scenePos()  # Use link_item for position
        # Access role directly from the SocketItem
        starting_role = self.source_socket_item.role
        path = self._path_calculator(self._source_pos, self._current_target_pos, True, starting_role)
        self.setPath(path)

    def update_target_position(self, new_mouse_scene_pos: QPointF) -> None:
        if self._current_target_pos != new_mouse_scene_pos:
            self.prepareGeometryChange()

            self._current_target_pos = new_mouse_scene_pos
            self._update_internal_path()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen)
        painter.drawPath(self.path())

    def type(self) -> int:
        return self.__class__.Type


class EdgeItem(QGraphicsPathItem):
    """
    Visual edge connecting two socket items.

    Dynamically updates its path based on socket movements and renders with styling
    that reflects its interaction state.
    """

    Type = QGraphicsItem.UserType + 1  # type: ignore[attr-defined]

    def __init__(
        self,
        source_socket_item: SocketItem,  # Changed from SocketLinkItem
        target_socket_item: SocketItem,  # Changed from SocketLinkItem
        path_calculator: PathCalculatorType = straight_line_path_calculator,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self.setZValue(theme.EDGE_Z_VALUE)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._path_calculator = path_calculator

        self.source_socket_item: SocketItem = source_socket_item  # Type hint updated
        self.target_socket_item: SocketItem = target_socket_item  # Type hint updated

        # Positions are taken from the link_item of the SocketItem
        self._source_pos: QPointF = self.source_socket_item.link_item.scenePos()
        self._target_pos: QPointF = self.target_socket_item.link_item.scenePos()

        self._pen = QPen(theme.EDGE_COLOR_DEFAULT, theme.EDGE_THICKNESS)
        self._pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._pen_selected = QPen(theme.EDGE_COLOR_SELECTED, theme.EDGE_THICKNESS)
        self._pen_selected.setCapStyle(Qt.PenCapStyle.RoundCap)

        self._edge_key: EdgeKey | None = None

        self.update_path()

    @property
    def edge_key(self) -> EdgeKey:
        if not self._edge_key:
            # Access socket_address directly from SocketItem
            source_socket_addr = self.source_socket_item.socket_address
            target_socket_addr = self.target_socket_item.socket_address
            self._edge_key = EdgeKey(source_socket_addr, target_socket_addr)
        return self._edge_key

    def boundingRect(self) -> QRectF:
        """
        Returns the bounding rectangle of this edge.

        The rectangle includes padding around the path to make it easier to interact with,
        especially if the line is thin.
        """
        path_rect = self.path().boundingRect()
        padding = self._pen.widthF() * 4
        return path_rect.adjusted(-padding, -padding, padding, padding)

    def update_path(self) -> None:
        self.prepareGeometryChange()

        # Positions are taken from the link_item of the SocketItem
        self._source_pos = self.source_socket_item.link_item.scenePos()
        self._target_pos = self.target_socket_item.link_item.scenePos()

        # An EdgeItem is always static when it simply "exists", meaning, it's inactive and it starts
        # from it's source role. The role is taken directly from the source SocketItem.
        path = self._path_calculator(self._source_pos, self._target_pos, False, self.source_socket_item.role)
        self.setPath(path)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        if self.isSelected():
            pen = self._pen_selected
        else:
            pen = self._pen

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.drawPath(self.path())

    def type(self) -> int:
        return self.__class__.Type
