"""Manages the interaction between the data-centric EntityGraph and the UI GraphicsScene.

This module provides the GraphController class, which is responsible for:
- Populating the graphics scene with nodes and edges based on the entity graph.
- Handling UI requests to add, remove, or modify nodes and edges,
  and translating these into operations on the entity graph.
- Keeping the UI representation synchronized with the state of the entity graph.
- Responding to signals from UI elements for graph-related actions.

"""

from collections.abc import Mapping, Sequence, MutableMapping
from typing import TYPE_CHECKING, Type

from loguru import logger
from PySide6.QtCore import QPointF

from edon.graph import EntityGraph
from edon.types import SocketAddress, SocketRole, EdgeKey
from edon.node import EntityNode
from edon_ui import theme
from edon_ui.graph.registry import GraphUIDataRegistry
from edon_ui.items.edge import EdgeItem
from edon_ui.items.factory import create_node_item
from edon_ui.items.node import NodeItem
from edon_ui.views.scene import DragPrepInfo

if TYPE_CHECKING:
    from edon_ui.views.scene import GraphicsScene


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
        node_type_registry: Mapping[str, Type[EntityNode]] | None = None,
    ):
        """
        Initialize controller with empty graph and registry.
        Graph content will be loaded separately via load_graph().
        """
        self._scene: "GraphicsScene | None" = None  # Will be set by set_scene
        self.entity_graph: EntityGraph = EntityGraph()  # Always start empty
        self.data: GraphUIDataRegistry = GraphUIDataRegistry()
        self.node_registry: NodeRegistryMap = dict(node_type_registry or {})

        logger.info(
            "GraphController initialized with an empty entity graph. UI scene will be set later."
        )

    @property
    def scene(self) -> "GraphicsScene":
        assert self._scene is not None, "CORRUPTION: Using scene opertion without a scene set."

        return self._scene

    @scene.setter
    def scene(self, scene: "GraphicsScene") -> None:
        logger.debug(
            f"GraphController: UI scene set to {scene}. Populating scene from graph data."
        )

        self._scene = scene

    def _clear_all_ui(self) -> None:
        """
        Removes all UI elements and clears the registry.

        This method ensures a clean slate by removing all visual elements
        and resetting the UI data registry. Order matters: edges must be
        removed before nodes due to dependencies.
        """
        # XXX: We should look into scene reset that is prettier than this.
        # I don't think we have to go through everything and delete it.
        # But if we do we should delegate it to scene either way.
        edge_items_to_remove = list(self.data.edges)
        for edge_item in edge_items_to_remove:
            self.scene.remove_edge(edge_item)

        node_items_to_remove = list(self.data.nodes)
        for node_item in node_items_to_remove:
            self.scene.remove_node(node_item)

        # Reset the registry to clean state
        self.data = GraphUIDataRegistry()
        # self._registration_order.clear() # _registration_order is not a member

        logger.debug(
            f"Cleared {len(edge_items_to_remove)} edges and {len(node_items_to_remove)} nodes"
        )

    def load_graph(self, entity_graph: EntityGraph) -> None:
        """
        Replaces the current graph and rebuilds the entire UI representation.

        This method provides a clean slate approach: it clears all existing UI elements,
        creates a fresh empty entity graph, and populates both the graph and UI
        from the given graph data.
        """
        logger.info(f"Loading new graph with {len(entity_graph.nodes)} nodes")

        # Reset All Sources
        self.data = GraphUIDataRegistry()
        self.entity_graph = EntityGraph()
        self.scene.clear()

        # Create Scene state from the given entity_graph
        self._populate_scene_from_graph_data(source_graph=entity_graph)
        self.scene._update_scene_content_display()

        logger.info("Graph loading completed successfully")

    def _register_node_internal(
        self, entity_node: EntityNode, scene_position: QPointF
    ) -> NodeItem:
        """
        Creates a NodeItem for an EntityNode that is ALREADY in self.entity_graph.

        This method only handles UI registration and assumes the entity_node
        is already properly added to the entity graph. It never modifies
        the entity graph itself, maintaining clear separation of concerns.
        """
        logger.debug(f"Registering UI for existing node '{entity_node.id}' at {scene_position}")

        node_item = create_node_item(
            entity_node,
            scene_position.x(),
            scene_position.y(),
        )

        # Register with scene and data layer
        self.scene.add_node(node_item)
        self.entity_graph.add_node(entity_node)

        self.data.register_node_with_sockets(node_item)

        return node_item

    def _register_edge_internal(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Creates an EdgeItem for the given EdgeKey, adds it to the scene,
        and updates internal controller maps.
        Assumes the link exists in self.entity_graph and source/target node UIs are registered.
        """
        logger.debug(f"GraphController: Registering UI for edge {edge_key}")

        source_socket_addr = edge_key.source
        target_socket_addr = edge_key.target

        edge_item = EdgeItem(
            self.data.socket_item_for_address(source_socket_addr),
            self.data.socket_item_for_address(target_socket_addr),
        )

        self.scene.add_edge(edge_item)
        self.data.register_edge_item(edge_key, edge_item)

        return edge_item

    def _populate_scene_from_graph_data(self, source_graph: EntityGraph | None = None) -> None:
        """
        Populates the GraphicsScene with NodeItems and EdgeItems based on the
        given source graph (or current EntityGraph if None).
        """
        graph_to_read = source_graph if source_graph is not None else self.entity_graph

        logger.debug(
            f"GraphController: Populating UI scene from {'external' if source_graph else 'current'} entity graph data."
        )

        # XXX: Temporary solution, we will track layout info in the serialization.
        default_x, default_y = 50.0, 50.0
        spacing_x = getattr(theme, "NODE_MIN_WIDTH", 150.0) + 50.0
        spacing_y = getattr(theme, "NODE_MIN_HEIGHT", 100.0) + 50.0
        nodes_per_row = 5

        # Add all nodes using existing request method
        for i, (_, entity_node) in enumerate(graph_to_read.nodes.items()):
            pos_x = default_x + (i % nodes_per_row) * spacing_x
            pos_y = default_y + (i // nodes_per_row) * spacing_y

            # We are working with existing entity_nodes, request_add_node will create the
            # entity node, we simply want to register it.
            self._register_node_internal(entity_node, scene_position=QPointF(pos_x, pos_y))

        # Add all edges using existing request method
        for edge_key in graph_to_read.edges:
            self.request_add_edge(edge_key)

        self.scene._update_scene_content_display()

    def handle_ui_node_creation_request(self, node_type_hint: str, scene_pos: QPointF) -> None:
        """
        Slot to handle the new_node_requested_at_scene_pos signal from the UI (e.g., GraphicsView).
        It determines the entity node class to create based on the hint and then
        calls the main request_add_node method.
        """
        logger.debug(
            f"GraphController: Received handle_ui_node_creation_request for type '{node_type_hint}' at {scene_pos}"
        )

        node_class_to_create = self.node_registry.get(node_type_hint)
        assert node_class_to_create is not None, (
            f"CORRUPTION: Node type hint '{node_type_hint}' not found in registry. Cannot create node."
        )

        self.request_add_node(
            node_entity_class=node_class_to_create,
            scene_position=scene_pos,
            **{"title": node_class_to_create.node_type},
        )

    def handle_ui_edge_link_request(
        self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress
    ) -> None:
        """
        Handles a UI request to link two sockets identified by their SocketAddress.

        Attempts to add the new edge if it doesn't already exist.
        """
        logger.debug(
            f"GraphController: Received handle_ui_edge_link_attempt from "
            f"source {source_socket_addr} to target {target_socket_addr}"
        )

        edge_key = EdgeKey(source_socket_addr, target_socket_addr)

        # If the target socket already has an edge, we remove it, input nodes can only have one edge
        # and we decided on behavior that the new edge will replace the old one.
        # This uses the updated find_edge_items_at_socket which calls the registry.
        edge_items = self.data.edge_items_for_socket(target_socket_addr)
        if edge_items:
            logger.debug(
                f"Target socket {target_socket_addr.node_id}::{target_socket_addr.name} already has a link, removing existing."
            )
            self.handle_ui_edge_deletion_request(list(edge_items))

        self.request_add_edge(edge_key)

    def handle_ui_node_deletion_request(self, entity_node_ids: Sequence[str]) -> None:
        """Processes a UI request to delete one or more specified nodes."""
        logger.debug(
            f"GraphController: Received handle_ui_node_deletion_request for IDs: {entity_node_ids}"
        )

        for node_id in entity_node_ids:
            self.request_remove_node(node_id)

    def handle_ui_edge_deletion_request(self, edge_items: Sequence[EdgeItem]) -> None:
        """Processes a UI request to delete one or more specified edges."""
        logger.debug(
            f"GraphController: Received handle_ui_edge_deletion_request for {len(edge_items)} edge(s)."
        )

        for edge_item in edge_items:
            self.request_remove_edge(edge_item.edge_key)

    def request_add_node(
        self,
        node_entity_class: type[EntityNode],
        scene_position: QPointF,
        **node_specific_kwargs,
    ) -> NodeItem:
        """
        Creates a new entity node or uses an existing one, adding it to both
        the entity graph and UI.

        This is the primary method for adding nodes during user interaction
        or when populating from existing graph data.
        """
        logger.debug(f"Creating new node of type '{node_entity_class}' at {scene_position}")

        new_entity_node = node_entity_class(**node_specific_kwargs)
        node_item = self._register_node_internal(new_entity_node, scene_position)

        return node_item

    def request_add_edge(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Link sockets in the entity graph and then register the UI edge representation.
        """
        logger.debug(f"GraphController: Requesting to create edge: {edge_key}")

        link_success, reason = self.entity_graph.link_sockets(edge_key)
        assert link_success, (
            f"CORRUPTION: EntityGraph.link_sockets failed for {edge_key} with reason {reason}"
        )

        return self._register_edge_internal(edge_key)

    def request_remove_node(self, entity_node_id: str) -> None:
        """
        Handles a request to remove a node and its linked edges from both the
        entity graph and the UI scene.
        """
        logger.debug(f"GraphController: Requesting to remove node with ID: {entity_node_id}")

        # Unregister from UI registry; this will assert if node_id is not found.
        # It returns the node_item, and lists of socket_items and edge_items that were part of this node.
        node_item_to_remove, _removed_socket_items, removed_edge_items = self.data.unregister_node(
            entity_node_id
        )

        # XXX: should  `remove_node` handle removing edges as well or is that part of business logic?
        # currently the data layer and the entity graph is handling the edge cleanup when we remove a
        # node.
        # Remove associated edges from the entity graph and the scene
        for edge_item in removed_edge_items:
            # Entity graph unlinking is based on the edge_key from the UI edge_item
            # This might attempt to unlink sockets that are already unlinked if
            # entity_graph.remove_node below also handles unlinking.
            # However, entity_graph.unlink_sockets should be idempotent or handle this.
            self.entity_graph.unlink_sockets(edge_item.edge_key)
            self.scene.remove_edge(edge_item)

        self.entity_graph.remove_node(entity_node_id)
        self.scene.remove_node(node_item_to_remove)

    def request_remove_edge(self, edge_key: EdgeKey) -> None:
        """
        Handles a request to remove a single edge (entity and UI).
        """
        logger.debug(f"GraphController: Requesting to remove edge: {edge_key}")

        # XXX: This should be handled by assertions in the `entity_graph`, not by upstream checks.
        # Unlink sockets in the entity graph first. Refactor necessary.
        self.entity_graph.unlink_sockets(edge_key)

        edge_item = self.data.unregister_edge(edge_key)
        self.scene.remove_edge(edge_item)

        logger.debug(f"UI EdgeItem for {edge_key} removed from graphics scene and UI registry.")

    def prepare_drag_operation(self, clicked_socket_addr: SocketAddress) -> DragPrepInfo:
        """
        Analyzes a clicked socket and prepares the data needed for edge drag operations.

        Handles the business logic of edge lifting when dragging from input sockets
        that already have connections. Returns the actual source socket that should
        be used for the new edge, along with precomputed drop target validation.
        Assertions in `GraphUIDataRegistry` handle cases where the socket address is not found.
        If this method returns, it guarantees a valid DragPrepInfo object.
        """
        socket_item = self.data.socket_item_for_address(clicked_socket_addr)

        # Check if we need to lift an existing edge
        # This uses the updated find_edge_items_at_socket which calls the registry.
        linked_edges = list(self.data.edge_items_for_socket(clicked_socket_addr))

        if socket_item.role == SocketRole.TARGET and linked_edges:
            # Lift existing edge - the actual source becomes the original source
            assert len(linked_edges) == 1, (
                f"CORRUPTION: Target socket {clicked_socket_addr} should have exactly one edge, "
                f"found {len(linked_edges)}: {linked_edges}."
            )

            lifted_edge = linked_edges[0]
            actual_source_socket_item = lifted_edge.source_socket_item
            actual_source_addr = actual_source_socket_item.address

            # We need to clean up the edge that we lifted, it will be replaced
            # by a temporary edge and managed as a new object.
            self.handle_ui_edge_deletion_request(linked_edges)

            is_lifted = True
            logger.debug(
                f"Lifting edge from {clicked_socket_addr}, original source: {actual_source_addr}"
            )
        else:
            actual_source_addr = clicked_socket_addr
            actual_source_socket_item = socket_item
            is_lifted = False
            logger.debug(f"Preparing new edge drag from {clicked_socket_addr}")

        valid_targets, invalid_targets = self.partition_socket_drop_targets(actual_source_addr)

        return DragPrepInfo(
            source_socket_addr=actual_source_addr,
            source_socket_item=actual_source_socket_item,
            is_lifted_edge=is_lifted,
            valid_targets={
                addr: self.data.socket_item_for_address(addr) for addr in valid_targets
            },
            invalid_targets={
                addr: self.data.socket_item_for_address(addr) for addr in invalid_targets
            },
        )

    def partition_socket_drop_targets(
        self, drag_origin_socket_addr: SocketAddress
    ) -> tuple[set[SocketAddress], set[SocketAddress]]:
        """
        Determines valid drop target sockets for an edge drag operation.

        This method delegates to EntityGraph.get_connection_targets() to maintain
        proper separation of concerns between UI coordination and business logic.
        """
        valid_targets, invalid_targets = self.entity_graph.partition_valid_link_targets(
            drag_origin_socket_addr
        )

        logger.debug(
            f"Found {len(valid_targets)} valid drop targets for {drag_origin_socket_addr} via EntityGraph: {valid_targets}"
        )
        return valid_targets, invalid_targets

    def find_edge_items_at_socket(self, socket_addr: SocketAddress) -> set[EdgeItem]:
        """Retrieves all UI EdgeItems connected to the given socket address from the UI registry.

        Assertions in `GraphUIDataRegistry` handle cases where the socket address is not found.
        """
        return self.data.edge_items_for_socket(socket_addr)
