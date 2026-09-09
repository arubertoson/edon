"""Transient presentation of values and errors beside a graph node."""

from collections.abc import Sequence

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QPainter, QPen
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget

from edon_ui import theme


class NodeInspectorItem(QGraphicsObject):
    """A non-authoritative, node-anchored rendering of execution information."""

    WIDTH = 190.0
    TITLE_HEIGHT = 25.0
    ROW_HEIGHT = 20.0
    PADDING = 8.0

    def __init__(
        self,
        title: str,
        rows: Sequence[tuple[str, str]],
        *,
        error: bool = False,
        parent: QGraphicsObject,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._rows = tuple(rows)
        self._error = error
        self.setZValue(10)
        self.setPos(parent.boundingRect().right() + 10.0, 0.0)

    def boundingRect(self) -> QRectF:
        row_count = max(1, len(self._rows))
        height = self.TITLE_HEIGHT + self.PADDING * 2 + row_count * self.ROW_HEIGHT
        return QRectF(0.0, 0.0, self.WIDTH, height)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        del option, widget
        rect = self.boundingRect()
        border_color = theme.ACCENT_ERROR if self._error else theme.NODE_BORDER_SELECTED
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(QBrush(theme.NODE_BACKGROUND))
        painter.drawRoundedRect(rect, theme.NODE_BORDER_RADIUS, theme.NODE_BORDER_RADIUS)

        painter.fillRect(
            QRectF(0.0, 0.0, rect.width(), self.TITLE_HEIGHT), theme.NODE_TITLE_BACKGROUND
        )
        painter.setFont(theme.FONT_NODE_TITLE)
        painter.setPen(theme.NODE_TITLE_TEXT)
        painter.drawText(
            QRectF(self.PADDING, 0.0, rect.width() - self.PADDING * 2, self.TITLE_HEIGHT),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._title,
        )

        painter.setFont(theme.FONT_NODE_LABEL)
        painter.setPen(theme.NODE_LABEL_TEXT)
        rows = self._rows or (("", "No values"),)
        for index, (name, value) in enumerate(rows):
            row_rect = QRectF(
                self.PADDING,
                self.TITLE_HEIGHT + self.PADDING + index * self.ROW_HEIGHT,
                rect.width() - self.PADDING * 2,
                self.ROW_HEIGHT,
            )
            text = f"{name}: {value}" if name else value
            elided = painter.fontMetrics().elidedText(
                text, Qt.TextElideMode.ElideRight, int(row_rect.width())
            )
            painter.drawText(row_rect, Qt.AlignmentFlag.AlignVCenter, elided)
