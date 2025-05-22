"""
UI Factory functions for constructing NodeItem, SocketRowItem, and socket widgets from entity nodes and sockets.
This centralizes all UI construction logic for the node editor.
"""

from edon.socket import SocketType
from loguru import logger
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QGraphicsItem

from edon.graph import SocketAddress, SocketRole
from edon_ui import theme
from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketCircleItem, SocketComponent, SocketRowItem
from edon_ui.widgets import (
    SOCKET_WIDGET_COMPONENT_FACTORIES,
    SocketLabel,
    SocketTextAdaptor,
)

if TYPE_CHECKING:
    from edon.node import EntityNode, SocketDef
    from edon.socket import EntitySocket


def create_socket_widget_component(
    entity_socket: "EntitySocket",
    node_id: str,
    parent_gfx_item: QGraphicsItem | None,
    initial_value: Any | None = None,
) -> SocketComponent | None:
    """
    Constructs a socket widget component for a specified entity socket.
    
    This function utilizes the SOCKET_WIDGET_COMPONENT_FACTORIES to retrieve a factory function
    that generates a SocketWidgetAdaptor along with its associated QWidget. It also manages
    the connection of the QWidget's value change signal to the controller for further processing.
    """
    type_info = getattr(entity_socket, "type_info", None)
    socket_name = getattr(entity_socket, "name", "")

    factory_func = SOCKET_WIDGET_COMPONENT_FACTORIES.get(type_info)
    logger.debug(f"Tried to fetch {type_info} factory from {SOCKET_WIDGET_COMPONENT_FACTORIES} registry.")

    if factory_func is not None:
        if initial_value is None:
            initial_value = getattr(entity_socket, "default_value", None)

        component_adaptor, _ = factory_func(
            initial_value=initial_value,
            node_id=node_id,
            socket_name=socket_name,
            parent_gfx_item=parent_gfx_item,
        )

        return component_adaptor
    else:
        print(f"Warning: No widget factory found for data_type {type_info} of socket {socket_name}")
        return None


def create_socket_row(
    entity_socket: "EntitySocket",
    socket_def: "SocketDef",
    node_id: str,
    socket_role: SocketRole,
) -> SocketRowItem:
    """Factory for creating a socket row with the correct composition."""
    linkable: bool = socket_def.linkable
    socket_type: SocketType = socket_def.socket_type.python_type.__name__
    initial_socket_value: Any = entity_socket.value

    label_component = SocketTextAdaptor(
        text_item=SocketLabel(
            text=socket_type,
            target_layout_height=theme.SOCKET_ROW_HEIGHT,
        )
    )
    socket_component = SocketCircleItem(None)
    widget_component: SocketComponent | None = None

    # If not socket role we simply have a label and socket
    if socket_role:
        if socket_role and linkable:  # Input socket, connectable: Label, Circle, Widget (if not connected)
            widget_component = create_socket_widget_component(
                entity_socket, node_id, None, initial_value=initial_socket_value
            )
        else:
            widget_component = create_socket_widget_component(
                entity_socket, node_id, None, initial_value=initial_socket_value
            )

    return SocketRowItem(
        label=label_component,
        socket=socket_component,
        widget=widget_component,
        role=socket_role,
        socket_entity_name=entity_socket.name,
        parent_entity_node_id=node_id,
    )


def _get_socketdef(socket_defs: list[Any], name: str) -> Any:
    for sd in socket_defs:
        if hasattr(sd, "name") and sd.name == name:
            return sd
    return None


def create_node_item(
    entity_node: "EntityNode",
    x: float,
    y: float,
    socket_row_map: dict[SocketAddress, SocketRowItem] | None = None,
) -> NodeItem:
    """
    Create a NodeItem (UI) from an entity node (data model), including all socket rows.
    Optionally registers each SocketRowItem in the provided socket_row_map for fast lookup.
    """
    source_defs = getattr(type(entity_node), "source_socket_definitions", [])
    target_defs = getattr(type(entity_node), "target_socket_definitions", [])

    target_sockets_ui: list[SocketRowItem] = []
    for entity_socket in entity_node.target_sockets.values():
        row = create_socket_row(
            entity_socket,
            _get_socketdef(target_defs, entity_socket.name),
            entity_node.id,
            SocketRole.TARGET,
        )
        # XXX: What is up with the socket_row_map
        if socket_row_map is not None:
            socket_addr = SocketAddress(node_id=entity_node.id, socket_name=entity_socket.name)
            socket_row_map[socket_addr] = row
        target_sockets_ui.append(row)

    source_sockets_ui: list[SocketRowItem] = []
    for entity_socket in entity_node.source_sockets.values():
        row = create_socket_row(
            entity_socket,
            _get_socketdef(source_defs, entity_socket.name),
            entity_node.id,
            SocketRole.SOURCE,
        )
        if socket_row_map is not None:
            socket_addr = SocketAddress(node_id=entity_node.id, socket_name=entity_socket.name)
            socket_row_map[socket_addr] = row
        source_sockets_ui.append(row)

    return NodeItem(
        title=entity_node.name,
        x=x,
        y=y,
        node_entity_id=entity_node.id,
        target_sockets=target_sockets_ui,
        source_sockets=source_sockets_ui,
    )


def create_edge_item(source_socket_circle: "SocketCircleItem", target_socket_circle: "SocketCircleItem") -> EdgeItem:
    """
    Create an EdgeItem connecting two SocketCircleItems.
    """
    edge = EdgeItem(source_socket_circle, target_socket_circle.scenePos())
    edge.set_target_socket(target_socket_circle)
    edge.settle_z_value()
    return edge
