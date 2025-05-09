from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QStyleOptionGraphicsItem,
    QWidget,
)

from .node_item import NodeItem
from . import theme # Import the theme module


class EmptySceneTextItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)

        # Define text and styles for each line
        self.line1_text = "There's nothing here!"
        self.line1_font_family = "Arial"
        self.line1_font_size_px = 18
        self.line1_color = QColor("#b4b4b4")
        self.line1_italic = False

        self.line2_text = "(ctrl+space to start adding nodes)"
        self.line2_font_family = "Arial"
        self.line2_font_size_px = 14
        self.line2_color = QColor("#909090")
        self.line2_italic = True

        self.line_spacing_px = 4  # Additional spacing between lines in pixels

        # Prepare fonts (can also be done in paint, but here is fine too)
        self._font1 = QFont(self.line1_font_family)
        self._font1.setPixelSize(self.line1_font_size_px)  # Use pixelSize for consistency
        self._font1.setItalic(self.line1_italic)

        self._font2 = QFont(self.line2_font_family)
        self._font2.setPixelSize(self.line2_font_size_px)
        self._font2.setItalic(self.line2_italic)

        # Cache bounding rect calculation
        self._cached_bounding_rect = self._calculate_bounding_rect()

    def _get_line_metrics(self, text, font):
        fm = QFontMetricsF(font)
        # boundingRect(text) gives a tight rect around the text.
        # Alternatively, height() gives ascent+descent, width(text) gives advance width.
        return fm.boundingRect(text)  # QRectF

    def _calculate_bounding_rect(self) -> QRectF:
        rect1 = self._get_line_metrics(self.line1_text, self._font1)
        rect2 = self._get_line_metrics(self.line2_text, self._font2)

        max_width = max(rect1.width(), rect2.width())
        total_height = rect1.height() + self.line_spacing_px + rect2.height()

        # We want the item's origin (0,0) to be its visual center for easy scene placement
        return QRectF(-max_width / 2, -total_height / 2, max_width, total_height)

    def boundingRect(self) -> QRectF:
        return self._cached_bounding_rect

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None) -> None:
        painter.setRenderHint(QPainter.TextAntialiasing)

        overall_br = self.boundingRect()  # This is already centered around (0,0)

        # --- Draw Line 1 ---
        painter.setFont(self._font1)
        painter.setPen(self.line1_color)

        # Calculate rect for line 1, centered horizontally within overall_br
        # and positioned at the top part of overall_br
        line1_metrics_rect = self._get_line_metrics(self.line1_text, self._font1)

        # Top-left y for line1 text block, relative to item's (0,0) origin
        y1_pos = overall_br.top()

        # Create a drawing rectangle for line1 that spans the full width of the item
        # Qt.AlignCenter will then center the text within this drawing_rect1.
        drawing_rect1 = QRectF(overall_br.left(), y1_pos, overall_br.width(), line1_metrics_rect.height())
        painter.drawText(drawing_rect1, Qt.AlignCenter, self.line1_text)

        # --- Draw Line 2 ---
        painter.setFont(self._font2)
        painter.setPen(self.line2_color)

        line2_metrics_rect = self._get_line_metrics(self.line2_text, self._font2)

        # Top-left y for line2 text block, relative to item's (0,0) origin
        # Positioned after line1 and spacing
        y2_pos = y1_pos + line1_metrics_rect.height() + self.line_spacing_px

        drawing_rect2 = QRectF(overall_br.left(), y2_pos, overall_br.width(), line2_metrics_rect.height())
        painter.drawText(drawing_rect2, Qt.AlignCenter, self.line2_text)


class GraphicsScene(QGraphicsScene):
    """A custom QGraphicsScene subclass designed for a node-based editor interface.

    This scene manages the visual workspace where nodes can be placed and manipulated.
    It provides:
    - A defined active area with visual boundaries
    - Dynamic scene resizing based on node positions
    - Empty state handling with helper text
    - Node tracking and management
    - Visual grid lines for alignment
    - Custom background and styling

    The scene automatically adjusts its boundaries as nodes are added, moved, or
    removed to maintain an appropriate workspace size. It also provides visual
    feedback when empty to guide users on how to begin using the editor.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.active_area_size = 2000  # Initial size, can be smaller if preferred
        self.setSceneRect(
            -self.active_area_size / 2, -self.active_area_size / 2, self.active_area_size, self.active_area_size
        )
        self.setBackgroundBrush(QBrush(theme.SCENE_BACKGROUND)) # Use theme color

        # Active area - initialized without specific rect, will be set by _update_scene_appearance
        self.active_area = QGraphicsRectItem()
        self.active_area.setBrush(QBrush(theme.SCENE_ACTIVE_AREA_BACKGROUND)) # Use theme color
        self.active_area.setPen(QPen(theme.SCENE_ACTIVE_AREA_BORDER, 1)) # Use theme color, border width 1
        self.active_area.setZValue(-100)  # Ensure it's behind all other items

        self.empty_scene_text = EmptySceneTextItem()

        self.node_items = []

        self._update_scene_appearance()

    def addItem(self, item):
        """Override to track node items, connect signals, and then add to the scene."""
        if isinstance(item, NodeItem) and item not in self.node_items:
            self.node_items.append(item)

            try:
                item.positionChanged.connect(self._update_scene_appearance)
            except AttributeError as e:  # Should not happen with QObject inheritance
                print(f"Warning: Could not connect positionChanged signal for item {item}. Error: {e}")
            except RuntimeError as e:
                print(f"ERROR during connect for item {item}: {e}")

            super().addItem(item)
            self._update_scene_appearance()

        elif item == self.active_area and self.active_area not in self.items():
            if self.node_items:  # Only add active_area if there are nodes
                super().addItem(self.active_area)
        elif item == self.empty_scene_text and self.empty_scene_text not in self.items():
            if not self.node_items:  # Only add empty_scene_text if there are no nodes
                super().addItem(self.empty_scene_text)
        else:
            # If it's not a NodeItem we are explicitly tracking or one of our special items,
            # or if it's a NodeItem being re-added (though 'item not in self.node_items' should prevent this path for existing nodes),
            # ensure it still gets added to the scene.
            if item.scene() != self:  # Avoid re-adding if already in this scene by some other means
                super().addItem(item)

    def removeItem(self, item):
        if isinstance(item, NodeItem) and item in self.node_items:
            try:
                item.positionChanged.disconnect(self._update_scene_appearance)
            except (AttributeError, RuntimeError):  # RuntimeError if connection doesn't exist or source deleted
                pass  # Often safe to ignore disconnection errors

            self.node_items.remove(item)
            super().removeItem(item)
            self._update_scene_appearance()
        else:
            super().removeItem(item)

    def add_new_node_at(self, scene_pos: QPointF):
        """Creates a new NodeItem at the given scene position and adds it to the scene."""
        node_title = f"Node {len(self.node_items) + 1}"
        new_node = NodeItem(title=node_title, x=scene_pos.x(), y=scene_pos.y())
        self.addItem(new_node)

    def _update_scene_appearance(self):
        if not self.node_items:
            if self.active_area.scene() == self:
                super().removeItem(self.active_area)
            if self.empty_scene_text.scene() != self:
                super().addItem(self.empty_scene_text)
            self.empty_scene_text.setVisible(True)
        else:
            if self.empty_scene_text.scene() == self:
                self.empty_scene_text.setVisible(False)
            if self.active_area.scene() != self:
                super().addItem(self.active_area)
            self._calculate_active_area_rect()

    def _calculate_active_area_rect(self):
        """Calculate the active area rectangle based on the current node positions"""
        if not self.node_items:  # Should not be called if no nodes, but as a safeguard
            # Default small rect if called erroneously, though _update_scene_appearance handles this path.
            # self.active_area.setRect(0,0,0,0) # Effectively hide it or set minimal
            return

        padding = 100
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        for node in self.node_items:
            pos = node.pos()
            rect = node.boundingRect()
            min_x = min(min_x, pos.x())
            min_y = min(min_y, pos.y())
            max_x = max(max_x, pos.x() + rect.width())
            max_y = max(max_y, pos.y() + rect.height())

        min_x -= padding
        min_y -= padding
        max_x += padding
        max_y += padding

        width = max(max_x - min_x, 400)
        height = max(max_y - min_y, 400)
        self.active_area.setRect(min_x, min_y, width, height)

    def adjust_scene_rect_for_view(self, visible_scene_rect: QRectF):
        """
        Adjusts the sceneRect to ensure it encompasses the given visible_scene_rect
        from a view, plus some padding.
        """
        current_s_rect = self.sceneRect()

        # Define padding in scene units. This ensures the sceneRect grows a bit beyond
        # what's immediately visible, giving some buffer for panning.
        padding = min(visible_scene_rect.width(), visible_scene_rect.height()) * 0.5  # 50% of smallest view dimension
        # Clamp padding to a reasonable min/max if necessary, e.g. max(500, min(padding, 5000))
        padding = max(200.0, padding)  # Ensure a minimum padding

        # Create a new rect based on the view's visible area plus padding
        # QRectF.adjusted returns a new QRectF
        padded_visible_rect = visible_scene_rect.adjusted(-padding, -padding, padding, padding)

        # Unite the current sceneRect with the padded visible rect to ensure the scene boundaries
        # encompass both the existing scene area and the newly visible area.
        # This prevents the scene from shrinking when panning/zooming and maintains context.
        # QRectF.united returns a new QRectF containing both input rectangles.
        new_scene_rect = current_s_rect.united(padded_visible_rect)

        if new_scene_rect != current_s_rect:
            self.setSceneRect(new_scene_rect)
