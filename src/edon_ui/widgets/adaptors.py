"""Adaptor classes to make Qt items conform to SocketComponent interface.

This module provides adaptor classes that wrap Qt graphics items to make them conform
to the SocketComponent protocol. These adaptors handle the layout and positioning
requirements of socket components within a node's socket row, while also enabling the use
of standard QWidgets through proxy wrapping for better integration with the QGraphicsView
event system.

These adaptors ensure consistent behavior and layout for different types of socket
components while maintaining the flexibility of the underlying Qt graphics system.
"""

from loguru import logger
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsProxyWidget,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from edon_ui import theme
from edon_ui.widgets.gfx import SocketLabel


class PaintEventMixin:
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None) -> None:
        """Overrides the pure virtual paint method from QGraphicsObject.

        This method must be implemented, even if it does nothing, to prevent
        a pure virtual function call error at runtime when Qt attempts to paint
        this QGraphicsObject. In this adaptor, painting is handled by the
        child QGraphicsTextItem, so this method intentionally does nothing.
        """
        pass


class SocketTextAdaptor(QGraphicsObject):
    """
    Adapts a QGraphicsTextItem (like SocketLabel) to be used as a SocketComponent.
    It manages the overall footprint including horizontal margins, and positions the text item within.
    """

    def __init__(
        self,
        text_item: SocketLabel,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsObject | None = None,
    ):
        super().__init__(parent)
        logger.trace(f"SocketTextAdaptor created for text_item: {text_item}")

        self._text_item = text_item
        self._horizontal_margin = horizontal_margin

        self._view = parent

        if self._text_item.parentItem() != self:  # Ensure correct parenting
            self._text_item.setParentItem(self)

        self._text_item.setTextWidth(self.get_required_component_width())
        self._text_item.setPos(self._horizontal_margin, 0)

    def get_required_component_width(self) -> float:
        return self._text_item.boundingRect().width() + (self._horizontal_margin * 2)

    def get_required_component_height(self) -> float:
        return self._text_item.boundingRect().height()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.get_required_component_width(), self.get_required_component_height())

    def text_item(self) -> QGraphicsTextItem:
        return self._text_item

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        if hasattr(self._text_item, "set_alignment"):
            # This assumes SocketLabel (or similar) has a 'set_alignment' method
            self._text_item.set_text_alignment(alignment)


class SocketWidgetAdaptor(QGraphicsObject):
    """
    Adapts a QWidget (e.g., QLineEdit) to be used as a SocketComponent.
    It wraps the QWidget in a QGraphicsProxyWidget and handles size, position, and internal
    horizontal margins.
    """

    def __init__(
        self,
        widget: QWidget,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(None)
        logger.trace(f"SocketWidgetAdaptor.__init__ for widget: {widget}, parent: {parent}")

        self._widget = widget
        self._horizontal_margin = horizontal_margin

        self._view = parent

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self._widget)
        self.proxy.setPos(self._horizontal_margin, 0)
        self.proxy.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._widget.proxy = self.proxy
        self._widget.setParent(parent)

    def get_required_component_width(self) -> float:
        # Use the actual width of the widget, or its size hint if not yet shown
        width = self._widget.width()
        if width == 0:
            width = self._widget.sizeHint().width()

        return width + (self._horizontal_margin * 2)

    def get_required_component_height(self) -> float:
        height = self._widget.height()
        if height == 0:
            height = self._widget.sizeHint().height()
        return height

    def boundingRect(self) -> QRectF:
        width = self.get_required_component_width()
        height = self.get_required_component_height()
        return QRectF(0, 0, width, height)

    def widget(self) -> QWidget:
        return self._widget
