"""Manages the interaction between the data-centric EntityGraph and the UI GraphicsScene.

This module provides the GraphController class, which is responsible for:
- Populating the graphics scene with nodes and edges based on the entity graph.
- Handling UI requests to add, remove, or modify nodes and edges,
  and translating these into operations on the entity graph.
- Keeping the UI representation synchronized with the state of the entity graph.
- Responding to signals from UI elements for graph-related actions.

TODO:
 - Ensure signatures are not widgets or scene items, they need to be the datatype representations
"""

from collections import defaultdict
from collections.abc import Mapping, MutableMapping, Sequence
from typing import TYPE_CHECKING, Type, TypeAlias

from loguru import logger
from PySide6.QtCore import QPointF

from edon.graph import EdgeKey, EntityGraph, SocketAddress, SocketRole
from edon.node import EntityNode
from edon_ui.items.edge import EdgeItem
from edon_ui.items.factory import create_node_item
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketItem

if TYPE_CHECKING:
    from edon_ui.views.scene import GraphicsScene


NodeItemMap: TypeAlias = MutableMapping[str, NodeItem]
EdgeItemMap: TypeAlias = MutableMapping[EdgeKey, EdgeItem]
SocketItemMap: TypeAlias = MutableMapping[SocketAddress, SocketItem]
SocketEdgeKeyMap: TypeAlias = MutableMapping[SocketAddress, set[EdgeKey]]
NodeRegistryMap: TypeAlias = MutableMapping[str, Type[EntityNode]]


class GraphController:
    """
    Controls the synchronization between the entity graph (edon.graph.EntityGraph)
    and the UI representation (edon_ui.graphics_scene.GraphicsScene).

    It acts as the intermediary, translating UI actions into model operations
    and reflecting model changes in the UI.
    """

    def __init__(
        self,
        entity_graph: EntityGraph,
        ui_scene: "GraphicsScene",
        node_type_registry: Mapping[str, Type[EntityNode]] | None = None,
    ):
        """
        Initializes the GraphController.

        Args:
            entity_graph: The instance of the entity graph (edon.graph.EntityGraph)
                           that this controller will oversee.
            graphics_scene: The QGraphicsScene instance where UI elements will be displayed.
            node_type_registry: Optional dictionary mapping node type hints to node classes.
        """
        self.entity_graph: EntityGraph = entity_graph
        self.ui_scene: "GraphicsScene" = ui_scene

        # Maps for entity graph to UI items
        self.edge_map: EdgeItemMap = {}
        self.node_map: NodeItemMap = {}
        self.node_registry: NodeRegistryMap = node_type_registry or {}
        self.socket_addr_socket_item_map: SocketItemMap = {}
        self.socket_addr_edge_key_map: SocketEdgeKeyMap = defaultdict(set)

        logger.info(
            f"GraphController initialized with entity graph: {self.entity_graph} and graphics scene: {self.ui_scene}"
        )
        logger.debug(f"Node type registry: {self.node_registry}")

    def request_add_node(
        self,
        node_entity_class: type[EntityNode],
        scene_position: QPointF,
        **node_specific_kwargs,
    ) -> NodeItem | None:
        """
        Create a new entity node and its corresponding UI node, registering both with the controller.
        """
        node_type = node_entity_class.__name__
        logger.info(f"request_add_node of type {node_type} at {scene_position}")

        try:
            new_entity_node = node_entity_class(**node_specific_kwargs)
            new_node_item = create_node_item(
                new_entity_node,
                scene_position.x(),
                scene_position.y(),
            )

            # Populate the map using the sockets from the resulting NodeItem
            for socket_row_item in new_node_item.source_sockets + new_node_item.target_sockets:
                self.socket_addr_socket_item_map[socket_row_item.socket_address] = socket_row_item

            logger.info(
                f"Successfully created and added node: {new_entity_node.name} (Entity ID: {new_entity_node.id}, UI: {new_node_item})"
            )

            # Add node to scene and maps AFTER successful creation and mapping
            self.ui_scene.add_node(new_node_item)
            self.node_map[new_entity_node.id] = new_node_item

            return new_node_item
        except Exception as e:
            logger.error(f"Error creating or adding node of type '{node_entity_class.__name__}': {e}")
            return None

    def request_add_edge(self, edge_key: EdgeKey) -> EdgeItem | None:
        """
        Create a new entity edge and its corresponding UI edge, registering both with the controller.
        """
        logger.info(f"GraphController: Requesting to create edge: {edge_key}")
        if edge_key in self.edge_map:
            logger.debug(f"Connection {edge_key} already exists. No new connection created.")
            return None

        source_socket_addr = edge_key.source
        target_socket_addr = edge_key.target
        link_success, reason = self.entity_graph.link_sockets(
            source_socket_addr,
            target_socket_addr,
        )

        if link_success:
            logger.debug(f"Entity connection successful for {edge_key}. Creating UI EdgeItem.")

            source_socket_row = self.socket_addr_socket_item_map.get(source_socket_addr)
            target_socket_row = self.socket_addr_socket_item_map.get(target_socket_addr)

            source_ui_socket_link = source_socket_row.link_item
            target_ui_socket_link = target_socket_row.link_item

            new_edge_item = EdgeItem(source_ui_socket_link, target_ui_socket_link)
            self.ui_scene.add_edge(new_edge_item)

            self.edge_map[edge_key] = new_edge_item
            self.socket_addr_edge_key_map[source_socket_addr].add(edge_key)
            self.socket_addr_edge_key_map[target_socket_addr].add(edge_key)

            logger.debug(f"UI EdgeItem created and added to scene/map for edge: {edge_key}")
            return new_edge_item
        else:
            logger.warning(f"  Entity connection FAILED for {edge_key}. Reason: {reason}. No UI edge created.")

        return None

    def request_remove_node(self, entity_node_id: str) -> bool:
        """
        Handles a request to remove a node (entity and UI) and its connected edges.

        The process involves:
        1. Identifying all edges connected to the node.
        2. Removing each of these edges from both the entity graph and the UI.
        3. Removing the node from the entity graph.
        4. Removing the node's UI representation from the scene.
        5. Cleaning up internal controller mappings.
        """
        logger.info(f"GraphController: Requesting to remove node with ID: {entity_node_id}")

        ui_node_to_remove = self.node_map.get(entity_node_id)
        if not ui_node_to_remove:
            logger.warning(f"Node with ID {entity_node_id} not found in UI map. Cannot remove.")
            return False

        entity_node = self.entity_graph.get_node(entity_node_id)
        if not entity_node:
            logger.warning(
                f"Node with ID {entity_node_id} not found in entity graph. "
                "Proceeding with UI removal if UI node exists."
            )

        # 1. Collect all EdgeKeys connected to this node's UI sockets.
        edge_keys_to_remove: set[EdgeKey] = set()
        for socket_row_item in ui_node_to_remove.source_sockets + ui_node_to_remove.target_sockets:
            socket_addr = socket_row_item.socket_address
            if socket_addr in self.socket_addr_edge_key_map:
                edge_keys_to_remove.update(self.socket_addr_edge_key_map[socket_addr])
        
        logger.debug(f"Found {len(edge_keys_to_remove)} edge(s) connected to node {entity_node_id}: {edge_keys_to_remove}")

        # 2. Remove these edges (entity and UI) by calling request_remove_edge.
        for edge_key in list(edge_keys_to_remove): # Iterate over a copy
            self.request_remove_edge(edge_key)
        logger.debug(f"Successfully processed removal of associated edges for node {entity_node_id}.")

        # 3. Remove node from the entity graph (if it existed).
        if entity_node:
            self.entity_graph.remove_node(entity_node_id)
            logger.debug(f"Node {entity_node_id} removed from entity graph.")

        # 4. Clean up socket_addr_socket_item_map for the removed node's sockets.
        for socket_row_item in ui_node_to_remove.source_sockets + ui_node_to_remove.target_sockets:
            socket_addr = socket_row_item.socket_address
            if socket_addr in self.socket_addr_socket_item_map:
                del self.socket_addr_socket_item_map[socket_addr]
        logger.debug(f"Cleaned up controller's socket item mappings for node {entity_node_id}.")

        # 5. Remove the UI NodeItem from the scene and controller's node_map.
        self.ui_scene.remove_node(ui_node_to_remove)
        if entity_node_id in self.node_map:
            del self.node_map[entity_node_id]
        logger.debug(f"UI NodeItem for {entity_node_id} removed from graphics scene and controller's node_map.")

        logger.info(f"GraphController: Node removal process for {entity_node_id} complete.")
        return True

    def request_remove_edge(self, edge_key: EdgeKey) -> bool:
        """
        Handles a request to remove a single edge (entity and UI).

        Args:
            edge_key: The EdgeKey instance representing the edge to remove.
        """
        logger.info(f"GraphController: Requesting to remove edge: {edge_key}")

        disconnection_success, reason = self.entity_graph.unlink_sockets(edge_key.source, edge_key.target)
        if disconnection_success:
            logger.debug(f"Entity disconnection successful for {edge_key}.")
        else:
            logger.warning(
                f"Entity disconnection FAILED for {edge_key}. Reason: {reason}. Proceeding with UI removal."
            )

        edge_item = self.edge_map.pop(edge_key, None)
        if edge_item:
            self.ui_scene.remove_edge(edge_item)

            self.socket_addr_edge_key_map[edge_key.source].discard(edge_key)
            self.socket_addr_edge_key_map[edge_key.target].discard(edge_key)

            logger.debug(f"UI EdgeItem for {edge_key} removed from graphics scene.")
            return True
        else:
            logger.warning(f"  Could not find edge {edge_key} in edge_map to remove.")
            return False

    def request_edge_drop_targets(self, socket_addr: SocketAddress) -> set[SocketAddress]:
        """
        Return a set of SocketAddress objects that are valid drop targets for the given source_socket_ui_item.
        The source_socket_ui_item is the UI representation of the socket being dragged.
        Only target sockets are considered as potential drop targets here, assuming a standard drag from an output.
        If reverse drag (source to target) is fully supported, this logic might need adjustment for the target iteration.
        """
        valid_targets: set[SocketAddress] = set()

        node_id = socket_addr.node_id
        entity_node = self.entity_graph.get_node(node_id)

        # This should never happen, there should always be a source.
        assert entity_node is not None, f"Source node not found for {node_id}"

        socket_item = self.socket_addr_socket_item_map[socket_addr]
        if socket_item.role == SocketRole.TARGET:  # This implies a reverse drag scenario for the source
            entity_source_socket = entity_node.target_sockets.get(socket_addr.socket_name)
            socket_iter = "source_sockets"
            logger.debug(f"Source socket is reversed: {entity_node.target_sockets}")

        else:  # Standard drag: source_socket_ui_item is an output
            entity_source_socket = entity_node.source_sockets.get(socket_addr.socket_name)
            socket_iter = "target_sockets"
            logger.debug(f"Source socket is normal: {entity_node.source_sockets}")

        # This should never happen, there should always be a source.
        assert entity_source_socket is not None, f"Source socket not found for {socket_item.socket_entity_name}"

        # Iterate over all potential entity target sockets (which must be source for a standard drag)
        for target_node in self.entity_graph.nodes.values():
            for target_socket_name, entity_target_socket in getattr(target_node, socket_iter).items():
                can_link, reason = entity_target_socket.can_link_to(entity_source_socket)
                if can_link:
                    would_cycle = self.entity_graph._has_path(
                        entity_source_socket.node.id, entity_target_socket.node.id
                    )
                    if not would_cycle:
                        valid_targets.add(SocketAddress(target_node.id, target_socket_name))
                else:
                    logger.trace(
                        f"  Entity socket {target_socket_name} cannot connect to {entity_source_socket.name} because {reason}"
                    )

        logger.debug(f"Valid targets: {valid_targets}")
        return valid_targets

    def handle_ui_edge_link_request(self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress):
        """
        Handles a UI request to connect two sockets identified by their SocketAddress.
        Ensures that a target socket has only one incoming edge by removing any
        existing ones. Then, attempts to add the new edge.
        """
        logger.debug(
            f"GraphController: Received handle_ui_edge_connection_attempt from "
            f"source {source_socket_addr} to target {target_socket_addr}"
        )

        edge_key = EdgeKey(source_socket_addr, target_socket_addr)
        if edge_key in self.edge_map:
            logger.warning(f"Edge {edge_key} already exists. Ignoring connection attempt.")
            return

        self.request_add_edge(edge_key)

    def handle_ui_node_creation_request(self, node_type_hint: str, scene_pos: QPointF):
        """
        Slot to handle the new_node_requested_at_scene_pos signal from the UI (e.g., GraphicsView).
        It determines the entity node class to create based on the hint and then
        calls the main request_add_node method.
        """
        logger.info(
            f"GraphController: Received handle_ui_node_creation_request for type '{node_type_hint}' at {scene_pos}"
        )

        node_class_to_create = self.node_registry.get(node_type_hint)

        if not node_class_to_create:
            logger.error(f"ERROR: Node type hint '{node_type_hint}' not found in registry. Cannot create node.")
            return

        # XXX: This might be unnecessary
        # Node names are auto-generated based on type and a running count to ensure uniqueness.
        type_count = sum(1 for node in self.entity_graph.nodes.values() if isinstance(node, node_class_to_create))
        node_name = f"{node_class_to_create.__name__} {type_count + 1}"

        self.request_add_node(
            node_entity_class=node_class_to_create,
            name=node_name,
            scene_position=scene_pos,
        )

    def handle_ui_node_deletion_request(self, entity_node_ids: Sequence[str]):
        logger.info(f"GraphController: Received handle_ui_node_deletion_request for IDs: {entity_node_ids}")
        for node_id in entity_node_ids:
            self.request_remove_node(node_id)

    def handle_ui_edge_deletion_request(self, edge_items: Sequence[EdgeItem]):
        logger.info(f"GraphController: Received handle_ui_edge_deletion_request for {len(edge_items)} edge(s).")
        for edge_item in edge_items:
            self.request_remove_edge(edge_item.edge_key)

    def find_edge_items_at_socket(self, socket_addr: SocketAddress) -> set[EdgeItem]:
        """Retrieves all UI EdgeItems connected to the given socket address."""
        edge_keys = self.socket_addr_edge_key_map.get(socket_addr, set())
        edge_items: set[EdgeItem] = set()
        for key in edge_keys:
            item = self.edge_map.get(key)
            if item:
                edge_items.add(item)
        return edge_items
