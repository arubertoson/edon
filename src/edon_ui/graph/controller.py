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
from typing import TYPE_CHECKING, Type

from loguru import logger
from PySide6.QtCore import QPointF

from edon.graph import EdgeKey, EntityGraph, SocketAddress, SocketRole
from edon.node import EntityNode
from edon_ui import theme
from edon_ui.items.edge import EdgeItem
from edon_ui.items.factory import create_node_item
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketItem

if TYPE_CHECKING:
    from edon.socket import EntitySocket
    from edon_ui.views.scene import GraphicsScene


type NodeItemMap = MutableMapping[str, NodeItem]
type EdgeItemMap = MutableMapping[EdgeKey, EdgeItem]
type SocketItemMap = MutableMapping[SocketAddress, SocketItem]
type SocketEdgeKeyMap = MutableMapping[SocketAddress, set[EdgeKey]]
type NodeRegistryMap = MutableMapping[str, Type[EntityNode]]


class GraphController:
    """
    Controls the synchronization between the entity graph (edon.graph.EntityGraph)
    and the UI representation (edon_ui.graphics_scene.GraphicsScene).

    It acts as the intermediary, translating UI actions into model operations
    and reflecting model changes in the UI. It can be initialized with an
    optional `node_type_registry` to map node type string identifiers to their
    respective `EntityNode` classes, facilitating node creation from type hints.
    """

    def __init__(
        self,
        entity_graph: EntityGraph,
        node_type_registry: Mapping[str, Type[EntityNode]] | None = None,
    ):
        self.entity_graph: EntityGraph = entity_graph
        self.ui_scene: "GraphicsScene" | None = None  # Will be set by set_scene

        # Maps for entity graph to UI items
        self.edge_map: EdgeItemMap = {}
        self.node_map: NodeItemMap = {}
        self.socket_addr_socket_item_map: SocketItemMap = {}
        self.socket_addr_edge_key_map: SocketEdgeKeyMap = defaultdict(set)

        self.node_registry: NodeRegistryMap = dict(node_type_registry or {})

        logger.info(f"GraphController initialized with entity graph: {self.entity_graph}. UI scene will be set later.")

    def set_scene(self, scene: "GraphicsScene") -> None:
        """Links the controller to its UI scene and populates the scene."""
        self.ui_scene = scene
        logger.info(f"GraphController: UI scene set to {self.ui_scene}. Populating scene from graph data.")
        self._populate_scene_from_graph_data()

    def _register_node_internal(self, entity_node: EntityNode, scene_position: QPointF) -> NodeItem | None:
        """
        Creates a NodeItem for the given EntityNode, adds it to the scene,
        and updates internal controller maps.
        Assumes entity_node is already in self.entity_graph.
        """
        assert self.ui_scene is not None, "UI Scene must be set before registering nodes."
        logger.debug(f"GraphController: Registering UI for node '{entity_node.id}' at {scene_position}")
        try:
            node_item = create_node_item(
                entity_node,
                scene_position.x(),
                scene_position.y(),
            )
            logger.warning("1")
            self.ui_scene.add_node(node_item)
            self.node_map[entity_node.id] = node_item

            for socket_item in node_item.source_sockets + node_item.target_sockets:
                if not socket_item:
                    continue

                self.socket_addr_socket_item_map[socket_item.socket_address] = socket_item

            logger.debug(f"UI for node '{entity_node.id}' registered successfully. UI Item: {node_item.title}")
            return node_item
        except Exception as e:
            logger.error(f"Error registering UI for node '{entity_node.id}': {e}", exc_info=True)
            # Consider if rollback of entity_node from entity_graph is needed if called from request_add_node
            return None

    def _register_edge_internal(self, edge_key: EdgeKey) -> EdgeItem | None:
        """
        Creates an EdgeItem for the given EdgeKey, adds it to the scene,
        and updates internal controller maps.
        Assumes the link exists in self.entity_graph and source/target node UIs are registered.
        """
        assert self.ui_scene is not None, "UI Scene must be set before registering edges."
        logger.debug(f"GraphController: Registering UI for edge {edge_key}")

        source_socket_addr = edge_key.source
        target_socket_addr = edge_key.target

        source_socket_item = self.socket_addr_socket_item_map.get(source_socket_addr)
        target_socket_item = self.socket_addr_socket_item_map.get(target_socket_addr)

        assert source_socket_item and target_socket_item, "State without existing sockets should not be possible"

        try:
            edge_item = EdgeItem(source_socket_item.link_item, target_socket_item.link_item)

            self.ui_scene.add_edge(edge_item)
            self.edge_map[edge_key] = edge_item
            self.socket_addr_edge_key_map[source_socket_addr].add(edge_key)
            self.socket_addr_edge_key_map[target_socket_addr].add(edge_key)

            logger.debug(f"UI for edge {edge_key} registered successfully. UI Item: {edge_item}")
            return edge_item
        except Exception as e:
            logger.error(f"Error registering UI for edge {edge_key}: {e}", exc_info=True)
            # Consider if rollback of link in entity_graph is needed if called from request_add_edge
            return None

    def _populate_scene_from_graph_data(self) -> None:
        """
        Populates the GraphicsScene with NodeItems and EdgeItems based on the
        current EntityGraph using internal registration methods.
        This is called by set_scene() after the scene is linked.
        """
        assert self.ui_scene is not None, "UI Scene must be set before populating it."

        logger.info("GraphController: Populating UI scene from entity graph data.")

        # Basic layout logic (can be made more sophisticated), consider a dependency injection
        # for layout functionality.
        default_x, default_y = 50.0, 50.0
        # Use getattr for theme attributes to provide defaults if theme doesn't have them
        spacing_x = getattr(theme, "NODE_MIN_WIDTH", 150.0) + 50.0
        spacing_y = getattr(theme, "NODE_MIN_HEIGHT", 100.0) + 50.0
        nodes_per_row = 5

        for i, (node_id, entity_node) in enumerate(self.entity_graph.nodes.items()):
            # TODO: Persist and use actual node positions from entity_node.metadata if available
            pos_x = default_x + (i % nodes_per_row) * spacing_x
            pos_y = default_y + (i // nodes_per_row) * spacing_y
            self._register_node_internal(entity_node, QPointF(pos_x, pos_y))
        logger.debug(f"GraphController: Registered UI for {len(self.node_map)} nodes from entity graph.")

        # Register edges
        processed_edge_keys: set[EdgeKey] = set()
        for source_node_id, source_entity_node in self.entity_graph.nodes.items():
            # We treat this as a DAG, using the source to establish connection to targets.
            for source_socket_name, source_entity_socket in source_entity_node.source_sockets.items():
                for linked_target_entity_socket in source_entity_socket.links:  # These are EntitySocket instances
                    target_node_id = linked_target_entity_socket.node.id
                    target_socket_name = linked_target_entity_socket.name

                    edge_key = EdgeKey(
                        source=SocketAddress(node_id=source_node_id, socket_name=source_socket_name),
                        target=SocketAddress(node_id=target_node_id, socket_name=target_socket_name),
                    )
                    if edge_key not in processed_edge_keys:
                        self._register_edge_internal(edge_key)
                        processed_edge_keys.add(edge_key)

        logger.debug(f"GraphController: Registered UI for {len(self.edge_map)} edges from entity graph.")

        self.ui_scene._refresh_scene_interaction_state()
        logger.info("GraphController: UI scene population complete.")

    def handle_ui_node_creation_request(self, node_type_hint: str, scene_pos: QPointF) -> None:
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

        # Node names are auto-generated based on type and a running count to ensure uniqueness.
        # This logic for name generation could be part of EntityNode.__init__ or a factory.
        type_count = sum(
            1
            for node_id in self.entity_graph.nodes
            if self.entity_graph.nodes[node_id].node_type_name == node_class_to_create.node_type_name()
        )
        node_name = f"{node_class_to_create.node_type_name()} {type_count + 1}"

        self.request_add_node(
            node_entity_class=node_class_to_create,
            scene_position=scene_pos,
            **{"title": node_name},
        )

    def handle_ui_edge_link_request(
        self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress
    ) -> None:
        """
        Handles a UI request to connect two sockets identified by their SocketAddress.

        Attempts to add the new edge if it doesn't already exist.
        """
        logger.debug(
            f"GraphController: Received handle_ui_edge_connection_attempt from "
            f"source {source_socket_addr} to target {target_socket_addr}"
        )

        edge_key = EdgeKey(source_socket_addr, target_socket_addr)
        if edge_key in self.edge_map:  # Check UI map first
            logger.warning(f"Edge {edge_key} already exists in UI. Ignoring connection attempt.")
            return

        # If the target socket already has an edge, we remove it, input nodes can only have one edge
        # and we decided on behavior that the new edge will replace the old one.
        edge_items = self.find_edge_items_at_socket(target_socket_addr)
        if edge_items:
            logger.warning(
                f"Target socket {target_socket_addr.node_id}::{target_socket_addr.socket_name} already has edges. Overwriting"
            )
            self.handle_ui_edge_deletion_request(list(edge_items))

        self.request_add_edge(edge_key)

    def handle_ui_node_deletion_request(self, entity_node_ids: Sequence[str]) -> None:
        """Processes a UI request to delete one or more specified nodes."""
        logger.info(f"GraphController: Received handle_ui_node_deletion_request for IDs: {entity_node_ids}")
        for node_id in entity_node_ids:
            self.request_remove_node(node_id)

    def handle_ui_edge_deletion_request(self, edge_items: Sequence[EdgeItem]) -> None:
        """Processes a UI request to delete one or more specified edges."""
        logger.info(f"GraphController: Received handle_ui_edge_deletion_request for {len(edge_items)} edge(s).")
        for edge_item in edge_items:
            if edge_item.edge_key:  # Ensure edge_key is available
                self.request_remove_edge(edge_item.edge_key)
            else:
                logger.warning(f"EdgeItem {edge_item} has no edge_key, cannot process deletion request.")

    def request_add_node(
        self,
        node_entity_class: type[EntityNode],
        scene_position: QPointF,
        **node_specific_kwargs,
    ) -> NodeItem | None:
        """
        Create a new entity node, add it to the entity graph, and then register
        its UI representation.
        """
        node_type_name = node_entity_class.__name__
        logger.info(f"GraphController: Requesting to add node of type '{node_type_name}' at {scene_position}")

        try:
            new_entity_node = node_entity_class(**node_specific_kwargs)
            self.entity_graph.add_node(new_entity_node)

            node_item = self._register_node_internal(new_entity_node, scene_position)
            if node_item:
                logger.info(
                    f"Successfully created and registered node: {new_entity_node.name} "
                    f"(Entity ID: {new_entity_node.id}, UI: {node_item.name})"
                )
            else:
                logger.error(
                    f"Failed to register UI for node '{new_entity_node.id}'. Rolling back entity graph add might be needed."
                )
                self.entity_graph.remove_node(new_entity_node.id)

            return node_item
        except Exception as e:
            logger.error(f"Error in request_add_node for type '{node_type_name}': {e}", exc_info=True)
            return None

    def request_add_edge(self, edge_key: EdgeKey) -> EdgeItem | None:
        """
        Link sockets in the entity graph and then register the UI edge representation.
        """
        logger.debug(f"GraphController: Requesting to create edge: {edge_key}")

        link_success, reason = self.entity_graph.link_sockets(
            edge_key.source,
            edge_key.target,
        )

        if link_success:
            logger.debug(f"EntityGraph link successful for {edge_key}.")

            edge_item = self._register_edge_internal(edge_key)
            if edge_item:
                logger.debug(f"Successfully created and registered edge: {edge_key}")
            else:
                logger.error(
                    f"Failed to register UI for edge {edge_key}. Rolling back entity graph link might be needed."
                )
                self.entity_graph.unlink_sockets(edge_key.source, edge_key.target)

            return edge_item
        else:
            logger.warning(f"EntityGraph link FAILED for {edge_key}. Reason: {reason}. No UI edge created.")
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

            for partner_socket_name, partner_socket in partner_sockets_map.items():
                potential_partner_socket_addr = SocketAddress(partner_node.id, partner_socket_name)

                if drag_origin_ui_socket_item.role == SocketRole.TARGET:  # Reverse drag
                    # Proposed edge: potential_partner_socket_addr (Output) -> drag_origin_socket_addr (Input)
                    prospective_source_addr = potential_partner_socket_addr
                    prospective_target_addr = drag_origin_socket_addr
                    # The target socket is the drag origin's socket
                    target_socket = self.entity_graph.get_node(drag_origin_socket_addr.node_id).target_sockets[
                        drag_origin_socket_addr.socket_name
                    ]
                else:  # Standard drag
                    # Proposed edge: drag_origin_socket_addr (Output) -> potential_partner_socket_addr (Input)
                    prospective_source_addr = drag_origin_socket_addr
                    prospective_target_addr = potential_partner_socket_addr
                    target_socket = partner_socket

                # If the target socket is a TARGET and already has a link, simulate unlinking it
                is_target = target_socket.role == SocketRole.TARGET
                already_linked = bool(target_socket.links)
                if is_target and already_linked:
                    # Temporarily remove all links
                    old_links = list(target_socket.links)
                    target_socket.links.clear()
                    can_form, reason = self.entity_graph.can_form_link(
                        prospective_source_addr, prospective_target_addr
                    )
                    # Restore links
                    target_socket.links.extend(old_links)
                else:
                    can_form, reason = self.entity_graph.can_form_link(
                        prospective_source_addr, prospective_target_addr
                    )

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

    def find_edge_items_at_socket(self, socket_addr: SocketAddress) -> set[EdgeItem]:
        """Retrieves all UI EdgeItems connected to the given socket address."""
        edge_keys = self.socket_addr_edge_key_map.get(socket_addr, set())
        edge_items: set[EdgeItem] = set()
        for key in edge_keys:
            item = self.edge_map.get(key)
            if item:
                edge_items.add(item)
        return edge_items
