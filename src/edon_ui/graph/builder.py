"""
Provides a function to build a scene representation (NodeItems and EdgeItems)
from an EntityGraph without direct interaction with QGraphicsScene or GraphController.
Also defines the data structure for this representation.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from loguru import logger

from edon.graph import EdgeKey, EntityGraph, NodeId, SocketAddress
from edon_ui import theme
from edon_ui.items.factory import create_edge_item, create_node_item

if TYPE_CHECKING:
    from edon_ui.items.edge import EdgeItem
    from edon_ui.items.node import NodeItem


@dataclass
class SceneItems:
    """
    A container for UI items constructed from an EntityGraph,
    not yet integrated into a live QGraphicsScene or GraphController.
    """

    nodes: dict[NodeId, "NodeItem"] = field(default_factory=dict)
    edges: dict[EdgeKey, "EdgeItem"] = field(default_factory=dict)


def create_scene_items_from_graph(
    entity_graph: EntityGraph,
) -> SceneItems:
    """
    Creates NodeItem and EdgeItem instances based on the provided EntityGraph.

    Args:
        entity_graph: The data graph to represent visually.

    Returns:
        A BuiltSceneRepresentation containing the constructed UI items.
    """
    logger.debug(f"SceneBuilder: Starting to build representation for graph with {len(entity_graph.nodes)} nodes.")
    built_nodes: dict[NodeId, "NodeItem"] = {}
    built_edges: dict[EdgeKey, "EdgeItem"] = {}

    default_x, default_y = 50.0, 50.0
    spacing_x = theme.NODE_MIN_WIDTH + 50.0
    spacing_y = theme.NODE_MIN_HEIGHT + 50.0
    nodes_per_row = 5

    for i, (node_id, entity_node) in enumerate(entity_graph.nodes.items()):
        pos_x = default_x + (i % nodes_per_row) * spacing_x
        pos_y = default_y + (i // nodes_per_row) * spacing_y
        ui_node = create_node_item(entity_node, pos_x, pos_y)
        built_nodes[node_id] = ui_node
    logger.debug(f"SceneBuilder: Built {len(built_nodes)} NodeItems.")

    processed_edge_keys: set[EdgeKey] = set()
    for source_node_id, source_entity_node in entity_graph.nodes.items():
        source_ui_node = built_nodes.get(source_node_id)
        if not source_ui_node:
            logger.warning(
                f"SceneBuilder: Source UI node {source_node_id} not found while building edges. Entity node: {source_entity_node.name}"
            )
            continue

        for source_socket_name, source_entity_socket in source_entity_node.source_sockets.items():
            for linked_target_entity_socket in source_entity_socket.links:
                target_node_id = linked_target_entity_socket.node.id
                target_socket_name = linked_target_entity_socket.name

                edge_key = EdgeKey(
                    source=SocketAddress(node_id=source_node_id, socket_name=source_socket_name),
                    target=SocketAddress(node_id=target_node_id, socket_name=target_socket_name),
                )

                if edge_key in processed_edge_keys:
                    continue
                processed_edge_keys.add(edge_key)

                target_ui_node = built_nodes.get(target_node_id)
                if not target_ui_node:
                    logger.warning(
                        f"SceneBuilder: Target UI node {target_node_id} not found for edge {edge_key}. Entity node: {linked_target_entity_socket.node.name}"
                    )
                    continue

                source_socket_circle = source_ui_node.get_socket_circle_item_by_name(
                    source_socket_name, is_target=False
                )
                target_socket_circle = target_ui_node.get_socket_circle_item_by_name(
                    target_socket_name, is_target=True
                )

                if not source_socket_circle:
                    logger.warning(
                        f"SceneBuilder: Source socket UI for {edge_key.source} (on node {source_ui_node.entity_node.name if source_ui_node.entity_node else 'N/A'}) not found."
                    )
                    continue
                if not target_socket_circle:
                    logger.warning(
                        f"SceneBuilder: Target socket UI for {edge_key.target} (on node {target_ui_node.entity_node.name if target_ui_node.entity_node else 'N/A'}) not found."
                    )
                    continue

                ui_edge = create_edge_item(source_socket_circle, target_socket_circle)
                built_edges[edge_key] = ui_edge
    logger.debug(f"SceneBuilder: Built {len(built_edges)} EdgeItems.")

    return BuiltSceneRepresentation(nodes=built_nodes, edges=built_edges)
