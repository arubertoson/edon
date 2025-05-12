from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPen, QPainterPath
from PySide6.QtWidgets import QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget, QGraphicsItem

from edon_ui import theme
from edon_ui.item.socket import SocketCircleItem


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

    def __init__(self, source_socket_item: SocketCircleItem, initial_target_pos: QPointF, parent=None):
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

    def settle_z_value(self):
        """
        Sets the Z-value of the edge to its 'settled' or finalized state.
        This is typically called when the edge is successfully connected.
        """
        self.setZValue(self._settled_z_value)

    @property
    def source_socket_item(self) -> SocketCircleItem:
        """The source `SocketCircleItem` of this edge."""
        return self._source_socket_item

    @property
    def target_socket_item(self) -> SocketCircleItem:
        """The target `SocketCircleItem` of this edge, or None if not yet connected."""
        return self._target_socket_item

    def set_target_pos(self, scene_pos: QPointF):
        """
        Updates the target position of the edge, typically used when dragging.

        Args:
            scene_pos: The new target position in scene coordinates.
        """
        self._target_pos = scene_pos
        self.update_path()

    def set_target_socket(self, target_socket_item: SocketCircleItem):
        """
        Sets the final target socket for the edge and snaps the edge's end point
        to the target socket's center.

        Args:
            target_socket_item: The `SocketCircleItem` to connect to.
        """
        self._target_socket_item = target_socket_item
        self._target_pos = self._target_socket_item.scenePos()
        self.update_path()

    def clear_target_socket(self):
        """Clears the target socket of this edge, making its target end floating."""
        self._target_socket_item = None
        # self.update_path() # Not strictly necessary here as set_target_pos will follow

    def update_path(self):
        """
        Recalculates and sets the QPainterPath for the edge.

        This method fetches the current scene positions of its source and target
        (if finalized) sockets to ensure the path is up-to-date.
        The path is a straight line by default but can be modified for curves.
        """
        self.prepareGeometryChange()

        self._source_pos = self._source_socket_item.scenePos()
        if self._target_socket_item:
            self._target_pos = self._target_socket_item.scenePos()

        path = QPainterPath()
        path.moveTo(self._source_pos)

        # NOTE: Bezier curve drawing (example, can be refined)
        # dx = self._target_pos.x() - self._source_pos.x()
        # dy = self._target_pos.y() - self._source_pos.y()
        # horizontal_offset_factor = 0.5 # Adjust for more/less curve
        # ctrl1_x = self._source_pos.x() + dx * horizontal_offset_factor
        # ctrl1_y = self._source_pos.y()
        # ctrl2_x = self._target_pos.x() - dx * horizontal_offset_factor
        # ctrl2_y = self._target_pos.y()
        # path.cubicTo(QPointF(ctrl1_x, ctrl1_y), QPointF(ctrl2_x, ctrl2_y), self._target_pos)

        path.lineTo(self._target_pos)
        self.setPath(path)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None):
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