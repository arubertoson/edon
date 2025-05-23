"""Initializes the socket_components sub-package.

This package provides various UI components used in the rendering and interaction
of node sockets, including graphical items, adaptors for Qt widgets, specialized
editor widgets, and factories to create these components.
"""

from edon_ui.widgets.gfx import SocketLabel, fit_font_to_height
from edon_ui.widgets.adaptors import SocketTextAdaptor, SocketWidgetAdaptor
from edon_ui.widgets.editors import FocusSelectLineEdit, ExpandLineEdit
from edon_ui.widgets.factories import (
    SOCKET_WIDGET_COMPONENT_FACTORIES,
    SocketWidgetComponentFactory,
    create_integer_socket_component,
    create_float_socket_component,
    create_string_socket_component,
    create_large_string_socket_component,
)

__all__ = [
    "SocketLabel",
    "fit_font_to_height",
    "SocketTextAdaptor",
    "SocketWidgetAdaptor",
    "FocusSelectLineEdit",
    "ExpandLineEdit",
    "SOCKET_WIDGET_COMPONENT_FACTORIES",
    "SocketWidgetComponentFactory",
    "create_integer_socket_component",
    "create_float_socket_component",
    "create_string_socket_component",
    "create_large_string_socket_component",
]
