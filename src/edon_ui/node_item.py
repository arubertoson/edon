from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QPainter, QPen, QPainterPath
from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QStyle, QGraphicsObject

from . import theme


class NodeItem(QGraphicsObject):
    """A node in the editor"""

    positionChanged = Signal()

    def __init__(self, title, x, y, width=220, height=150):
        super().__init__()

        self.title = title
        self._width = width
        self._height = height

        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setCacheMode(QGraphicsItem.ItemCoordinateCache)  # Enable caching

        # Title text item - will be positioned in paint or resize
        self.title_text_item = QGraphicsTextItem(self.title, self)
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)
        # Initial position, will be refined. Centering logic can be complex here,
        # often better to draw text directly in paint for perfect alignment with custom title bar.
        title_text_width = self.title_text_item.boundingRect().width()
        self.title_text_item.setPos(
            (self._width - title_text_width) / 2,
            (theme.NODE_TITLE_HEIGHT - self.title_text_item.boundingRect().height()) / 2,
        )

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
        current_border_width = 1.5
        if option.state & QStyle.State_Selected:
            pen = QPen(theme.NODE_BORDER_SELECTED, current_border_width + 0.5)
        else:
            pen = QPen(theme.NODE_BORDER_DEFAULT, current_border_width)
        painter.setPen(pen)
        painter.drawRoundedRect(node_rect, theme.NODE_BORDER_RADIUS, theme.NODE_BORDER_RADIUS)

        # Title Bar area
        # Create a path for the title bar with rounded top corners
        title_bar_rect = QRectF(0, 0, node_rect.width(), theme.NODE_TITLE_HEIGHT)
        title_path = QPainterPath()
        # Add a rounded rect for the title bar portion
        title_path.addRoundedRect(title_bar_rect, theme.NODE_BORDER_RADIUS, theme.NODE_BORDER_RADIUS)
        # Intersect with a rectangle that effectively cuts off the bottom rounding
        # This creates a shape with rounded top-left and top-right, and sharp bottom-left and bottom-right
        # The adjustment by border_width ensures the title background fills neatly inside the border
        clipper_rect = QRectF(
            current_border_width / 2,
            current_border_width / 2,
            node_rect.width() - current_border_width,
            theme.NODE_TITLE_HEIGHT - (current_border_width / 2),
        )
        # Create a path for the clipper (top part of the node without bottom rounding)
        clipper_path = QPainterPath()
        clipper_path.addRect(clipper_rect.adjusted(0, 0, 0, theme.NODE_BORDER_RADIUS))

        # We want the title bar to be the top section of the main rounded rect
        # So, we fill the entire node with NODE_BACKGROUND first (done above).
        # Then, we draw the title bar *background* specifically.
        # The border is already drawn around the whole node.

        painter.setBrush(QBrush(theme.NODE_TITLE_BACKGROUND))
        painter.setPen(Qt.NoPen)

        # A simpler way for title bar background:
        # Just draw a rect, let the main border show through.
        # Clip painting to the rounded shape of the node if NODE_TITLE_BACKGROUND differs significantly
        # from NODE_BACKGROUND, otherwise it might look odd at the rounded corners.
        # Given NODE_TITLE_BACKGROUND is same as NODE_BACKGROUND in current theme, this is fine.
        # If they were different, a more complex path operation would be needed for the fill.

        # For now, assuming title background is same as node or does not need complex clipping:
        # We will draw a path that has rounded top corners and flat bottom for the title area fill

        # Create a path for the title bar background fill
        # Start slightly inside the border to avoid artifacts if colors differ
        fill_title_rect = title_bar_rect.adjusted(
            current_border_width / 2, current_border_width / 2, -current_border_width / 2, 0
        )

        title_fill_path = QPainterPath()
        title_fill_path.moveTo(fill_title_rect.left() + theme.NODE_BORDER_RADIUS, fill_title_rect.top())
        title_fill_path.lineTo(fill_title_rect.right() - theme.NODE_BORDER_RADIUS, fill_title_rect.top())
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.right() - 2 * theme.NODE_BORDER_RADIUS,
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS,
                2 * theme.NODE_BORDER_RADIUS,
            ),
            90,
            -90,
        )
        title_fill_path.lineTo(fill_title_rect.right(), fill_title_rect.bottom())
        title_fill_path.lineTo(fill_title_rect.left(), fill_title_rect.bottom())
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.left(),
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS,
                2 * theme.NODE_BORDER_RADIUS,
            ),
            180,
            -90,
        )
        title_fill_path.closeSubpath()
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
