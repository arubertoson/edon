from typing import TYPE_CHECKING

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsTextItem, QStyle


from edon_ui import theme
from edon_ui.items.socket import SocketRowItem

# Forward type declaration for edon.node.Node to avoid circular import if it were to import NodeItem
if TYPE_CHECKING:
    from edon.node import EntityNode as EntityNode


class NodeItem(QGraphicsObject):
    """A visual node item in the editor, representing a logical node entity."""

    positionChanged = Signal()
    sizeChanged = Signal(str)

    def __init__(
        self,
        title: str,
        x: float,
        y: float,
        node_entity_id: str,
        input_sockets: list[SocketRowItem] | None = None,
        output_sockets: list[SocketRowItem] | None = None,
        width: float = theme.NODE_MIN_WIDTH,
        height: float = theme.NODE_MIN_HEIGHT,
    ):
        super().__init__()

        self.title = title
        self.node_entity_id = node_entity_id
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

        self._input_sockets = input_sockets or []
        self._output_sockets = output_sockets or []
        for row in self._input_sockets + self._output_sockets:
            row.setParentItem(self)
            row.layoutChanged.connect(self._on_socket_row_layout_changed)

        self._on_socket_row_layout_changed()

    def _calculate_dynamic_height(self) -> float:
        total_socket_rows_height = theme.NODE_TITLE_HEIGHT + theme.SOCKET_VERTICAL_CONTENT_MARGIN

        for idx, row in enumerate(self._input_sockets + self._output_sockets):
            total_socket_rows_height += row.boundingRect().height()
            if idx < len(self._input_sockets + self._output_sockets) - 1:
                total_socket_rows_height += theme.SOCKET_VERTICAL_ITEM_PADDING

        total_socket_rows_height += theme.SOCKET_VERTICAL_CONTENT_MARGIN
        print(f"total_socket_rows_height: {total_socket_rows_height}")
        print(f"self._min_height_param: {self._min_height_param}")

        content_area_height = max(total_socket_rows_height, theme.NODE_MIN_CONTENT_HEIGHT)

        return max(self._min_height_param, total_socket_rows_height, content_area_height)

    def _calculate_dynamic_width(self) -> float:
        print(f"CALCULATING DYNAMIC WIDTH in {self.title}")
        max_row_w = 0
        all_rows = self._input_sockets + self._output_sockets
        if all_rows:
            max_row_w = max(row.get_effective_width() for row in all_rows)

        for row in all_rows:
            print(f"row {row.socket_entity_name}: {row.get_effective_width()}")

        print(f"max_row_w: {max_row_w}")

        min_content_width = theme.NODE_MIN_WIDTH - (theme.NODE_HORIZONTAL_PADDING * 2)
        calculated_internal_content_width = max(max_row_w, min_content_width)
        calculated_total_width = calculated_internal_content_width  #  + (theme.NODE_HORIZONTAL_PADDING * 2)

        print(f"calculated_total_width: {calculated_total_width}, vs min_width_param: {self._min_width_param}")

        return max(self._min_width_param, calculated_total_width)

    def _layout_socket_rows(self) -> None:
        """Layout input and output socket rows using their required width and height.

        This method positions each socket row within the node, stacking them vertically.
        Output rows are right-aligned, input rows are left-aligned.
        Padding is only added between rows, not after the last row.
        """
        current_row_top_y: float = theme.NODE_TITLE_HEIGHT + theme.SOCKET_VERTICAL_CONTENT_MARGIN

        # Output sockets
        for row_item in self._output_sockets:
            row_item.setPos(0, current_row_top_y)

            current_row_top_y += row_item.boundingRect().height() + theme.SOCKET_VERTICAL_ITEM_PADDING

        # Input sockets
        for idx, row_item in enumerate(self._input_sockets):
            row_item.setPos(0, current_row_top_y)

            current_row_top_y += row_item.boundingRect().height()
            if idx < len(self._input_sockets) - 1:
                current_row_top_y += theme.SOCKET_VERTICAL_ITEM_PADDING

    def _on_socket_row_layout_changed(self):
        """Handle a socket row's layout change by relayout and redraw the node."""
        self.prepareGeometryChange()
        self._layout_socket_rows()
        self._height = self._calculate_dynamic_height()
        self._width = self._calculate_dynamic_width()

        self.update()
        self.sizeChanged.emit(self.node_entity_id)

    def boundingRect(self):
        return QRectF(0, 0, self._width, self._height)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.positionChanged.emit()

        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Main node body
        node_rect = self.boundingRect()
        painter.setBrush(QBrush(theme.NODE_BACKGROUND))

        # Border
        border_width = theme.NODE_BORDER_WIDTH_DEFAULT
        if option.state & QStyle.StateFlag.State_Selected:
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

    def content_rect(self) -> QRectF:
        """Returns the rectangle for the content area, below the title bar, with padding."""
        # Use a consistent border width, ideally fetched from theme or a class const
        # For now, matching the visual border drawn.
        # The main border is drawn with width current_border_width (1.5 or 2.0)
        # We assume content should be placed inside this main border.
        padding = 10.0  # Internal padding for content from the edges of the content space
        content_y_start = theme.NODE_TITLE_HEIGHT

        # The available width for content is node_width - 2*effective_border_for_content_placement
        # The border is outside the fill area in QPainter if pen width > 1, half inside, half outside.
        # To be safe, let's consider full border width for now.
        # However, visually, content is placed relative to the inner edge of the drawn rounded rect.
        # The self.boundingRect() is (0,0, self._width, self._height)
        # The drawn rounded rect fills this.

        content_x = padding
        content_width = self._width - (2 * padding)
        content_height = self._height - content_y_start - padding  # Space from bottom edge

        return QRectF(content_x, content_y_start, content_width, content_height)
