"""Defines the NodeItem class, the visual representation of a node in the UI.

This module provides the QGraphicsObject subclass that handles rendering,
interaction, and layout for individual nodes within the graphics scene.
"""

from loguru import logger
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from edon_ui import theme

if TYPE_CHECKING:
    from edon_ui.items.socket import SocketItem


class NodeItem(QGraphicsObject):
    """A visual node item in the editor, representing a logical node entity."""

    node_position_update_signal = Signal(str)
    node_redraw_signal = Signal(str)

    def __init__(
        self,
        title: str | None,
        x: float,
        y: float,
        node_entity_id: str,
        target_sockets: list["SocketItem"] | None = None,
        source_sockets: list["SocketItem"] | None = None,
        width: float = theme.NODE_MIN_WIDTH,
        height: float = theme.NODE_MIN_HEIGHT,
    ) -> None:
        super().__init__()

        self.title = title if title is not None else "Untitled"
        self.entity_id = node_entity_id
        self._min_width_param = width
        self._min_height_param = height

        self.setPos(x, y)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)

        self.title_text_item = QGraphicsTextItem(self.title, self)
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)

        self.target_sockets = target_sockets or []
        self.source_sockets = source_sockets or []
        for row in self.target_sockets + self.source_sockets:
            row.setParentItem(self)
            row.layoutChanged.connect(self._on_socket_row_layout_changed)

        self._width: float = 0
        self._height: float = 0

        self._on_socket_row_layout_changed()

    def _calculate_dynamic_height(self) -> float:
        total_socket_rows_height = theme.NODE_TITLE_HEIGHT + theme.SOCKET_VERTICAL_CONTENT_MARGIN

        for idx, row in enumerate(self.target_sockets + self.source_sockets):
            total_socket_rows_height += row.boundingRect().height()
            if idx < len(self.target_sockets + self.source_sockets) - 1:
                total_socket_rows_height += theme.SOCKET_VERTICAL_ITEM_PADDING

        total_socket_rows_height += theme.SOCKET_VERTICAL_CONTENT_MARGIN
        content_area_height = max(total_socket_rows_height, theme.NODE_MIN_CONTENT_HEIGHT)

        return max(self._min_height_param, total_socket_rows_height, content_area_height)

    def _calculate_dynamic_width(self) -> float:
        max_row_w = 0
        all_rows = self.target_sockets + self.source_sockets
        if all_rows:
            max_row_w = max(row.boundingRect().width() for row in all_rows)

        # Remember to remove the padding
        min_content_width = theme.NODE_MIN_WIDTH - (theme.NODE_HORIZONTAL_PADDING * 2)
        calculated_total_width = max(max_row_w, min_content_width)

        return max(self._min_width_param, calculated_total_width)

    def _layout_socket_rows(self) -> None:
        """Layout input and output socket rows using their required width and height.

        This method positions each socket row within the node, stacking them vertically.
        Output rows are right-aligned, input rows are left-aligned.
        Padding is only added between rows, not after the last row.
        """
        current_row_top_y: float = theme.NODE_TITLE_HEIGHT + theme.SOCKET_VERTICAL_CONTENT_MARGIN

        # self._width should have been calculated by _calculate_dynamic_width() before this method is called.
        # This is the width available for the content of the socket rows, inside the node's own padding.
        content_area_width_for_rows = self._width

        # Source sockets
        for row_item in self.source_sockets:
            row_item.update_layout(content_area_width_for_rows)
            # Position the row considering the node's left padding
            row_item.setPos(0, current_row_top_y)
            current_row_top_y += row_item.boundingRect().height() + theme.SOCKET_VERTICAL_ITEM_PADDING

        # Target sockets
        for idx, row_item in enumerate(self.target_sockets):
            row_item.update_layout(content_area_width_for_rows)  # Pass the available width
            # Position the row considering the node's left padding
            row_item.setPos(0, current_row_top_y)
            current_row_top_y += row_item.boundingRect().height()
            if idx < len(self.target_sockets) - 1:
                current_row_top_y += theme.SOCKET_VERTICAL_ITEM_PADDING

    def _on_socket_row_layout_changed(self) -> None:
        """Handle a socket row's layout change by relayouting the entire node."""
        self.prepareGeometryChange()  # Prepare the node for geometry changes

        # Recalculate node's own width first based on potentially changed intrinsic needs of rows
        self._width = self._calculate_dynamic_width()

        # Then, layout socket rows, passing them the available content width
        self._layout_socket_rows()

        # Finally, calculate the node's height based on the new row layouts
        self._height = self._calculate_dynamic_height()

        logger.info(f"Node {self.entity_id} layout changed: {self._width}x{self._height}")

        self.update()  # Redraw the node
        self.node_redraw_signal.emit(self.entity_id)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """Handles item state changes, like position changes.

        Args:
            change: The type of change occurring.
            value: The new value associated with the change.

        Returns:
            The processed value, potentially modified from the input value.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node_position_update_signal.emit(self.entity_id)

        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Main node body
        node_rect = self.boundingRect()
        painter.setBrush(QBrush(theme.NODE_BACKGROUND))

        # Border
        border_width = theme.NODE_BORDER_WIDTH_DEFAULT
        if self.isSelected():
            pen = QPen(theme.NODE_BORDER_SELECTED, theme.NODE_BORDER_WIDTH_SELECTED)
            border_width = theme.NODE_BORDER_WIDTH_SELECTED  # For consistency if used elsewhere
        else:
            pen = QPen(theme.NODE_BORDER_DEFAULT, theme.NODE_BORDER_WIDTH_DEFAULT)
        painter.setPen(pen)
        painter.drawRoundedRect(node_rect, theme.NODE_BORDER_RADIUS, theme.NODE_BORDER_RADIUS)

        # Title Bar area
        # Create a path for the title bar with rounded top corners
        title_bar_rect = QRectF(0, 0, node_rect.width(), theme.NODE_TITLE_HEIGHT)
        # To ensure title bar fill respects the main border radius at top corners:
        # Create a path for the title bar background fill
        # Adjust for half border width to be inside the main border line
        # Corrected title bar drawing logic for perfect rounded tops inside border
        half_border = border_width / 2.0
        fill_title_rect = title_bar_rect.adjusted(
            half_border, half_border, -half_border, 0
        )  # Don't adjust bottom for fill

        title_fill_path = QPainterPath()
        title_fill_path.moveTo(fill_title_rect.left() + theme.NODE_BORDER_RADIUS - half_border, fill_title_rect.top())
        title_fill_path.lineTo(fill_title_rect.right() - theme.NODE_BORDER_RADIUS + half_border, fill_title_rect.top())
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.right() - 2 * theme.NODE_BORDER_RADIUS + half_border,
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS - half_border,  # arc width
                2 * theme.NODE_BORDER_RADIUS - half_border,  # arc height
            ),
            90,
            -90,
        )
        title_fill_path.lineTo(
            fill_title_rect.right(), fill_title_rect.bottom()
        )  # Straight down to bottom of title bar rect
        title_fill_path.lineTo(fill_title_rect.left(), fill_title_rect.bottom())  # Straight across bottom
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.left(),
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS - half_border,
                2 * theme.NODE_BORDER_RADIUS - half_border,
            ),
            180,
            -90,
        )
        title_fill_path.closeSubpath()

        painter.setBrush(QBrush(theme.NODE_TITLE_BACKGROUND))
        painter.setPen(Qt.PenStyle.NoPen)  # No border for the fill path itself
        painter.drawPath(title_fill_path)

        # Position and draw title text (QGraphicsTextItem handles its own drawing)
        # Ensure title_text_item is correctly positioned.
        # The initial positioning in __init__ might not be perfect after font metrics.
        # For truly centered text in a custom-drawn rounded rect, manual calculation is best.
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)

        # Center the QGraphicsTextItem within the title bar rect
        title_text_rect = self.title_text_item.boundingRect()
        title_text_x = (self._width - title_text_rect.width()) / 2
        title_text_y = (theme.NODE_TITLE_HEIGHT - title_text_rect.height()) / 2
        self.title_text_item.setPos(title_text_x, title_text_y)
