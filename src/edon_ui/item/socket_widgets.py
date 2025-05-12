from PySide6.QtCore import QRectF, Qt, Signal, QRegularExpression
from PySide6.QtGui import QIntValidator, QRegularExpressionValidator, QDoubleValidator
from PySide6.QtWidgets import QGraphicsObject, QGraphicsProxyWidget, QHBoxLayout, QLineEdit, QWidget

from edon_ui import theme


class IntegerSocketWidget(QGraphicsObject):
    """
    A QGraphicsObject that embeds a QLineEdit for integer socket UIs.
    It aims to fit within the standard socket row content area.
    """

    valueChanged = Signal(int)  # Emitted when the integer value changes by UI interaction

    def __init__(
        self, initial_value: int = 0, parent_node_entity_id: str = "", socket_entity_name: str = "", parent=None
    ):
        super().__init__(parent)
        self.parent_node_entity_id = parent_node_entity_id
        self.socket_entity_name = socket_entity_name

        self.line_edit = QLineEdit()
        self.line_edit.setText(str(initial_value))
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.line_edit.setValidator(QIntValidator(-2147483648, 2147483647, self.line_edit))
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

    def _on_text_changed(self, text: str):
        """Convert text to integer and emit valueChanged signal if valid"""
        if text:
            try:
                value = int(text)
                self.valueChanged.emit(value)
            except ValueError:
                # Handle invalid input (shouldn't happen with validator)
                pass

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

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
        self, initial_value: float = 0.0, parent_node_entity_id: str = "", socket_entity_name: str = "", parent=None
    ):
        super().__init__(parent)
        self.parent_node_entity_id = parent_node_entity_id
        self.socket_entity_name = socket_entity_name

        self.line_edit = QLineEdit()
        self.line_edit.setText(str(initial_value))
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        validator = QDoubleValidator()
        validator.setNotation(QDoubleValidator.StandardNotation)
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
        self, initial_value: str = "", parent_node_entity_id: str = "", socket_entity_name: str = "", parent=None
    ):
        super().__init__(parent)
        self.parent_node_entity_id = parent_node_entity_id
        self.socket_entity_name = socket_entity_name

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


# Placeholder for SocketRowItem constants to avoid import error if this file is run standalone or for linting
class SocketRowItem:
    CONTENT_ITEM_FIXED_WIDTH = 70.0
    CONTENT_ITEM_VERTICAL_MARGIN = 4.0
