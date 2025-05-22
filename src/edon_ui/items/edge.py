"""Defines the EdgeItem class for representing connections between sockets in the UI.

This module provides the visual representation of an edge (connection)
within the graphics scene, linking two SocketCircleItem instances.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget

from edon_ui import theme
from edon_ui.items.socket import SocketCircleItem


class EdgeItem(QGraphicsPathItem):
    """
    Represents a visual edge (typically a line or curve) in the graphics scene,
    connecting two `SocketCircleItem` instances.

    This item is responsible for:
    - Storing references to its source and (optional) target sockets.
    - Maintaining and updating its visual path based on socket positions.
    - Drawing itself with appropriate styling (e.g., color, thickness).
    - Managing its Z-value for correct stacking order during dragging and when finalized.

    Attributes:
        _source_socket_item (SocketCircleItem): The socket from which the edge originates.
        _target_socket_item (SocketCircleItem | None): The socket to which the edge connects.
                                                    None if the edge is temporary (e.g., being dragged).
        _source_pos (QPointF): The last known scene position of the source socket.
        _target_pos (QPointF): The last known scene position of the target socket or mouse cursor.
        _pen (QPen): The pen used for drawing the edge.
        _settled_z_value (float): The Z-value the edge should have when finalized.
    """

    def __init__(
        self, source_socket_item: SocketCircleItem, initial_target_pos: QPointF, parent: QGraphicsItem | None = None
    ) -> None:
        """
        Initializes a new EdgeItem.

        The edge is initially set to a high Z-value to ensure it's drawn on top
        during dragging operations.

        Args:
            source_socket_item: The `SocketCircleItem` from which this edge originates.
            initial_target_pos: The initial scene position for the target end of the edge
                                (typically the mouse cursor position when dragging starts).
            parent: The parent item in the QGraphicsScene hierarchy (optional).
        """
        super().__init__(parent)

        self._settled_z_value = theme.EDGE_Z_VALUE
        self.setZValue(theme.EDGE_Z_VALUE_DRAGGING)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        self._source_socket_item: SocketCircleItem = source_socket_item
        self._target_socket_item: SocketCircleItem | None = None

        self._source_pos: QPointF = self._source_socket_item.scenePos()
        self._target_pos: QPointF = initial_target_pos

        self._pen = QPen(theme.EDGE_COLOR_DEFAULT, theme.EDGE_THICKNESS)
        self._pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._pen_selected = QPen(theme.EDGE_COLOR_SELECTED, theme.EDGE_THICKNESS)
        self._pen_selected.setCapStyle(Qt.PenCapStyle.RoundCap)

        self.update_path()

    def settle_z_value(self) -> None:
        """
        Sets the Z-value of the edge to its 'settled' or finalized state.
        This is typically called when the edge is successfully connected.
        """
        self.setZValue(self._settled_z_value)

    @property
    def edge_key(self) -> EdgeKey:
        source_socket_addr = SocketAddress(
            self.source_socket_item.node_entity_id, self.source_socket_item.socket_entity_name
        )
        target_socket_addr = SocketAddress(
            self.target_socket_item.node_entity_id, self.target_socket_item.socket_entity_name
        )
        return EdgeKey(source_socket_addr, target_socket_addr)

    @property
    def source_socket_item(self) -> SocketCircleItem:
        """The source `SocketCircleItem` of this edge."""
        return self._source_socket_item

    @property
    def target_socket_item(self) -> SocketCircleItem | None:
        """The target `SocketCircleItem` of this edge, or None if not yet connected."""
        return self._target_socket_item

    def set_target_pos(self, scene_pos: QPointF) -> None:
        """
        Updates the target position of the edge, typically used when dragging.

        Args:
            scene_pos: The new target position in scene coordinates.
        """
        self._target_pos = scene_pos
        self.update_path()

    def set_target_socket(self, target_socket_item: SocketCircleItem) -> None:
        """
        Sets the final target socket for the edge and snaps the edge's end point
        to the target socket's center.

        Args:
            target_socket_item: The `SocketCircleItem` to connect to.
        """
        self._target_socket_item = target_socket_item
        self._target_pos = self._target_socket_item.scenePos()
        self.update_path()

    def clear_target_socket(self) -> None:
        """Clears the target socket of this edge, making its target end floating."""
        self._target_socket_item = None

    def update_path(self) -> None:
        """
        Recalculates and sets the QPainterPath for the edge.
        This method fetches the current scene positions of its source and target
        (if finalized) sockets to ensure the path is up-to-date.
        Uses a cubic Bezier curve for drawing.
        """
        # XXX: Trying to comment out, don't think this is necesary.
        # if not self._source_socket_item or not self.scene():  # Basic safety check
        #     # If source_socket_item is None (e.g., edge being created but source not fully set)
        #     # or if the item is not yet in a scene, we can't get scenePos reliably.
        #     return

        self.prepareGeometryChange()

        p1: QPointF = self._source_socket_item.scenePos()
        p2: QPointF
        if self._target_socket_item:
            p2 = self._target_socket_item.scenePos()
        else:
            # For temp_edge, _target_pos is already in scene coordinates (mouse cursor)
            p2 = self._target_pos

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
        if self._source_socket_item.is_input:
            ctrl1_x_offset = -offset_magnitude_abs
        else:
            ctrl1_x_offset = offset_magnitude_abs
        ctrl1 = QPointF(p1.x() + ctrl1_x_offset, p1.y())

        # Determine orientation for ctrl2 based on target socket type or drag direction
        ctrl2_x_offset: float
        if self._target_socket_item:
            # Target is a fixed socket
            # If target is an input, control point extends to its left (relative to p2).
            # If target is an output, control point extends to its right (relative to p2).
            if self._target_socket_item.is_input:
                ctrl2_x_offset = -offset_magnitude_abs
            else:
                ctrl2_x_offset = offset_magnitude_abs
        else:
            # Target is the mouse cursor (p2), edge is being dragged
            # ctrl2's offset should be opposite to ctrl1's effective direction relative to p2.
            # If dragging generally rightwards (dx >= 0), ctrl2 pulls left from p2.
            # If dragging generally leftwards (dx < 0), ctrl2 pulls right from p2.
            if dx >= 0:
                ctrl2_x_offset = -offset_magnitude_abs
            else:
                ctrl2_x_offset = offset_magnitude_abs
        ctrl2 = QPointF(p2.x() + ctrl2_x_offset, p2.y())

        path.cubicTo(ctrl1, ctrl2, p2)
        self.setPath(path)
        self.update()

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        """
        Paints the edge.

        Args:
            painter: The QPainter instance to use for drawing.
            option: Provides style options for the item.
            widget: The widget that is being painted on (optional).
        """
        if self.isSelected():
            pen = self._pen_selected
        else:
            pen = self._pen

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.drawPath(self.path())

    def boundingRect(self) -> QRectF:
        """
        Returns the bounding rectangle of this edge.

        The rectangle includes padding around the path to make it easier to interact with,
        especially if the line is thin.
        """
        path_rect = self.path().boundingRect()
        padding = self._pen.widthF() * 4
        return path_rect.adjusted(-padding, -padding, padding, padding)
