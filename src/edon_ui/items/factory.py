"""
UI Factory functions for constructing NodeItem, SocketRowItem, and socket widgets from entity nodes and sockets.
This centralizes all UI construction logic for the node editor.
"""

from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QGraphicsItem, QGraphicsTextItem

from edon_ui import theme
from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketCircleItem, SocketRowItem
from edon_ui.items.socket_widgets import SOCKET_WIDGET_REGISTRY
from edon_ui.items.socket_widgets import SocketLabel

if TYPE_CHECKING:
    from edon.node import EntityNode, SocketDef
    from edon.socket import EntitySocket


def create_socket_widget(
    entity_socket: "EntitySocket", node_id: str, parent: QGraphicsItem | None, initial_value: Any | None = None
) -> QGraphicsItem:
    """
    Create the appropriate socket widget for the given entity socket.
    """
    data_type = getattr(entity_socket, "data_type", None)
    socket_name = getattr(entity_socket, "name", "")

    widget_cls = SOCKET_WIDGET_REGISTRY.get(data_type)
    if widget_cls is not None:
        return widget_cls(
            initial_value=initial_value if initial_value is not None else getattr(widget_cls, "default", None),
            parent_node_entity_id=node_id,
            socket_entity_name=socket_name,
            parent=parent,
        )
    else:
        # Fallback: just show the socket name as a label
        return QGraphicsTextItem(socket_name, parent)


def create_socket_row(
    entity_socket: "EntitySocket",
    socket_def: "SocketDef",
    node_id: str,
    is_input: bool,
) -> SocketRowItem:
    """Factory for creating a socket row with the correct composition.

    Args:
        entity_socket: The socket entity.
        socket_def: The socket definition.
        node_id: The node's unique identifier.
        is_input: Whether this is an input socket.

    Returns:
        A composable SocketRowItem.
    """
    accepts_connection: bool = getattr(socket_def, "accepts_connection", True)
    type_label: str = socket_def.type.__name__ if hasattr(socket_def, "type") else "Value"
    width: int = int(theme.NODE_MIN_WIDTH)
    label: QGraphicsItem | None = None
    circle: QGraphicsItem | None = None
    widget: QGraphicsItem | None = None

    if not is_input:
        # Output: always label + circle
        label = SocketLabel(type_label, width)
        circle = SocketCircleItem(None, entity_socket.name, node_id)

    elif is_input and accepts_connection:
        # Input: label + circle + widget
        label = SocketLabel(type_label, width)
        circle = SocketCircleItem(None, entity_socket.name, node_id)
        widget = create_socket_widget(entity_socket, node_id, None)

    else:
        # Not connectable: just the widget
        widget = create_socket_widget(entity_socket, node_id, None)

    return SocketRowItem(
        label=label,
        circle=circle,
        widget=widget,
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
) -> NodeItem:
    """
    Create a NodeItem (UI) from an entity node (data model), including all socket rows.
    Optionally registers each SocketRowItem in the provided socket_row_map for fast lookup.
    """
    # In the new declarative node architecture, each node type defines its input and output sockets
    # as class-level attributes: `input_socket_definitions` and `output_socket_definitions`.
    # These are typically lists of SocketDef dataclasses, describing the sockets' names, types, defaults, etc.
    #
    # Previously, the code called a method `_resolve_socket_defs`, but this was removed in favor of
    # direct, declarative class attributes. We now use `getattr(type(entity_node), ...)` to access
    # these definitions from the node's class, ensuring we always get the correct socket definitions
    # for any node type, regardless of the instance. This approach is robust, future-proof, and
    # matches the new extensible design, where all socket metadata is declared at the class level.
    input_defs = getattr(type(entity_node), "input_socket_definitions", [])
    output_defs = getattr(type(entity_node), "output_socket_definitions", [])

    input_sockets: list[SocketRowItem] = []
    for entity_socket in entity_node.input_sockets.values():
        row = create_socket_row(entity_socket, _get_socketdef(input_defs, entity_socket.name), entity_node.id, True)
        if socket_row_map is not None:
            socket_row_map[(entity_node.id, entity_socket.name, True)] = row
        input_sockets.append(row)

    output_sockets: list[SocketRowItem] = []
    for entity_socket in entity_node.output_sockets.values():
        row = create_socket_row(entity_socket, _get_socketdef(output_defs, entity_socket.name), entity_node.id, False)
        if socket_row_map is not None:
            socket_row_map[(entity_node.id, entity_socket.name, False)] = row
        output_sockets.append(row)

    return NodeItem(
        title=entity_node.name,
        x=x,
        y=y,
        node_entity_id=entity_node.id,
        input_sockets=input_sockets,
        output_sockets=output_sockets,
    )


def create_edge_item(source_socket_circle: "SocketCircleItem", target_socket_circle: "SocketCircleItem") -> EdgeItem:
    """
    Create an EdgeItem connecting two SocketCircleItems.
    """
    edge = EdgeItem(source_socket_circle, target_socket_circle.scenePos())
    edge.set_target_socket(target_socket_circle)
    edge.settle_z_value()
    return edge
