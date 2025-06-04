"""
UI Factory functions for constructing NodeItem, SocketRowItem, and socket widgets from entity nodes and sockets.
This centralizes all UI construction logic for the node editor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from edon.graph import SocketRole
from edon.subgraph.node import SubGraphNode
from edon_ui import theme
from edon_ui.items.node import NodeItem, SubGraphNodeItem
from edon_ui.items.socket import SocketComponent, SocketComponents, SocketItem, SocketLinkItem
from edon_ui.widgets import (
    SOCKET_WIDGET_COMPONENT_FACTORIES,
    SocketLabel,
    SocketTextAdaptor,
)

if TYPE_CHECKING:
    from edon.node import EntityNode
    from edon.socket import EntitySocket
    from edon.types import SocketDef, SocketDisplayState, SocketType


def create_socket_widget_component(
    entity_socket: EntitySocket,
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
    entity_socket: EntitySocket,
    socket_def: SocketDef,
    node_id: str,
    socket_role: SocketRole,
) -> SocketItem:
    """Factory for creating a socket row with the correct composition."""
    logger.debug(f"Creating socket item for {socket_def}::{socket_role}")

    display_state: SocketDisplayState = socket_def.display_state
    socket_type: SocketType = socket_def.socket_type
    initial_socket_value: Any = entity_socket.value

    socket_component = SocketLinkItem(None, visual_type_key=socket_type.description)
    label_component = SocketTextAdaptor(
        text_item=SocketLabel(
            text=socket_type.python_type.__name__,
            target_layout_height=theme.SOCKET_ROW_HEIGHT,
        )
    )
    widget_component = create_socket_widget_component(
        entity_socket, node_id, initial_value=initial_socket_value
    )

    assert socket_component and label_component and widget_component, (
        "CORRUPTION: All components needs to exists."
    )

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


def _get_socketdef(socket_defs: list[SocketDef], name: str) -> SocketDef | None:
    for sd in socket_defs:
        if sd.name == name:
            return sd
    return None


def create_node_item(
    entity_node: EntityNode,
) -> NodeItem:
    logger.debug(f"Creating {entity_node.node_type} node from factory.")

    target_sockets_ui: list[SocketItem] = []
    source_sockets_ui: list[SocketItem] = []
    actual_node_item_class: type[NodeItem]

    if isinstance(entity_node, SubGraphNode):
        actual_node_item_class = SubGraphNodeItem
        # For SubGraphNode, its sockets (proxies) are dynamically created.
        # We need to create SocketDef instances on-the-fly for the UI factory,
        # as SubGraphNode doesn't rely on class-level socket_definitions for its proxy sockets' UI.
        # The EntitySocket instances on SubGraphNode already have type_info and default_value.
        from edon.types import SocketDisplayState, SocketDef

        for entity_socket_instance in entity_node.target_sockets:
            # Create a SocketDef based on the EntitySocket's properties
            temp_socket_def = SocketDef(
                name=entity_socket_instance.name,
                socket_type=entity_socket_instance.type_info,  # entity_socket.type_info is SocketType
                default=entity_socket_instance.default_value,
                display_state=SocketDisplayState.ALL,  # Explicitly set, or rely on SocketDef default
            )
            row = create_socket_item(
                entity_socket_instance, temp_socket_def, entity_node.id, SocketRole.TARGET
            )
            target_sockets_ui.append(row)

        for entity_socket_instance in entity_node.source_sockets:
            temp_socket_def = SocketDef(
                name=entity_socket_instance.name,
                socket_type=entity_socket_instance.type_info,
                default=entity_socket_instance.default_value,
                display_state=SocketDisplayState.ALL,  # Explicitly set
            )
            row = create_socket_item(
                entity_socket_instance, temp_socket_def, entity_node.id, SocketRole.SOURCE
            )
            source_sockets_ui.append(row)
    else:
        actual_node_item_class = NodeItem
        # Existing logic for regular EntityNodes that use class-level socket_definitions
        source_defs = type(entity_node).source_socket_definitions
        target_defs = type(entity_node).target_socket_definitions

        # The original assertion was: `assert source_defs and target_defs`
        # This can be problematic if a node legitimately has no inputs or no outputs.
        # For example, a constant node might only have source_sockets.
        # A print/display node might only have target_sockets.
        # We'll adjust the assertion to be more flexible, checking for None rather than emptiness,
        # as EntityNode.__post_init__ initializes these lists.
        assert source_defs is not None, (
            f"CORRUPTION: {type(entity_node).__name__}.source_socket_definitions is None. "
            "It should be an empty list if no source sockets are defined."
        )
        assert target_defs is not None, (
            f"CORRUPTION: {type(entity_node).__name__}.target_socket_definitions is None. "
            "It should be an empty list if no target sockets are defined."
        )

        for entity_socket in entity_node.target_sockets:
            socket_def = _get_socketdef(target_defs, entity_socket.name)
            assert socket_def is not None, (
                f"CORRUPTION: No `SocketDef` for target entity: {entity_socket}. Available Defs: {target_defs}"
            )
            row = create_socket_item(entity_socket, socket_def, entity_node.id, SocketRole.TARGET)
            target_sockets_ui.append(row)

        for entity_socket in entity_node.source_sockets:
            socket_def = _get_socketdef(source_defs, entity_socket.name)
            assert socket_def is not None, (
                f"CORRUPTION: No `SocketDef` for source entity: {entity_socket}. Available Defs: {source_defs}"
            )
            row = create_socket_item(entity_socket, socket_def, entity_node.id, SocketRole.SOURCE)
            source_sockets_ui.append(row)

    # Instantiate the determined node item class
    ui_node = actual_node_item_class(
        title=entity_node.name,
        node_entity_id=entity_node.id,
        target_sockets=target_sockets_ui,
        source_sockets=source_sockets_ui,
    )
    return ui_node
