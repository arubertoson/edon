"""
UI Factory functions for constructing NodeItem, SocketRowItem, and socket widgets from entity nodes and sockets.
This centralizes all UI construction logic for the node editor.
"""

from typing import TYPE_CHECKING, Any, Callable

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem, QLineEdit
from PySide6.QtCore import QObject

from edon_ui import theme
from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketCircleItem, SocketRowItem, SocketComponent
from edon_ui.items.socket_widgets import (
    SOCKET_WIDGET_COMPONENT_FACTORIES,
    SocketWidgetAdaptor,
    SocketLabel,
    SocketTextAdaptor,
)

if TYPE_CHECKING:
    from edon.node import EntityNode, SocketDef
    from edon.socket import EntitySocket
    from edon_ui.graph_controller import GraphController


def create_socket_widget_component(
    entity_socket: "EntitySocket",
    node_id: str,
    parent_gfx_item: QGraphicsItem | None,
    initial_value: Any | None = None,
    controller: "GraphController | None" = None,
) -> SocketComponent | None:
    """
    Creates the appropriate socket widget component for the given entity socket.
    Uses the SOCKET_WIDGET_COMPONENT_FACTORIES to get a factory function,
    which returns a SocketWidgetAdaptor and the underlying QWidget.
    Handles connecting the QWidget's value changed signal to the controller.
    """
    data_type = getattr(entity_socket, "data_type", None)
    socket_name = getattr(entity_socket, "name", "")

    factory_func = SOCKET_WIDGET_COMPONENT_FACTORIES.get(data_type)

    if factory_func is not None:
        if initial_value is None:
            initial_value = getattr(entity_socket, "default_value", None)

        component_adaptor, _ = factory_func(
            initial_value=initial_value,
            controller=controller,
            node_id=node_id,
            socket_name=socket_name,
            parent_gfx_item=parent_gfx_item,
        )

        return component_adaptor
    else:
        print(f"Warning: No widget factory found for data_type {data_type} of socket {socket_name}")
        return None


def create_socket_row(
    entity_socket: "EntitySocket",
    socket_def: "SocketDef",
    node_id: str,
    is_input: bool,
    controller: "GraphController | None" = None,
) -> SocketRowItem:
    """Factory for creating a socket row with the correct composition.

    Args:
        entity_socket: The socket entity.
        socket_def: The socket definition.
        node_id: The node's unique identifier.
        is_input: Whether this is an input socket.
        controller: The graph controller, for connecting widget signals.

    Returns:
        A composable SocketRowItem.
    """
    accepts_connection: bool = getattr(socket_def, "accepts_connection", True)
    type_label_text: str = socket_def.type.__name__ if hasattr(socket_def, "type") else "Value"

    label_component: SocketComponent | None = None
    circle_component: SocketComponent | None = None
    widget_component: SocketComponent | None = None
    initial_socket_value: Any = socket_def.default

    if not is_input:  # Output socket: Label and Circle
        socket_label = SocketLabel(text=type_label_text, target_layout_height=theme.SOCKET_ROW_HEIGHT)
        label_component = SocketTextAdaptor(
            text_item=socket_label,
        )
        circle_component = SocketCircleItem(None, entity_socket.name, node_id)

    elif is_input and accepts_connection:  # Input socket, connectable: Label, Circle, Widget (if not connected)
        socket_label = SocketLabel(text=type_label_text, target_layout_height=theme.SOCKET_ROW_HEIGHT)
        label_component = SocketTextAdaptor(
            text_item=socket_label,
        )
        circle_component = SocketCircleItem(None, entity_socket.name, node_id)
        widget_component = create_socket_widget_component(
            entity_socket, node_id, None, initial_value=initial_socket_value, controller=controller
        )

    else:
        widget_component = create_socket_widget_component(
            entity_socket, node_id, None, initial_value=initial_socket_value, controller=controller
        )

    return SocketRowItem(
        label=label_component,
        circle=circle_component,
        widget=widget_component,
        is_input=is_input,
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
    socket_row_map: dict[tuple[str, str, bool], SocketRowItem] | None = None,
    controller: "GraphController | None" = None,
) -> NodeItem:
    """
    Create a NodeItem (UI) from an entity node (data model), including all socket rows.
    Optionally registers each SocketRowItem in the provided socket_row_map for fast lookup.
    """
    input_defs = getattr(type(entity_node), "input_socket_definitions", [])
    output_defs = getattr(type(entity_node), "output_socket_definitions", [])

    input_sockets_ui: list[SocketRowItem] = []
    for entity_socket in entity_node.input_sockets.values():
        row = create_socket_row(
            entity_socket, _get_socketdef(input_defs, entity_socket.name), entity_node.id, True, controller=controller
        )
        if socket_row_map is not None:
            socket_row_map[(entity_node.id, entity_socket.name, True)] = row
        input_sockets_ui.append(row)

    output_sockets_ui: list[SocketRowItem] = []
    for entity_socket in entity_node.output_sockets.values():
        row = create_socket_row(
            entity_socket,
            _get_socketdef(output_defs, entity_socket.name),
            entity_node.id,
            False,
            controller=controller,
        )
        if socket_row_map is not None:
            socket_row_map[(entity_node.id, entity_socket.name, False)] = row
        output_sockets_ui.append(row)

    return NodeItem(
        title=entity_node.name,
        x=x,
        y=y,
        node_entity_id=entity_node.id,
        input_sockets=input_sockets_ui,
        output_sockets=output_sockets_ui,
    )


def create_edge_item(source_socket_circle: "SocketCircleItem", target_socket_circle: "SocketCircleItem") -> EdgeItem:
    """
    Create an EdgeItem connecting two SocketCircleItems.
    """
    edge = EdgeItem(source_socket_circle, target_socket_circle.scenePos())
    edge.set_target_socket(target_socket_circle)
    edge.settle_z_value()
    return edge
