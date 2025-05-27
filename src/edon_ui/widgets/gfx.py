"""Graphical primitives for socket UI rendering."""

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFont,
    QFontMetricsF,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
)

from edon_ui import theme


def fit_font_to_height(font: QFont, target_height: float, min_size: int = 1, max_size: int = 30) -> QFont:
    """Finds the largest font size that fits within target_height."""
    test_font = QFont(font)
    for size in range(max_size, min_size - 1, -1):
        test_font.setPointSize(size)
        metrics = QFontMetricsF(test_font)
        if metrics.height() <= target_height:
            return test_font
    test_font.setPointSize(min_size)
    return test_font


def _font_height_diff(font: QFont, target_height: float) -> float:
    metrics = QFontMetricsF(font)
    return target_height - metrics.height()


class SocketLabel(QGraphicsTextItem):
    def __init__(self, text: str, target_layout_height: float, parent: QGraphicsItem | None = None):
        super().__init__(text, parent)
        logger.trace(f"SocketLabel created with text: '{text}'")

        font = self.font()
        font.setPointSize(getattr(theme, "FONT_SOCKET_LABEL_DEFAULT_SIZE", 10))

        diff = _font_height_diff(font, target_layout_height)
        if diff < 0:
            font = fit_font_to_height(font, target_layout_height)
            diff = _font_height_diff(font, target_layout_height)

        self.setFont(font)
        self.document().setDocumentMargin(diff / 2 if diff > 0 else 0)
        self.setDefaultTextColor(getattr(theme, "SOCKET_LABEL_TEXT_COLOR", theme.INPUT_TEXT_COLOR))

    def get_required_component_width(self) -> float:
        """Returns the width as determined by setTextWidth or natural text width."""
        return self.boundingRect().width()

    def get_required_component_height(self) -> float:
        """Returns the actual bounding height of the text item, including document margins."""
        return self.boundingRect().height()

    def set_text_alignment(self, alignment: Qt.AlignmentFlag):
        doc = self.document()
        option = doc.defaultTextOption()
        option.setAlignment(alignment)
        doc.setDefaultTextOption(option)
