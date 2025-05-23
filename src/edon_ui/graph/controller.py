"""Manages the interaction between the data-centric EntityGraph and the UI GraphicsScene.

This module provides the GraphController class, which is responsible for:
- Populating the graphics scene with nodes and edges based on the entity graph.
- Handling UI requests to add, remove, or modify nodes and edges,
  and translating these into operations on the entity graph.
- Keeping the UI representation synchronized with the state of the entity graph.
- Responding to signals from UI elements for graph-related actions.

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
    from edon.socket import EntitySocket


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
        self.socket_addr_socket_item_map: SocketItemMap = {}
        self.socket_addr_edge_key_map: SocketEdgeKeyMap = defaultdict(set)

        self.node_registry: NodeRegistryMap = node_type_registry or {}

        logger.info(
            f"GraphController initialized with entity graph: {self.entity_graph} and graphics scene: {self.ui_scene}"
        )

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
            for socket_item in new_node_item.source_sockets + new_node_item.target_sockets:
                self.socket_addr_socket_item_map[socket_item.socket_address] = socket_item

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
        Handles a request to remove a node and its connected edges from both the
        entity graph and the UI scene.

        The removal process first identifies the UI node and the corresponding entity node.
        It then collects all edges connected to this node's UI sockets. Each of these
        edges is removed by invoking `request_remove_edge`, which handles both the
        entity graph and UI cleanup for the edge. After all associated edges are
        removed, the node itself is removed from the entity graph. Subsequently,
        the controller's internal mapping for the node's sockets is cleared.
        Finally, the node's UI representation is removed from the graphics scene,
        and the node is removed from the controller's main node map.
        """
        logger.info(f"GraphController: Requesting to remove node with ID: {entity_node_id}")

        node_item_to_remove = self.node_map.get(entity_node_id)

        # Collect all EdgeKeys for edges connected to the UI sockets of the node being removed.
        # This information is retrieved from the controller's mapping of socket addresses to edge keys.
        for socket_item in node_item_to_remove.source_sockets + node_item_to_remove.target_sockets:
            for edge_key in self.socket_addr_edge_key_map.get(socket_item.socket_address):
                self.request_remove_edge(edge_key)

            logger.debug(f"Removing `SocketAddress` {socket_item.socket_address} mapping")
            # Clean up the controller's mapping from socket addresses to socket UI items
            # for all sockets belonging to the removed node.
            del self.socket_addr_socket_item_map[socket_item.socket_address]

        # Remove the node from the controller's primary mapping of entity IDs to UI node items.
        del self.node_map[entity_node_id]
        self.entity_graph.remove_node(entity_node_id)
        self.ui_scene.remove_node(node_item_to_remove)

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

    def find_valid_socket_drop_targets(self, drag_origin_socket_addr: SocketAddress) -> set[SocketAddress]:
        """
        Determines valid drop target sockets for an edge drag operation using EntityGraph validation.

        Args:
            drag_origin_socket_addr: The SocketAddress of the socket where the drag started.

        Returns:
            A set of SocketAddress objects representing sockets that are valid drop targets.
        """
        valid_targets: set[SocketAddress] = set()

        drag_origin_entity_node = self.entity_graph.get_node(drag_origin_socket_addr.node_id)
        # This assertion remains important as the starting point must be valid.
        assert drag_origin_entity_node is not None, f"Node for dragged socket {drag_origin_socket_addr} not found."

        drag_origin_ui_socket_item = self.socket_addr_socket_item_map.get(drag_origin_socket_addr)

        # Determine which collection of sockets to iterate on partner nodes
        # and how to define prospective source/target for the new edge.
        if drag_origin_ui_socket_item.role == SocketRole.TARGET:  # Dragging from an TARGET socket (reverse drag)
            partner_sockets_collection_name = "source_sockets"
            logger.debug(f"Drag originated from TARGET socket: {drag_origin_socket_addr}. Looking for SOURCE sockets.")
        else:
            partner_sockets_collection_name = "target_sockets"
            logger.debug(f"Drag originated from SOURCE socket: {drag_origin_socket_addr}. Looking for TARGET sockets.")

        for partner_node in self.entity_graph.nodes.values():
            partner_sockets_map: Mapping[str, "EntitySocket"] = getattr(partner_node, partner_sockets_collection_name)

            for partner_socket_name in partner_sockets_map.keys():
                potential_partner_socket_addr = SocketAddress(partner_node.id, partner_socket_name)

                if drag_origin_ui_socket_item.role == SocketRole.TARGET:  # Reverse drag
                    # Proposed edge: potential_partner_socket_addr (Output) -> drag_origin_socket_addr (Input)
                    prospective_source_addr = potential_partner_socket_addr
                    prospective_target_addr = drag_origin_socket_addr
                else:  # Standard drag
                    # Proposed edge: drag_origin_socket_addr (Output) -> potential_partner_socket_addr (Input)
                    prospective_source_addr = drag_origin_socket_addr
                    prospective_target_addr = potential_partner_socket_addr

                can_form, reason = self.entity_graph.can_form_link(prospective_source_addr, prospective_target_addr)
                if can_form:
                    valid_targets.add(potential_partner_socket_addr)
                else:
                    logger.trace(
                        f"  EntityGraph: Cannot form edge from {prospective_source_addr} "
                        f"to {prospective_target_addr}: {reason}"
                    )

        logger.debug(
            f"Found {len(valid_targets)} valid drop targets for {drag_origin_socket_addr} via EntityGraph: {valid_targets}"
        )
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
