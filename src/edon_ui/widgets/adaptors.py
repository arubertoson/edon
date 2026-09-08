"""Adaptor classes to make Qt items conform to SocketComponent interface.

This module provides adaptor classes that wrap Qt graphics items to make them conform
to the SocketComponent protocol. These adaptors handle the layout and positioning
requirements of socket components within a node's socket row, while also enabling the use
of standard QWidgets through proxy wrapping for better integration with the QGraphicsView
event system.

These adaptors ensure consistent behavior and layout for different types of socket
components while maintaining the flexibility of the underlying Qt graphics system.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsProxyWidget, QWidget

from edon_ui import theme
from edon_ui.base import BaseEdonGraphicsObject
from edon_ui.widgets.editors import ProxyAttributeMixin
from edon_ui.widgets.gfx import SocketLabel


class SocketTextAdaptor(BaseEdonGraphicsObject):
    """Adapts a SocketLabel to be used as a SocketComponent with margins."""

    def __init__(
        self,
        text_item: SocketLabel,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsObject | None = None,
    ):
        super().__init__(parent)
        self._text_item = text_item
        self._horizontal_margin = horizontal_margin

        if self._text_item.parentItem() != self:
            self._text_item.setParentItem(self)
        self._text_item.setPos(self._horizontal_margin, 0)

    def get_required_component_width(self) -> float:
        return self._text_item.boundingRect().width() + (self._horizontal_margin * 2)

    def get_required_component_height(self) -> float:
        return self._text_item.boundingRect().height()

    def boundingRect(self) -> QRectF:
        width = self.get_required_component_width()
        height = self.get_required_component_height()
        return QRectF(0, 0, width, height)

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        self._text_item.set_text_alignment(alignment)


class SocketWidgetAdaptor(BaseEdonGraphicsObject):
    """Adapts a QWidget to be used as a SocketComponent via QGraphicsProxyWidget."""

    def __init__(
        self,
        widget: QWidget,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(None)
        if parent is not None:
            self.setParentItem(parent)

        self._widget = widget
        self._horizontal_margin = horizontal_margin

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(widget)
        self.proxy.setPos(horizontal_margin, 0)
        self.proxy.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        if isinstance(widget, ProxyAttributeMixin):
            widget.proxy = self.proxy

    def get_required_component_width(self) -> float:
        width = self._widget.width() or self._widget.sizeHint().width()
        return width + (self._horizontal_margin * 2)

    def get_required_component_height(self) -> float:
        return self._widget.height() or self._widget.sizeHint().height()

    def boundingRect(self) -> QRectF:
        return QRectF(
            0, 0, self.get_required_component_width(), self.get_required_component_height()
        )
