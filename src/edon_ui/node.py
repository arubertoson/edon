from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QStyle, QGraphicsObject

from . import theme
from .socket import SocketRowItem


class NodeItem(QGraphicsObject):
    """A node in the editor"""

    positionChanged = Signal()

    # Define a minimum content height for the node, even if no sockets
    MIN_CONTENT_HEIGHT = 20.0

    def __init__(self, title, x, y, width=theme.NODE_MIN_WIDTH, height=theme.NODE_MIN_HEIGHT):
        super().__init__()

        self.title = title
        # Store initial width/height params as minimums
        self._min_width_param = width
        self._min_height_param = height

        # self._width and self._height will be calculated and finalized

        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)  # Important for itemChange() and scene updates
        self.setCacheMode(QGraphicsItem.ItemCoordinateCache)

        self.title_text_item = QGraphicsTextItem(self.title, self)
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)

        self._input_sockets = []
        self._output_sockets = []

        row_in1 = SocketRowItem(
            parent=self,
            is_input=True,
            socket_identifier="in1",
            socket_visual_type="integer",
            label_text="Value A Input",
        )
        self._input_sockets.append(row_in1)
        row_in2 = SocketRowItem(
            parent=self, is_input=True, socket_identifier="in2", socket_visual_type="float", label_text="Value B"
        )
        self._input_sockets.append(row_in2)
        row_in3 = SocketRowItem(
            parent=self, is_input=True, socket_identifier="in3", socket_visual_type="default", label_text="Control"
        )
        self._input_sockets.append(row_in3)

        row_out1 = SocketRowItem(
            parent=self,
            is_input=False,
            socket_identifier="out1",
            socket_visual_type="string",
            label_text="Result Output Long Name",
        )
        self._output_sockets.append(row_out1)

        # --- Calculate Dynamic Sizing (initial calculation) ---
        temp_height = self._calculate_dynamic_height()
        temp_width = self._calculate_dynamic_width()

        # Now, prepare for geometry change BEFORE actually setting self._width, self._height
        self.prepareGeometryChange()

        # Set final _width and _height
        print(f"Setting final _width and _height: {temp_width}, {temp_height}")
        self._height = temp_height
        self._width = temp_width
        # --- End Dynamic Sizing ---

        # Update layout of children based on final size
        self.layout_socket_rows()
        self._update_title_text_position()

    def _calculate_dynamic_height(self) -> float:
        input_rows_height = sum(row.get_required_height() for row in self._input_sockets)
        output_rows_height = sum(row.get_required_height() for row in self._output_sockets)
        total_socket_rows_height = input_rows_height + output_rows_height
        content_area_height = (theme.SOCKET_PADDING * 2) + max(total_socket_rows_height, self.MIN_CONTENT_HEIGHT)
        calculated_total_height = theme.NODE_TITLE_HEIGHT + content_area_height
        return max(self._min_height_param, calculated_total_height)

    def _calculate_dynamic_width(self) -> float:
        max_row_w = 0
        all_rows = self._input_sockets + self._output_sockets
        if all_rows:
            max_row_w = max(row.get_required_width() for row in all_rows)

        min_content_width = theme.NODE_MIN_WIDTH - (theme.NODE_HORIZONTAL_PADDING * 2)
        calculated_internal_content_width = max(max_row_w, min_content_width)
        calculated_total_width = calculated_internal_content_width + (theme.NODE_HORIZONTAL_PADDING * 2)
        return max(self._min_width_param, calculated_total_width)

    def _update_title_text_position(self):
        """Centers the title text item within the title bar."""
        title_text_width = self.title_text_item.boundingRect().width()
        self.title_text_item.setPos(
            (self._width - title_text_width) / 2,
            (theme.NODE_TITLE_HEIGHT - self.title_text_item.boundingRect().height()) / 2,
        )

    def layout_socket_rows(self):
        """Positions SocketRowItems on the node in a single column."""
        current_row_top_y = theme.NODE_TITLE_HEIGHT + theme.SOCKET_PADDING

        for row_item in self._input_sockets:
            row_item.setPos(0, current_row_top_y)
            current_row_top_y += row_item.get_required_height()

        # Outputs continue below inputs in the same column
        for row_item in self._output_sockets:
            row_x = self._width - row_item.get_required_width()
            row_item.setPos(row_x, current_row_top_y)
            current_row_top_y += row_item.get_required_height()

    def boundingRect(self):
        # Define the bounding rectangle of the node
        return QRectF(0, 0, self._width, self._height)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            pass
        elif change == QGraphicsItem.ItemPositionHasChanged:
            self.positionChanged.emit()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        # Main node body
        node_rect = self.boundingRect()
        painter.setBrush(QBrush(theme.NODE_BACKGROUND))

        # Border
        border_width = theme.NODE_BORDER_WIDTH_DEFAULT
        if option.state & QStyle.State_Selected:
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
        painter.setPen(Qt.NoPen)  # No border for the fill path itself
        painter.drawPath(title_fill_path)

        # Position and draw title text (QGraphicsTextItem handles its own drawing)
        # Ensure title_text_item is correctly positioned.
        # The initial positioning in __init__ might not be perfect after font metrics.
        # For truly centered text in a custom-drawn rounded rect, manual calculation is best.
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)

        # Center the QGraphicsTextItem within the title bar rect
        title_text_rect = self.title_text_item.boundingRect()
        title_text_x = (title_bar_rect.width() - title_text_rect.width()) / 2
        title_text_y = (theme.NODE_TITLE_HEIGHT - title_text_rect.height()) / 2
        self.title_text_item.setPos(title_text_x, title_text_y)

        # Sockets are child QGraphicsItems, Qt handles calling their paint method.
        # We just ensure they are created and positioned correctly.
        # If specific drawing related to sockets needs to happen in NodeItem's paint,
        # for example, lines from socket to node edge, it would go here.
        # For now, socket positioning in __init__ and their own paint methods suffice.

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
