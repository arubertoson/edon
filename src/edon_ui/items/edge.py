"""Defines the EdgeItem class for representing connections between sockets in the UI.

This module provides the visual representation of an edge (connection)
within the graphics scene, linking two SocketCircleItem instances.
"""

from collections.abc import Callable
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget

from edon.socket import SocketRole
from edon.graph import EdgeKey, SocketAddress
from edon_ui import theme
from edon_ui.items.socket import SocketLinkItem

PathCalculatorType = Callable[[QPointF, QPointF], QPainterPath]


def straight_line_path_calculator(
    p1: QPointF, p2: QPointF, active: bool, starting_socket_role: SocketRole
) -> QPainterPath:
    """
    Calculate a straight-line path between two points.

    Args:
        p1 (QPointF): The starting point.
        p2 (QPointF): The ending point.
        active (bool): Indicates if the edge is active.
        starting_socket_role (SocketRole): The role of the starting socket.

    Returns:
        QPainterPath: The computed straight-line path.
    """
    path = QPainterPath()
    path.moveTo(p1)
    path.lineTo(p2)
 
    return path


def bezier_path_calculator(p1: QPointF, p2: QPointF, active: bool, starting_socket_role: SocketRole) -> QPainterPath:
    """
    Calculate a cubic Bezier curve path between two points.

    Args:
        p1 (QPointF): The starting point.
        p2 (QPointF): The ending point.
        active (bool): Indicates if the edge is active.
        starting_socket_role (SocketRole): The role of the starting socket affecting control points.

    Returns:
        QPainterPath: The computed Bezier curve path.
    """
    path = QPainterPath()
    path.moveTo(p1)

    # --- Cubic Bezier Curve Calculation ---
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

    # Determine orientation for ctrl1 based on source socket type
    # If source is an input, control point extends to its left, else to its right.
    ctrl1_x_offset: float
    ctrl2_x_offset: float
    if starting_socket_role == SocketRole.TARGET:
        ctrl1_x_offset = -offset_magnitude_abs
    else:
        ctrl1_x_offset = offset_magnitude_abs

    # Determine orientation for ctrl2 based on target socket type or drag direction
    if active:
        # Target is the mouse cursor (p2), edge is being dragged
        # ctrl2's offset should be opposite to ctrl1's effective direction relative to p2.
        # If dragging generally rightwards (dx >= 0), ctrl2 pulls left from p2.
        # If dragging generally leftwards (dx < 0), ctrl2 pulls right from p2.
        if dx >= 0:
            ctrl2_x_offset = -offset_magnitude_abs
        else:
            ctrl2_x_offset = offset_magnitude_abs
    else:
        # Target is a fixed socket
        # If target is an input, control point extends to its left (relative to p2).
        # If target is an output, control point extends to its right (relative to p2).
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
    Represents a temporary visual edge being dragged from a source socket.
    """

    Type = QGraphicsItem.UserType + 2  # type: ignore[attr-defined]

    def __init__(
        self,
        source_socket_item: SocketLinkItem,
        initial_mouse_scene_pos: QPointF,
        path_calculator: PathCalculatorType = straight_line_path_calculator,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(parent)

        self._source_socket_item: SocketLinkItem = source_socket_item
        self._source_pos: QPointF = self._source_socket_item.scenePos()
        self._current_target_pos: QPointF = initial_mouse_scene_pos
        self._path_calculator: PathCalculatorType = path_calculator

        self.setZValue(theme.EDGE_Z_VALUE_DRAGGING)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

        self._pen: QPen = QPen(theme.EDGE_COLOR_DRAGGING, theme.EDGE_THICKNESS_DRAGGING)
        self._pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        self._update_internal_path()

    @property
    def source_socket_item(self) -> SocketLinkItem:
        return self._source_socket_item

    def _update_internal_path(self) -> None:
        self._source_pos = self._source_socket_item.scenePos()
        path = self._path_calculator(self._source_pos, self._current_target_pos)
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
    Represents a visual edge (typically a line or curve) in the graphics scene,
    connecting two `SocketCircleItem` instances.

    This item is responsible for:
    - Storing references to its source and (optional) target sockets.
    - Maintaining and updating its visual path based on socket positions.
    - Drawing itself with appropriate styling (e.g., color, thickness).
    - Managing its Z-value for correct stacking order during dragging and when finalized.
    """

    Type = QGraphicsItem.UserType + 1  # type: ignore[attr-defined]

    def __init__(
        self,
        source_socket_item: SocketLinkItem,
        target_socket_item: SocketLinkItem,
        path_calculator: PathCalculatorType = straight_line_path_calculator,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self.setZValue(theme.EDGE_Z_VALUE)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._path_calculator = path_calculator

        self.source_socket_item = source_socket_item
        self.target_socket_item = target_socket_item

        self._source_pos: QPointF = self.source_socket_item.scenePos()
        self._target_pos: QPointF = self.target_socket_item.scenePos()

        self._pen = QPen(theme.EDGE_COLOR_DEFAULT, theme.EDGE_THICKNESS)
        self._pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._pen_selected = QPen(theme.EDGE_COLOR_SELECTED, theme.EDGE_THICKNESS)
        self._pen_selected.setCapStyle(Qt.PenCapStyle.RoundCap)

        self._edge_key: EdgeKey | None = None

        self._update_internal_path()

    @property
    def edge_key(self) -> EdgeKey:
        if not self._edge_key:
            source_socket_addr = SocketAddress(
                self.source_socket_item.node_entity_id, self.source_socket_item.socket_entity_name
            )
            target_socket_addr = SocketAddress(
                self.target_socket_item.node_entity_id, self.target_socket_item.socket_entity_name
            )
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

    def _update_internal_path(self) -> None:
        self._source_pos = self.source_socket_item.scenePos()
        self._target_pos = self.target_socket_item.scenePos()

        path = self._path_calculator(self._source_pos, self._target_pos)
        self.setPath(path)

    def socket_moved(self, moved_socket: SocketLinkItem) -> None:
        if moved_socket == self._source_socket_item or moved_socket == self._target_socket_item:
            self.prepareGeometryChange()
            self._update_internal_path()

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
