"""
UI Factory functions for constructing NodeItem, SocketRowItem, and socket widgets from entity nodes and sockets.
This centralizes all UI construction logic for the node editor.
"""

from typing import TYPE_CHECKING, Any

from loguru import logger
from PySide6.QtWidgets import QGraphicsItem

from edon.graph import SocketRole
from edon_ui import theme
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketComponent, SocketItem, SocketLinkItem, SocketComponents
from edon_ui.widgets import (
    SOCKET_WIDGET_COMPONENT_FACTORIES,
    SocketLabel,
    SocketTextAdaptor,
)

if TYPE_CHECKING:
    from edon.node import EntityNode, SocketDef, SocketDisplayState
    from edon.socket import EntitySocket, SocketType


def create_socket_widget_component(
    entity_socket: "EntitySocket",
    node_id: str,
    initial_value: Any | None = None,
) -> SocketComponent:
    """
    Constructs a socket widget component for a specified entity socket.

    This function utilizes the SOCKET_WIDGET_COMPONENT_FACTORIES to retrieve a factory function
    that generates a SocketWidgetAdaptor along with its associated QWidget.
    """
    logger.debug(f"Creating socket widget item for {entity_socket}")

    type_info = entity_socket.type_info
    socket_name = entity_socket.name

    factory_func = SOCKET_WIDGET_COMPONENT_FACTORIES.get(type_info)
    assert factory_func is not None, (
        f"CORRUPTION: `factory_func` needs to exists in {SOCKET_WIDGET_COMPONENT_FACTORIES}"
    )

    return factory_func(
        initial_value=initial_value,
        node_id=node_id,
        socket_name=socket_name,
    )


def create_socket_item(
    entity_socket: "EntitySocket",
    socket_def: "SocketDef",
    node_id: str,
    socket_role: SocketRole,
) -> SocketItem:
    """Factory for creating a socket row with the correct composition."""
    logger.debug(f"Creating socket item for {socket_def}::{socket_role}")

    display_state: "SocketDisplayState" = socket_def.display_state
    socket_type: "SocketType" = socket_def.socket_type
    initial_socket_value: Any = entity_socket.value

    socket_component = SocketLinkItem(None, visual_type_key=socket_type.description)
    label_component = SocketTextAdaptor(
        text_item=SocketLabel(
            text=socket_type.python_type.__name__,
            target_layout_height=theme.SOCKET_ROW_HEIGHT,
        )
    )
    widget_component = create_socket_widget_component(entity_socket, node_id, initial_value=initial_socket_value)

    assert socket_component and label_component and widget_component, "CORRUPTION: All components needs to exists."

    return SocketItem(
        role=socket_role,
        entity_name=entity_socket.name,
        node_entity_id=node_id,
        components=SocketComponents(
            link=socket_component,
            label=label_component,
            widget=widget_component,
            display_state=display_state,
        ),
    )


def _get_socketdef(socket_defs: list["SocketDef"], name: str) -> "SocketDef | None":
    for sd in socket_defs:
        if sd.name == name:
            return sd
    return None


def create_node_item(
    entity_node: "EntityNode",
    x: float,
    y: float,
) -> NodeItem:
    logger.debug(f"Creating {entity_node.node_type} node from factory.")

    source_defs = type(entity_node).source_socket_definitions
    target_defs = type(entity_node).target_socket_definitions

    assert source_defs and target_defs, "CORRUPTION: EntityNode.*_socket_definitions are None."

    target_sockets_ui: list[SocketItem] = []
    for entity_socket in entity_node.target_sockets.values():
        socket_def = _get_socketdef(target_defs, entity_socket.name)
        assert socket_def is not None, (
            f"CORRUPTION: No `SocketDef` for target entity: {entity_socket}. Available Defs: {target_defs}"
        )

        row = create_socket_item(
            entity_socket,
            socket_def,
            entity_node.id,
            SocketRole.TARGET,
        )
        target_sockets_ui.append(row)

    source_sockets_ui: list[SocketItem] = []
    for entity_socket in entity_node.source_sockets.values():
        socket_def = _get_socketdef(source_defs, entity_socket.name)
        assert socket_def is not None, (
            f"CORRUPTION: No `SocketDef` for source entity: {entity_socket}. Available Defs: {source_defs}"
        )

        row = create_socket_item(
            entity_socket,
            socket_def,
            entity_node.id,
            SocketRole.SOURCE,
        )
        source_sockets_ui.append(row)

    return NodeItem(
        title=entity_node.name,
        x=x,
        y=y,
        node_entity_id=entity_node.id,
        target_sockets=target_sockets_ui,
        source_sockets=source_sockets_ui,
    )
