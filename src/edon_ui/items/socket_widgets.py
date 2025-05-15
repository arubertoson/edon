from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QDoubleValidator, QFont, QFontMetricsF, QIntValidator, QColor
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsProxyWidget,
    QGraphicsTextItem,
    QLineEdit,
    QWidget,
)

from edon_ui import theme

if TYPE_CHECKING:
    from edon_ui.graph_controller import GraphController
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QStyleOptionGraphicsItem


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
    def __init__(self, text: str, target_layout_height: float, parent=None):
        super().__init__(text, parent)

        font = self.font()
        # Assuming a theme constant like theme.FONT_SOCKET_LABEL_DEFAULT_SIZE exists or will be added
        font.setPointSize(getattr(theme, "FONT_SOCKET_LABEL_DEFAULT_SIZE", 10))

        # Ensure the font fits within the socket row height by dynamically adjusting its size.
        # We first check if the current font would overflow our target height.
        # If it would overflow, we find the largest font size that fits properly.
        # This approach ensures consistent text display and proper vertical alignment
        # across different socket types regardless of their content.
        diff = _font_height_diff(font, target_layout_height)
        if diff < 0:
            font = fit_font_to_height(font, target_layout_height)
            diff = _font_height_diff(font, target_layout_height)

        self.setFont(font)
        self.document().setDocumentMargin(diff / 2 if diff > 0 else 0)
        # Assuming a theme constant like theme.SOCKET_LABEL_TEXT_COLOR exists or INPUT_TEXT_COLOR is fine
        self.setDefaultTextColor(getattr(theme, "SOCKET_LABEL_TEXT_COLOR", theme.INPUT_TEXT_COLOR))

    def get_required_component_width(self) -> float:
        """Returns the width as determined by setTextWidth or natural text width."""
        return self.boundingRect().width()

    def get_required_component_height(self) -> float:
        """Returns the actual bounding height of the text item, including document margins."""
        return self.boundingRect().height()

    def set_alignment(self, alignment: Qt.AlignmentFlag):
        doc = self.document()
        option = doc.defaultTextOption()
        option.setAlignment(alignment)
        doc.setDefaultTextOption(option)


class SocketTextAdaptor(QGraphicsObject):
    """
    Adapts a QGraphicsTextItem (like SocketLabel) to be used as a SocketComponent.
    It manages the overall footprint including horizontal margins, and positions the text item within.
    """

    def __init__(
        self,
        text_item: QGraphicsTextItem,
        fixed_width: float = theme.NODE_MIN_WIDTH,
        fixed_height: float = theme.SOCKET_ROW_HEIGHT,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(parent)
        self._text_item = text_item
        self._fixed_width = fixed_width
        self._fixed_height = fixed_height
        self._horizontal_margin = horizontal_margin

        if self._text_item.parentItem() != self:  # Ensure correct parenting
            self._text_item.setParentItem(self)

        # Calculate the actual content width for the QGraphicsTextItem
        content_width = self._fixed_width - (2 * self._horizontal_margin)
        self._fixed_width = max(0, content_width)

        self._text_item.setTextWidth(content_width)

        # Position the text item with a horizontal offset for the margin.
        # Vertical position is 0 as text_item should fill fixed_height via its internal mechanisms.
        self._text_item.setPos(self._horizontal_margin, 0)

    # --- SocketComponent required methods ---
    def get_required_component_width(self) -> float:
        return self._fixed_width

    def get_required_component_height(self) -> float:
        return self._fixed_height

    # --- QGraphicsItem methods ---
    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._fixed_width, self._fixed_height)

    def paint(self, painter: "QPainter", option: "QStyleOptionGraphicsItem", widget: "QWidget | None" = None) -> None:
        # This QGraphicsObject is a container and does not paint anything itself.
        # Its child (SocketLabel) handles its own painting.
        # Providing an empty paint method prevents NotImplementedError if Qt tries to paint it,
        # especially due to parent caching (e.g., NodeItem).
        pass

    # --- Convenience methods to access underlying text item if needed ---
    def text_item(self) -> QGraphicsTextItem:
        return self._text_item

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        """Sets the text alignment of the underlying QGraphicsTextItem if it supports it."""
        if hasattr(self._text_item, "set_alignment"):
            self._text_item.set_alignment(alignment)
        else:
            # Fallback or warning if the text_item doesn't have set_alignment
            # This shouldn't happen if it's always a SocketLabel instance
            print(f"Warning: Text item {type(self._text_item)} does not have set_alignment method.")


class SocketWidgetAdaptor(QGraphicsObject):
    """
    Adapts a QWidget (e.g., QLineEdit) to be used as a SocketComponent.
    It wraps the QWidget in a QGraphicsProxyWidget and handles size, position, and internal horizontal margins.
    The fixed_width and fixed_height define the total space for the adaptor.
    The actual QWidget is placed inside this space, inset horizontally by the specified margin.
    Vertical alignment is handled by the QWidget itself within its allocated fixed_height.
    """

    def __init__(
        self,
        widget: QWidget,
        fixed_width: float = theme.NODE_MIN_WIDTH,
        fixed_height: float = theme.SOCKET_ROW_HEIGHT,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(parent)
        self._widget = widget
        self._fixed_width = fixed_width
        self._fixed_height = fixed_height
        self._horizontal_margin = horizontal_margin

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(self._widget)

        # Calculate the actual dimensions for the QWidget
        widget_width = self._fixed_width - (2 * self._horizontal_margin)
        widget_height = self._fixed_height  # Widget takes the full provided height

        # Ensure widget dimensions are not negative
        widget_width = max(0, widget_width)
        # widget_height is already handled by fixed_height, should not be < 0 if fixed_height is sensible

        # Position the proxy widget (which contains the QWidget) with a horizontal offset for the margin.
        # Vertical position is 0 as widget_height is the full fixed_height.
        self.proxy.setPos(self._horizontal_margin, 0)

        # Ensure the underlying QWidget has the calculated fixed size
        self._widget.setFixedWidth(int(widget_width))
        self._widget.setFixedHeight(int(widget_height))

    # --- SocketComponent required methods ---
    def get_required_component_width(self) -> float:
        return self._fixed_width

    def get_required_component_height(self) -> float:
        return self._fixed_height

    # --- QGraphicsItem methods ---
    # QGraphicsObject provides implementations for many of these (setPos, pos, show, hide, etc.)
    # We only need to override what's necessary, like boundingRect.

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._fixed_width, self._fixed_height)

    def paint(self, painter: "QPainter", option: "QStyleOptionGraphicsItem", widget: QWidget | None = None) -> None:
        # is not strictly needed for SocketWidgetAdaptor itself if it's just a container.
        # The QGraphicsProxyWidget handles painting its QWidget.
        # If you wanted to draw a border or background for the adaptor itself, you would override paint.
        # Example: Draw a debug border for the adaptor itself
        # super().paint(painter, option, widget)
        # pen = QPen(QColor("blue"))
        # painter.setPen(pen)
        # painter.drawRect(self.boundingRect())
        pass

    # --- Convenience methods to access underlying widget if needed ---
    def widget(self) -> QWidget:
        return self._widget


# Type alias for socket widget component factory functions
SocketWidgetComponentFactory = Callable[
    [Any, "GraphController | None", str, str, QGraphicsItem | None], tuple[SocketWidgetAdaptor, QWidget]
]

# Registry for socket widget component factories
SOCKET_WIDGET_COMPONENT_FACTORIES: dict[type, SocketWidgetComponentFactory] = {}


def create_integer_socket_component(
    initial_value: Any = 0,
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[SocketWidgetAdaptor, QLineEdit]:
    """
    Creates a QLineEdit configured for integer input and wraps it in a SocketWidgetAdaptor.

    Args:
        initial_value: The initial integer value for the QLineEdit.
        controller: The graph controller instance for updating the backend.
        node_id: The ID of the parent node entity.
        socket_name: The name of the socket entity.
        parent_gfx_item: The parent QGraphicsItem for the SocketWidgetAdaptor.

    Returns:
        A tuple containing the configured SocketWidgetAdaptor and the QLineEdit instance.
    """
    line_edit = QLineEdit()
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    # Consider if QIntValidator needs a parent if line_edit isn't parented yet by proxy
    line_edit.setValidator(QIntValidator(-2147483648, 2147483647, line_edit))
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else 0))

    if controller and node_id and socket_name:
        # Connection logic for controller (e.g., on editingFinished or textChanged)
        # This is currently commented out as per previous discussions, assuming controller handles updates elsewhere or via direct widget access.
        pass
    adaptor = SocketWidgetAdaptor(widget=line_edit, parent=parent_gfx_item)
    return adaptor, line_edit


def create_float_socket_component(
    initial_value: Any = 0.0,
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[SocketWidgetAdaptor, QLineEdit]:
    """
    Creates a QLineEdit configured for float input and wraps it in a SocketWidgetAdaptor.

    Args:
        initial_value: The initial float value for the QLineEdit.
        controller: The graph controller instance for updating the backend.
        node_id: The ID of the parent node entity.
        socket_name: The name of the socket entity.
        parent_gfx_item: The parent QGraphicsItem for the SocketWidgetAdaptor.

    Returns:
        A tuple containing the configured SocketWidgetAdaptor and the QLineEdit instance.
    """
    line_edit = QLineEdit()
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    validator = QDoubleValidator(line_edit)
    validator.setNotation(QDoubleValidator.Notation.StandardNotation)
    line_edit.setValidator(validator)
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else 0.0))

    if controller and node_id and socket_name:
        pass  # Connection logic (if any) is handled by controller or direct access

    adaptor = SocketWidgetAdaptor(widget=line_edit, parent=parent_gfx_item)
    return adaptor, line_edit


def create_string_socket_component(
    initial_value: Any = "",
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[SocketWidgetAdaptor, QLineEdit]:
    """
    Creates a QLineEdit configured for string input and wraps it in a SocketWidgetAdaptor.

    Args:
        initial_value: The initial string value for the QLineEdit.
        controller: The graph controller instance for updating the backend.
        node_id: The ID of the parent node entity.
        socket_name: The name of the socket entity.
        parent_gfx_item: The parent QGraphicsItem for the SocketWidgetAdaptor.

    Returns:
        A tuple containing the configured SocketWidgetAdaptor and the QLineEdit instance.
    """
    line_edit = QLineEdit()
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)  # Or AlignLeft
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else ""))

    if controller and node_id and socket_name:
        pass  # Connection logic (if any) is handled by controller or direct access

    adaptor = SocketWidgetAdaptor(widget=line_edit, parent=parent_gfx_item)
    return adaptor, line_edit


# Now, register all factories
SOCKET_WIDGET_COMPONENT_FACTORIES[int] = create_integer_socket_component
SOCKET_WIDGET_COMPONENT_FACTORIES[float] = create_float_socket_component
SOCKET_WIDGET_COMPONENT_FACTORIES[str] = create_string_socket_component


# Clean up any old registry if it existed and is no longer needed
# For example, if there was an old SOCKET_WIDGET_REGISTRY
# del SOCKET_WIDGET_REGISTRY # Or comment out its definition if found elsewhere
