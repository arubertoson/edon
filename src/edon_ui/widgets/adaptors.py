"""Adaptor classes to make Qt items conform to SocketComponent interface.

This module provides adaptor classes that wrap Qt graphics items to make them conform
to the SocketComponent protocol. These adaptors handle the layout and positioning
requirements of socket components within a node's socket row, while also enabling the use
of standard QWidgets through proxy wrapping for better integration with the QGraphicsView
event system.

These adaptors ensure consistent behavior and layout for different types of socket
components while maintaining the flexibility of the underlying Qt graphics system.
"""

from typing import Any

from loguru import logger
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator, QPainter
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsProxyWidget,
    QLineEdit,
    QStyleOptionGraphicsItem,
    QWidget,
)

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

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Draw nothing; the child label renders the content."""

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        self._text_item.set_text_alignment(alignment)


class SocketWidgetAdaptor(BaseEdonGraphicsObject):
    """Adapts a QWidget to be used as a SocketComponent via QGraphicsProxyWidget."""

    value_committed = Signal(object)

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
        if isinstance(widget, QLineEdit):
            widget.editingFinished.connect(self._emit_committed_value)

    def _emit_committed_value(self) -> None:
        assert isinstance(self._widget, QLineEdit)
        text = self._widget.text()
        validator = self._widget.validator()
        try:
            value: Any
            if isinstance(validator, QIntValidator):
                value = int(text)
            elif isinstance(validator, QDoubleValidator):
                value = float(text)
            else:
                value = text
        except ValueError:
            logger.warning(f"Ignoring invalid socket input value: {text!r}")
            return
        self.value_committed.emit(value)

    def get_required_component_width(self) -> float:
        width = self._widget.width() or self._widget.sizeHint().width()
        return width + (self._horizontal_margin * 2)

    def get_required_component_height(self) -> float:
        return self._widget.height() or self._widget.sizeHint().height()

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Draw nothing; the child proxy widget renders the content."""

    def boundingRect(self) -> QRectF:
        return QRectF(
            0, 0, self.get_required_component_width(), self.get_required_component_height()
        )
