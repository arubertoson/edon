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

from edon.graph import EdgeKey, EntityGraph, SocketAddress, SocketRole
from edon.node import EntityNode
from edon_ui import theme
from edon_ui.graph.registry import GraphUIDataRegistry
from edon_ui.items.edge import EdgeItem
from edon_ui.items.factory import create_node_item
from edon_ui.items.node import NodeItem
from edon_ui.views.scene import DragPrepInfo

if TYPE_CHECKING:
    from edon.errors import GraphObjectErrorReason, SocketLinkErrorReason
    from edon.socket import EntitySocket
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
        replaces the entity graph, and rebuilds the UI from the new graph data.
        Ideal for file loading, graph replacement, or resetting the workspace.
        """
        logger.info(f"Loading new graph with {len(entity_graph.nodes)} nodes")

        assert self._scene is not None, "Scene must be set before loading a graph."

        self._clear_all_ui()
        self.entity_graph = entity_graph
        self._populate_scene_from_graph_data()
        self._scene._update_scene_content_display()  # Ensure empty scene text is updated

        logger.info("Graph loading completed successfully")

    def clear_graph(self) -> None:
        """
        Clears the current graph and all UI elements, returning to empty state.
        """
        logger.info("Clearing current graph and UI")
        assert self._scene is not None, "Scene must be set before clearing the graph."
        self._clear_all_ui()
        self.entity_graph = EntityGraph()  # Reset to a new empty graph
        self._scene._update_scene_content_display()

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
        assert self._scene is not None, "Scene must be set before registering a node."

        # Validate the node exists in the entity graph
        assert entity_node.id in self.entity_graph.nodes, (
            f"CORRUPTION: Cannot register UI for node '{entity_node.id}': not found in entity graph"
        )

        node_item = create_node_item(
            entity_node,
            scene_position.x(),
            scene_position.y(),
        )

        # Register with scene and data layer
        self.scene.add_node(node_item)
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

    def _populate_scene_from_graph_data(self) -> None:
        """
        Populates the GraphicsScene with NodeItems and EdgeItems based on the
        current EntityGraph using internal registration methods.
        This is called by set_scene() after the scene is linked.
        """
        logger.debug("GraphController: Populating UI scene from entity graph data.")

        # XXX: Layout logic should not exist here, we should have positions from a saved serialization.
        # Basic layout logic (can be made more sophisticated), consider a dependency injection
        # for layout functionality.
        default_x, default_y = 50.0, 50.0
        # Use getattr for theme attributes to provide defaults if theme doesn't have them
        spacing_x = getattr(theme, "NODE_MIN_WIDTH", 150.0) + 50.0
        spacing_y = getattr(theme, "NODE_MIN_HEIGHT", 100.0) + 50.0
        nodes_per_row = 5

        for i, (_, entity_node) in enumerate(self.entity_graph.nodes.items()):
            pos_x = default_x + (i % nodes_per_row) * spacing_x
            pos_y = default_y + (i // nodes_per_row) * spacing_y
            self._register_node_internal(entity_node, QPointF(pos_x, pos_y))

        processed_edge_keys: set[EdgeKey] = set()
        for source_node_id, source_entity_node in self.entity_graph.nodes.items():
            # We treat this as a DAG, using the source to establish connection to targets.
            for (
                source_socket_name,
                source_entity_socket,
            ) in source_entity_node.source_sockets.items():
                for linked_target_entity_socket in source_entity_socket.links:
                    target_node_id = linked_target_entity_socket.node.id
                    target_socket_name = linked_target_entity_socket.name

                    edge_key = EdgeKey(
                        source=SocketAddress(
                            node_id=source_node_id, socket_name=source_socket_name
                        ),
                        target=SocketAddress(
                            node_id=target_node_id, socket_name=target_socket_name
                        ),
                    )
                    if edge_key not in processed_edge_keys:
                        self._register_edge_internal(edge_key)
                        processed_edge_keys.add(edge_key)

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
                f"Target socket {target_socket_addr.node_id}::{target_socket_addr.socket_name} already has a link, removing existing."
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
        Creates a new entity node and adds it to both the entity graph and UI.

        This is the primary method for adding new nodes during user interaction.
        It follows the pattern: create entity → add to graph → register UI.
        """
        logger.debug(f"Creating new node of type '{node_entity_class}' at {scene_position}")

        new_entity_node = node_entity_class(**node_specific_kwargs)
        self.entity_graph.add_node(new_entity_node)  # Add to the graph first

        # Then register its UI representation
        node_item = self._register_node_internal(new_entity_node, scene_position)

        return node_item

    def request_add_edge(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Link sockets in the entity graph and then register the UI edge representation.
        """
        logger.debug(f"GraphController: Requesting to create edge: {edge_key}")

        link_success, _ = self.entity_graph.link_sockets(
            edge_key.source,
            edge_key.target,
        )

        if link_success:
            logger.debug(f"EntityGraph link successful for {edge_key}.")
            # If link_success is true, _register_edge_internal is guaranteed to return an EdgeItem
            # or GraphUIDataRegistry would have asserted if socket items were not found.
            edge_item = self._register_edge_internal(edge_key)
            assert edge_item is not None, (
                "CORRUPTION: _register_edge_internal returned None unexpectedly after successful link"
            )  # Should be unreachable
            return edge_item
        # If link_success is false, it implies a condition that should ideally be caught
        # by can_form_link checks before attempting to link.
        # For tiger style, we might assert here if we expect `can_form_link` to prevent this.
        # However, EntityGraph.link_sockets itself might return reasons for failure that are not
        # strictly corruption (e.g. max connections reached if that was a soft rule).
        # For now, let's assume if link_sockets fails, it's a state that shouldn't have been reached.
        assert link_success, (
            f"CORRUPTION: EntityGraph.link_sockets failed for {edge_key} with reason {_}"
        )
        # The following line is unreachable due to the assertion above but makes linters happy.
        raise AssertionError("Unreachable code after link_sockets failure assertion")

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
            self.entity_graph.unlink_sockets(edge_item.edge_key.source, edge_item.edge_key.target)
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
        disconnection_success, reason = self.entity_graph.unlink_sockets(
            edge_key.source, edge_key.target
        )
        assert disconnection_success, (
            f"CORRUPTION: Entity disconnection FAILED for {edge_key}. Reason: {reason}."
        )

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
            actual_source_addr = actual_source_socket_item.socket_address

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
        """
        valid_targets: set[SocketAddress] = set()
        unvalid_targets: set[SocketAddress] = set()

        drag_origin_node_entity = self.entity_graph.get_node(drag_origin_socket_addr.node_id)
        drag_origin_socket_item = self.data.socket_item_for_address(drag_origin_socket_addr)
        drag_origin_role = drag_origin_socket_item.role

        # Based on the drag origin's role, determine the roles and corresponding socket
        # collection names on other nodes.
        potential_link_partners_collection_name: (
            str  # Sockets to check with can_form_link (opposite role to origin)
        )
        same_role_as_origin_collection_name: (
            str  # Sockets inherently invalid (same role as origin)
        )
        target_role: SocketRole  # The role a socket must have to potentially link with drag_origin

        if drag_origin_role == SocketRole.SOURCE:
            target_role = SocketRole.TARGET
            potential_link_partners_collection_name = "target_sockets"
            same_role_as_origin_collection_name = "source_sockets"
        else:  # drag_origin_role == SocketRole.TARGET
            target_role = SocketRole.SOURCE
            potential_link_partners_collection_name = "source_sockets"
            same_role_as_origin_collection_name = "target_sockets"

        logger.debug(
            f"Drag from {drag_origin_socket_addr} (role: {drag_origin_role}). "
            f"Potential link partners must have role: {target_role} (collection: '{potential_link_partners_collection_name}'). "
            f"Sockets with role {drag_origin_role} (collection: '{same_role_as_origin_collection_name}') are inherently invalid."
        )
        # The assertion `assert not drag_origin_role == target_role` is implicitly covered by the logic
        # above, as drag_origin_role and target_role are now defined to be opposites.

        # Iterate through each node in the graph to categorize its sockets.
        for entity_node in self.entity_graph.nodes.values():
            # 1. Add sockets with the same role as drag_origin to unvalid_targets.
            #    These are inherently incompatible for forming a new link.
            #    dict.values() returns a view (Iterable).
            sockets_with_same_role_view: Iterable[EntitySocket] = getattr(
                entity_node, same_role_as_origin_collection_name
            ).values()

            current_node_inherently_invalid_addrs: set[SocketAddress] = set()
            for s in sockets_with_same_role_view:
                addr = SocketAddress(node_id=entity_node.id, socket_name=s.name)
                current_node_inherently_invalid_addrs.add(addr)
                logger.trace(
                    f"  Marking {addr} as invalid (role incompatibility: same as drag origin role {drag_origin_role})."
                )
            unvalid_targets.update(current_node_inherently_invalid_addrs)

            # 2. Check sockets with the opposite role (potential_link_partners) using can_form_link.
            #    These are candidates for valid_targets or unvalid_targets based on detailed rules.
            potential_partner_sockets_view: Iterable[EntitySocket] = getattr(
                entity_node, potential_link_partners_collection_name
            ).values()

            # We are working on theoretical links, this means that we do have to create addresses and
            # from each sockets to our origin address that we are currently dragging.
            for entity_socket_link_candidate in potential_partner_sockets_view:
                link_candidate_addr = SocketAddress(
                    node_id=entity_node.id, socket_name=entity_socket_link_candidate.name
                )

                prospective_source_addr: SocketAddress
                prospective_target_addr: SocketAddress
                entity_socket_receiving_link: "EntitySocket"

                if drag_origin_role == SocketRole.SOURCE:
                    # Standard drag: drag_origin (SOURCE) -> current_partner (TARGET)
                    prospective_source_addr = drag_origin_socket_addr
                    prospective_target_addr = link_candidate_addr
                    entity_socket_receiving_link = entity_socket_link_candidate
                else:
                    # Reverse drag: current_partner (SOURCE) -> drag_origin (TARGET)
                    prospective_source_addr = link_candidate_addr
                    prospective_target_addr = drag_origin_socket_addr
                    entity_socket_receiving_link = drag_origin_node_entity.target_sockets[
                        drag_origin_socket_addr.socket_name
                    ]

                # Now we have established the theoretical setup, we have our sockets, addresses and nodes,
                # it's time to check if this setup is valid or not.
                can_form: bool
                reason: SocketLinkErrorReason | GraphObjectErrorReason | None

                # Overwrite logic: if the socket receiving the link is a TARGET socket
                # and it's already connected, temporarily remove its existing links
                # to check if the new link can be formed (simulating replacement).
                if entity_socket_receiving_link.role == SocketRole.TARGET and bool(
                    entity_socket_receiving_link.links
                ):
                    # XXX: This feels like a dangerous operation, we are changing the state of the graph
                    # to validate a connection. We need to handle this differently. There is a theritical
                    # hey, "could we make this connection", and "can we make this connection."
                    original_links = list(entity_socket_receiving_link.links)
                    entity_socket_receiving_link.links.clear()

                    can_form, reason = self.entity_graph.can_form_link(
                        prospective_source_addr, prospective_target_addr
                    )

                    entity_socket_receiving_link.links.extend(original_links)
                else:
                    # Not a TARGET socket, or not linked. `can_form_link` handles role, type compatibility etc.
                    can_form, reason = self.entity_graph.can_form_link(
                        prospective_source_addr, prospective_target_addr
                    )

                if can_form:
                    valid_targets.add(link_candidate_addr)
                    logger.trace(
                        f"  EntityGraph: Can form edge from {prospective_source_addr} "
                        f"to {prospective_target_addr}: {reason}"
                    )
                else:
                    unvalid_targets.add(link_candidate_addr)
                    logger.trace(
                        f"  EntityGraph: Cannot form edge from {prospective_source_addr} "
                        f"to {prospective_target_addr}: {reason}"
                    )

        logger.debug(
            f"Found {len(valid_targets)} valid drop targets for {drag_origin_socket_addr} via EntityGraph: {valid_targets}"
        )
        return valid_targets, unvalid_targets

    def find_edge_items_at_socket(self, socket_addr: SocketAddress) -> set[EdgeItem]:
        """Retrieves all UI EdgeItems connected to the given socket address from the UI registry.

        Assertions in `GraphUIDataRegistry` handle cases where the socket address is not found.
        """
        return self.data.edge_items_for_socket(socket_addr)
