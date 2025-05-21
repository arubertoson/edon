"""Factory functions for creating socket editor components."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import QGraphicsItem, QLineEdit

from edon.socket import SocketType
from edon_ui.items.socket_components.adaptors import SocketWidgetAdaptor
from edon_ui.items.socket_components.editors import ExpandLineEdit, FocusSelectLineEdit, ValueTextEdit

if TYPE_CHECKING:
    from edon_ui.graph_controller import GraphController

# Type alias for socket widget component factory functions
SocketWidgetComponentFactory = Callable[
    [Any, "GraphController | None", str, str, QGraphicsItem | None], tuple[SocketWidgetAdaptor, QLineEdit]
]


def create_integer_socket_component(
    initial_value: int | None = 0,
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[SocketWidgetAdaptor, QLineEdit]:
    """
    Creates a QLineEdit configured for integer input and wraps it in a SocketWidgetAdaptor.
    """
    logger.debug(
        f"Creating integer socket component for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)  # Parent will be set by SocketWidgetAdaptor via proxy
    line_edit.setObjectName(f"le_int_{node_id}_{socket_name}")
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    line_edit.setValidator(QIntValidator(-2147483648, 2147483647, line_edit))
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else 0))

    if controller and node_id and socket_name:
        # Connection logic for controller (e.g., on editingFinished or textChanged)
        # This is handled by the GraphController when it uses these factories.
        pass
    adaptor = SocketWidgetAdaptor(widget=line_edit, parent=parent_gfx_item)
    return adaptor, line_edit


def create_float_socket_component(
    initial_value: float | None = 0.0,
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[SocketWidgetAdaptor, QLineEdit]:
    """
    Creates a QLineEdit configured for float input and wraps it in a SocketWidgetAdaptor.
    """
    logger.debug(
        f"Creating float socket component for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)
    line_edit.setObjectName(f"le_float_{node_id}_{socket_name}")
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    validator = QDoubleValidator(line_edit)
    validator.setNotation(QDoubleValidator.Notation.StandardNotation)
    line_edit.setValidator(validator)
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else 0.0))

    if controller and node_id and socket_name:
        pass  # Connection logic handled by GraphController

    adaptor = SocketWidgetAdaptor(widget=line_edit, parent=parent_gfx_item)
    return adaptor, line_edit


def create_string_socket_component(
    initial_value: str | None = "",
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[SocketWidgetAdaptor, QLineEdit]:
    logger.debug(
        f"Creating string socket component (QLineEdit) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)
    line_edit.setObjectName(f"le_str_{node_id}_{socket_name}")
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else ""))

    # FontMetrics calculation for logging purposes, can be removed if not essential here
    fm = line_edit.fontMetrics()
    text_width_pixels = fm.horizontalAdvance(line_edit.text())
    logger.debug(
        f"  String QLineEdit '{line_edit.objectName()}': text='{line_edit.text()}', calculated fontMetrics text_width_pixels={text_width_pixels}"
    )

    if controller and node_id and socket_name:
        pass  # Connection logic handled by GraphController

    adaptor = SocketWidgetAdaptor(widget=line_edit, parent=parent_gfx_item)
    return adaptor, line_edit


def create_large_string_socket_component(
    initial_value: str | None = "",
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[SocketWidgetAdaptor, QLineEdit]:  # QLineEdit is the base for IconPopupLineEdit
    logger.debug(
        f"Creating large string socket component (IconPopupLineEdit) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = ExpandLineEdit(parent=None, widget_factory=type[ValueTextEdit])
    line_edit.setObjectName(f"text_edit_{node_id}_{socket_name}")
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else ""))

    # Connection logic for controller (if any) is handled by GraphController or direct access
    if controller and node_id and socket_name:
        pass

    adaptor = SocketWidgetAdaptor(widget=line_edit, parent=controller.graphics_scene.views()[0])
    return adaptor, line_edit


# Registry for socket widget component factories
SOCKET_WIDGET_COMPONENT_FACTORIES: dict[SocketType, SocketWidgetComponentFactory] = {
    SocketType.INTEGER: create_integer_socket_component,
    SocketType.FLOAT: create_float_socket_component,
    SocketType.STRING: create_string_socket_component,
    SocketType.LARGE_STRING: create_large_string_socket_component,
}
