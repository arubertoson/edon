"""Factory functions for creating socket editor components."""

from typing import Protocol, Any

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator

from edon.socket import SocketType
from edon_ui.widgets.adaptors import SocketWidgetAdaptor
from edon_ui.widgets.editors import ExpandLineEdit, FocusSelectLineEdit, ValueTextEdit


class SocketWidgetComponentFactoryProtocol(Protocol):
    def __call__(
        self,
        initial_value: Any,
        node_id: str,
        socket_name: str,
    ) -> SocketWidgetAdaptor: ...


type SocketWidgetComponentFactory = SocketWidgetComponentFactoryProtocol


def create_integer_socket_component(
    initial_value: int,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
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
    line_edit.setText(str(initial_value))

    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


def create_float_socket_component(
    initial_value: float,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
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
    line_edit.setText(str(initial_value))

    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


def create_string_socket_component(
    initial_value: str,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
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

    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


def create_large_string_socket_component(
    initial_value: str,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
    logger.debug(
        f"Creating large string socket component (IconPopupLineEdit) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = ExpandLineEdit(parent=None, widget_factory=ValueTextEdit)
    line_edit.setObjectName(f"text_edit_{node_id}_{socket_name}")
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(initial_value)

    # XXX: Popup logic needs it own way of ending on top.
    # We have weird parenting logic here. Ensure that this is not the end result required.
    # adaptor = SocketWidgetAdaptor(widget=line_edit, parent=controller.graphics_scene.views()[0])
    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


# XXX: This is just shit
def create_any(
    initial_value: str,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
    logger.debug(
        f"Creating large string socket component (IconPopupLineEdit) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)

    adaptor = SocketWidgetAdaptor(line_edit)
    return adaptor


# Registry for socket widget component factories
SOCKET_WIDGET_COMPONENT_FACTORIES: dict[SocketType, SocketWidgetComponentFactory] = {
    SocketType.ANY: create_any,
    SocketType.INTEGER: create_integer_socket_component,
    SocketType.FLOAT: create_float_socket_component,
    SocketType.STRING: create_string_socket_component,
    SocketType.LARGE_STRING: create_large_string_socket_component,
}
