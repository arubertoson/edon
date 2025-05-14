from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator, QPen, QColor, QFontMetricsF, QFont, QPainter
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsProxyWidget, QLineEdit, QGraphicsTextItem

from edon_ui import theme


def fit_font_to_height(font: QFont, target_height: float, min_size: int = 1, max_size: int = 30) -> QFont:
    """Finds the largest font size that fits within target_height."""
    test_font = QFont(font)
    for size in range(max_size, min_size - 1, -1):
        test_font.setPointSize(size)
        metrics = QFontMetricsF(test_font)
        print(f"size: {size}, height: {metrics.height()}")
        if metrics.height() <= target_height:
            return test_font
    test_font.setPointSize(min_size)
    return test_font


def _font_height_diff(font: QFont, target_height: float) -> float:
    metrics = QFontMetricsF(font)
    return target_height - metrics.height()


class SocketLabel(QGraphicsTextItem):
    def __init__(self, text: str, width: int, parent=None):
        super().__init__(text, parent)

        font = self.font()
        font.setPointSize(10)

        # Ensure the font fits within the socket row height
        # We first check if the current font size would fit in our target height
        # If not, we'll find the largest font size that does fit
        # This ensures consistent text display across different socket types
        diff = _font_height_diff(font, theme.SOCKET_ROW_HEIGHT)
        if diff < 0:
            font = fit_font_to_height(font, theme.SOCKET_ROW_HEIGHT)
            diff = _font_height_diff(font, theme.SOCKET_ROW_HEIGHT)

        self.setFont(font)
        self.document().setDocumentMargin(diff / 2 if diff > 0 else 0)
        self.setDefaultTextColor(theme.INPUT_TEXT_COLOR)

        self.setTextWidth(width)

    def effective_height(self, padding: float = 0) -> float:
        return self.boundingRect().height() + padding

    def set_alignment(self, alignment: Qt.AlignmentFlag):
        doc = self.document()
        option = doc.defaultTextOption()
        option.setAlignment(alignment)
        doc.setDefaultTextOption(option)

    # def paint(self, painter, option, widget=None):
    #     super().paint(painter, option, widget)
    #     # Draw bounding rect outline
    #     pen = QPen(QColor("red"))
    #     pen.setWidth(1)
    #     painter.setPen(pen)
    #     painter.setBrush(Qt.NoBrush)
    #     painter.drawRect(self.boundingRect())


class IntegerSocketWidget(QGraphicsObject):
    """
    A QGraphicsObject that embeds a QLineEdit for integer socket UIs.
    It aims to fit within the standard socket row content area.
    """

    valueChanged = Signal(int)  # Emitted when the integer value changes by UI interaction

    def __init__(
        self,
        initial_value: int = 0,
        parent_node_entity_id: str = "",
        socket_entity_name: str = "",
        type_label: str = "Integer",
        parent=None,
    ):
        super().__init__(parent)

        self.type_label = type_label or "Integer"
        self.parent_node_entity_id = parent_node_entity_id
        self.socket_entity_name = socket_entity_name

        self.line_edit = QLineEdit()
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
        self.line_edit.setValidator(QIntValidator(-2147483648, 2147483647, self.line_edit))
        self.line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.line_edit.setText(str(initial_value))

        fixed_height = int(theme.SOCKET_ROW_HEIGHT)
        fixed_width = int(theme.NODE_MIN_WIDTH)

        self.line_edit.setFixedHeight(fixed_height)
        self.line_edit.setFixedWidth(fixed_width)

        # self.line_edit.setStyleSheet(f"""
        #     QLineEdit {{
        #         border: 1px solid {theme.INPUT_BORDER_COLOR.name()};
        #         border-radius: {theme.INPUT_BORDER_RADIUS}px;
        #         background-color: {theme.INPUT_BACKGROUND_COLOR.name()};
        #         color: {theme.INPUT_TEXT_COLOR.name()};
        #         padding: 2px 4px;
        #     }}
        # """)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.line_edit)

        self.line_edit.textChanged.connect(self._on_text_changed)

        self._width = fixed_width
        self._height = fixed_height

    def _on_text_changed(self, text: str):
        """Convert text to integer and emit valueChanged signal if valid"""
        if text:
            try:
                value = int(text)
                self.valueChanged.emit(value)
            except ValueError:
                pass

    def boundingRect(self) -> QRectF:
        return QRectF(
            0,
            0,
            self._width,
            self._height,
        )

    def get_value(self) -> int:
        """Get the current integer value or 0 if empty/invalid"""
        try:
            return int(self.line_edit.text()) if self.line_edit.text() else 0
        except ValueError:
            return 0

    def set_value(self, value: int):
        """Sets the value without emitting the valueChanged signal"""
        # Block signals to prevent re-emitting valueChanged
        self.line_edit.blockSignals(True)
        self.line_edit.setText(str(value))
        self.line_edit.blockSignals(False)


class FloatSocketWidget(QGraphicsObject):
    """
    A QGraphicsObject that embeds a QLineEdit for float socket UIs.
    It aims to fit within the standard socket row content area.
    """

    valueChanged = Signal(float)  # Emitted when the float value changes by UI interaction

    def __init__(
        self,
        initial_value: float = 0.0,
        parent_node_entity_id: str = "",
        socket_entity_name: str = "",
        type_label: str = "Float",
        parent=None,
    ):
        super().__init__(parent)
        self.parent_node_entity_id = parent_node_entity_id
        self.socket_entity_name = socket_entity_name
        self.type_label = type_label or "Float"

        self.line_edit = QLineEdit()
        self.line_edit.setText(str(initial_value))
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        self.line_edit.setValidator(validator)

        fixed_height = int(theme.SOCKET_ROW_HEIGHT - 4.0 * 2)
        fixed_width = int(70.0)
        self.line_edit.setFixedHeight(fixed_height)
        self.line_edit.setFixedWidth(fixed_width)

        self.line_edit.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {theme.INPUT_BORDER_COLOR.name()};
                border-radius: {theme.INPUT_BORDER_RADIUS}px;
                background-color: {theme.INPUT_BACKGROUND_COLOR.name()};
                color: {theme.INPUT_TEXT_COLOR.name()};
                padding: 2px 4px;
            }}
        """)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.line_edit)

        self.line_edit.textChanged.connect(self._on_text_changed)

        self._width = fixed_width
        self._height = fixed_height
        self._layout()

    def _layout(self):
        self.proxy.setPos(0, 0)

    def _on_text_changed(self, text: str):
        """Convert text to float and emit valueChanged signal if valid"""
        if text:
            try:
                value = float(text)
                self.valueChanged.emit(value)
            except ValueError:
                # Handle invalid input (shouldn't happen with validator)
                pass

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def get_value(self) -> float:
        """Get the current float value or 0.0 if empty/invalid"""
        try:
            return float(self.line_edit.text()) if self.line_edit.text() else 0.0
        except ValueError:
            return 0.0

    def set_value(self, value: float):
        """Sets the value without emitting the valueChanged signal"""
        # Block signals to prevent re-emitting valueChanged
        self.line_edit.blockSignals(True)
        self.line_edit.setText(str(value))
        self.line_edit.blockSignals(False)


class StringSocketWidget(QGraphicsObject):
    """
    A QGraphicsObject that embeds a QLineEdit for string socket UIs.
    It aims to fit within the standard socket row content area.
    """

    valueChanged = Signal(str)  # Emitted when the string value changes by UI interaction

    def __init__(
        self,
        initial_value: str = "",
        parent_node_entity_id: str = "",
        socket_entity_name: str = "",
        type_label: str = "String",
        parent=None,
    ):
        super().__init__(parent)
        self.parent_node_entity_id = parent_node_entity_id
        self.socket_entity_name = socket_entity_name
        self.type_label = type_label or "String"

        # self.label_item = QGraphicsTextItem(self.type_label, self)
        # self.label_item.setDefaultTextColor(theme.INPUT_TEXT_COLOR)
        # font = self.label_item.font()
        # font.setPointSize(10)
        # self.label_item.setFont(font)

        self.line_edit = QLineEdit()
        self.line_edit.setText(initial_value)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        fixed_height = int(theme.SOCKET_ROW_HEIGHT - 4.0 * 2)
        fixed_width = int(70.0)
        self.line_edit.setFixedHeight(fixed_height)
        self.line_edit.setFixedWidth(fixed_width)

        self.line_edit.setStyleSheet(f"""
            QLineEdit {{
                border: 1px solid {theme.INPUT_BORDER_COLOR.name()};
                border-radius: {theme.INPUT_BORDER_RADIUS}px;
                background-color: {theme.INPUT_BACKGROUND_COLOR.name()};
                color: {theme.INPUT_TEXT_COLOR.name()};
                padding: 2px 4px;
            }}
        """)

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self.line_edit)

        self.line_edit.textChanged.connect(self._on_text_changed)

        self._width = fixed_width
        self._height = fixed_height
        self._layout()

    def _layout(self):
        self.proxy.setPos(0, 0)

    def _on_text_changed(self, text: str):
        """Emit valueChanged signal with the current text"""
        self.valueChanged.emit(text)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def get_value(self) -> str:
        """Get the current string value or empty string if none"""
        return self.line_edit.text() or ""

    def set_value(self, value: str):
        """Sets the value without emitting the valueChanged signal"""
        # Block signals to prevent re-emitting valueChanged
        self.line_edit.blockSignals(True)
        self.line_edit.setText(value)
        self.line_edit.blockSignals(False)


SOCKET_WIDGET_REGISTRY: dict[type, type[QGraphicsItem]] = {}
SOCKET_WIDGET_REGISTRY[int] = IntegerSocketWidget
SOCKET_WIDGET_REGISTRY[float] = FloatSocketWidget
SOCKET_WIDGET_REGISTRY[str] = StringSocketWidget
