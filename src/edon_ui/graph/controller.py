"""
Manages the synchronization and interaction between the logical entity graph
and its visual representation in the UI.

This controller acts as the central point for handling user input related
to graph manipulation (node creation, deletion, linking) and reflecting
changes from the entity graph model onto the graphics scene. It also
manages the context when navigating into and out of subgraphs.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import TYPE_CHECKING, Type, cast

from loguru import logger
from PySide6.QtCore import QPointF, Slot

from edon.graph import EntityGraph, EntitySubGraphNode
from edon.node import EntityNode
from edon.types import EdgeKey, SocketAddress, SocketRole
from edon_ui import theme
from edon_ui.graph.context import ContextState, WorkspaceContextStack
from edon_ui.graph.registry import WorkspaceUIDataRegistry
from edon_ui.items.edge import EdgeItem
from edon_ui.items.factory import create_node_item
from edon_ui.items.node import NodeItem
from edon_ui.views.scene import EdgeDragContext, GraphicsScene
from edon_ui.views.viewer import GraphicsView

if TYPE_CHECKING:
    pass

type NodeRegistryMap = MutableMapping[str, Type[EntityNode]]


class WorkspaceController:
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
        Initialize controller, creating its own GraphicsView and initial root graph context.
        The GraphContextStack is initialized with this root context.
        Graph content can be loaded subsequently via load_graph().
        """
        self._view = GraphicsView(self)

        self.context_stack = WorkspaceContextStack()
        self.node_registry: NodeRegistryMap = dict(node_type_registry or {})

        init_scene = self._create_wired_scene()
        self._view.setScene(init_scene)
        assert self.view.scene() is init_scene, (
            "CORRUPTION: GraphicsView's scene does not match the initial_scene created by WorkspaceController."
        )

        self.context_stack.initialize(
            ContextState(
                graph=EntityGraph(),
                scene=init_scene,
                registry=WorkspaceUIDataRegistry(),
            )
        )

    def _create_wired_scene(self) -> GraphicsScene:
        scene = GraphicsScene()
        scene.edge_drag_initiation_request.connect(self.handle_ui_init_edge_drag_action)
        scene.edge_link_request.connect(self.handle_ui_edge_link_request)
        scene.node_redraw_ui_request.connect(self.handle_ui_node_redraw_request)

        return scene

    @property
    def view(self) -> GraphicsView:
        return self._view

    @property
    def scene(self) -> GraphicsScene:
        return self.context_stack.current.scene

    @property
    def graph(self) -> EntityGraph:
        return self.context_stack.current.graph

    @property
    def registry(self) -> WorkspaceUIDataRegistry:
        return self.context_stack.current.registry

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
        edge_items_to_remove = list(self.registry.edges)
        for edge_item in edge_items_to_remove:
            self.scene.remove_edge(edge_item)

        node_items_to_remove = list(self.registry.nodes)
        for node_item in node_items_to_remove:
            self.scene.remove_node(node_item)

        # Reset the registry to clean state
        self.context_stack.current.registry = WorkspaceUIDataRegistry()

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

        assert self.context_stack.is_at_root(), (
            "load_graph can only be called when at the root navigation level."
        )

        state = ContextState(
            graph=EntityGraph(),
            scene=self._create_wired_scene(),
            registry=WorkspaceUIDataRegistry(),
        )
        self.context_stack.initialize(state)

        # Create Scene state from the given entity_graph
        self._populate_scene_from_graph_data(entity_graph)

        self.view.setScene(state.scene)
        self.view.set_interactive_scene(bool(state.registry.nodes))

        logger.info("Graph loading completed successfully for the current context")

    def _register_node_internal(
        self, entity_node: EntityNode, scene_position: QPointF
    ) -> NodeItem:
        """
        Creates a NodeItem for an EntityNode that is ALREADY in self.graph.

        This method only handles UI registration and assumes the entity_node
        is already properly added to the entity graph. It never modifies
        the entity graph itself, maintaining clear separation of concerns.
        """
        logger.debug(f"Registering UI for existing node '{entity_node.id}' at {scene_position}")

        node_item = create_node_item(
            entity_node,
        )

        # XXX: we do this if we are populating a scene from existing graph
        if entity_node.id not in self.graph.nodes:
            self.graph.add_node(entity_node)

        self.registry.register_node_with_sockets(node_item)

        # Finally update graphics layers, scene/view behavior, if this is the first node added this will
        # enable interactivity etc.
        self.scene.add_node(node_item)

        if not self.view.is_interactive:
            self.view.set_interactive_scene(True)

        return node_item

    def _register_edge_internal(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Creates an EdgeItem for the given EdgeKey, adds it to the scene,
        and updates internal controller maps.
        Assumes the link exists in self.graph and source/target node UIs are registered.
        """
        logger.debug(f"GraphController: Registering UI for edge {edge_key}")

        source_socket_addr = edge_key.source
        target_socket_addr = edge_key.target

        edge_item = EdgeItem(
            self.registry.socket_item_for_address(source_socket_addr),
            self.registry.socket_item_for_address(target_socket_addr),
        )

        self.scene.add_edge(edge_item)
        self.registry.register_edge_item(edge_key, edge_item)

        return edge_item

    def _populate_scene_from_graph_data(self, source_graph: EntityGraph | None = None) -> None:
        """
        Populates the GraphicsScene with NodeItems and EdgeItems based on the
        given source graph (or current EntityGraph if None).
        """
        graph_to_read = source_graph if source_graph is not None else self.graph

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
            self._register_edge_internal(edge_key)

    def enter_subgraph(self, subgraph_node_item: NodeItem) -> None:
        """
        Switches the controller's context to the internal graph of the given SubGraphNodeItem.
        """
        logger.trace(f"Entering subgraph from depth {self.context_stack.depth}")

        # The graph and UI registry should be in sync; if node_item exists, entity_node must exist.
        entity_id = subgraph_node_item.entity_id
        entity_node = self.graph.get_node(entity_id)

        assert entity_node is not None, (
            f"CRITICAL: EntityNode with ID {entity_id} not found in graph despite UI item existing."
        )
        assert isinstance(entity_node, EntitySubGraphNode), (
            f"CORRUPTION: Node {entity_node.id} provided to enter_subgraph "
            f"is not a SubGraphNode. Actual type: {type(entity_node)}."
        )

        subgraph_entity = cast(EntitySubGraphNode, entity_node)
        context_state = ContextState(
            graph=subgraph_entity.internal_graph,
            scene=self._create_wired_scene(),
            registry=WorkspaceUIDataRegistry(),
            origin_subgraph_node=subgraph_entity,
        )
        self.context_stack.push(context_state)

        self._populate_scene_from_graph_data(source_graph=context_state.graph)

        # It's always important to update the interaction on the scene.
        self.view.setScene(self.scene)
        self.view.set_interactive_scene(bool(self.context_stack.current.registry.nodes))

        logger.debug(
            f"Successfully entered subgraph: {subgraph_entity.id}. Current depth: {self.context_stack.depth}"
        )

    def exit_subgraph(self) -> None:
        """
        Exits the current subgraph view and returns to the parent graph view.
        """
        logger.trace(f"Leaving subgraph from depth {self.context_stack.depth}")

        assert not self.context_stack.is_at_root(), (
            "Cannot exit subgraph: Already at the root graph."
        )

        self.context_stack.pop()
        logger.info(
            f"Exited subgraph. Current depth: {self.context_stack.depth}. "
            f"Now viewing graph: {self.context_stack.current.graph if self.context_stack.current.graph else 'Root'}"
        )

        # Update the view to display the parent scene
        self.view.setScene(self.scene)
        self.view.set_interactive_scene(bool(self.context_stack.current.graph.nodes))

    @Slot(str, QPointF)
    def handle_ui_node_creation_request(self, node_type_hint: str, scene_pos: QPointF) -> NodeItem:
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

        return self.request_add_node(
            node_entity_class=node_class_to_create,
            mouse_position=scene_pos,
        )

    @Slot(SocketAddress, SocketAddress)
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
        edge_items = self.registry.edge_items_for_socket(target_socket_addr)
        if edge_items:
            logger.debug(
                f"Target socket {target_socket_addr.node_id}::{target_socket_addr.name} already has a link, removing existing."
            )
            self.handle_ui_edge_deletion_request(list(edge_items))

        # If we are in a subgraph we need to check whether we have to update the SubGraphNode in the parent with
        # new context.
        if not self.context_stack.is_at_root():
            # Import here to avoid circular dependencies at module level if SubgraphPromoterNode
            # itself might eventually use controller functionalities, or keep at top if safe.
            from edon.nodes.utility import SubgraphPromoterNode

            source_node_entity = self.graph.get_node(source_socket_addr.node_id)
            target_node_entity = self.graph.get_node(target_socket_addr.node_id)

            is_source_node_promoter = isinstance(source_node_entity, SubgraphPromoterNode)
            is_target_node_promoter = isinstance(target_node_entity, SubgraphPromoterNode)
            if any([is_source_node_promoter, is_target_node_promoter]):
                if is_source_node_promoter:
                    internal_socket_addr = target_socket_addr
                else:
                    internal_socket_addr = source_socket_addr

                logger.debug(
                    f"Dispatching to request_expose_subgraph_socket: "
                    f"internal: {internal_socket_addr}"
                )
                self.request_expose_socket_from_subgraph(internal_socket_addr=internal_socket_addr)

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
        mouse_position: QPointF,
        **node_specific_kwargs,
    ) -> NodeItem:
        """
        Creates a new entity node or uses an existing one, adding it to both
        the entity graph and UI.

        This is the primary method for adding nodes during user interaction
        or when populating from existing graph data.
        """
        logger.debug(f"Creating new node of type '{node_entity_class}' at {mouse_position}")

        new_entity_node = node_entity_class(**node_specific_kwargs)
        node_item = self._register_node_internal(new_entity_node, mouse_position)

        return node_item

    def request_add_edge(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Link sockets in the entity graph and then register the UI edge representation.
        """
        logger.debug(f"GraphController: Requesting to create edge: {edge_key}")

        link_success, reason = self.graph.link_sockets(edge_key)
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
        node_item_to_remove, _removed_socket_items, removed_edge_items = (
            self.registry.unregister_node(entity_node_id)
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
            self.graph.unlink_sockets(edge_item.edge_key)
            self.scene.remove_edge(edge_item)

        self.graph.remove_node(entity_node_id)
        self.scene.remove_node(node_item_to_remove)

        # Finally update view behavior, if this is the first node added this will
        # enable interactivity etc.
        self.view.set_interactive_scene(bool(self.registry.nodes))

    def request_remove_edge(self, edge_key: EdgeKey) -> None:
        """
        Handles a request to remove a single edge (entity and UI).
        """
        logger.debug(f"GraphController: Requesting to remove edge: {edge_key}")

        # XXX: This should be handled by assertions in the `entity_graph`, not by upstream checks.
        # Unlink sockets in the entity graph first. Refactor necessary.
        self.graph.unlink_sockets(edge_key)

        edge_item = self.registry.unregister_edge(edge_key)
        self.scene.remove_edge(edge_item)

        logger.debug(f"UI EdgeItem for {edge_key} removed from graphics scene and UI registry.")

    def request_expose_socket_from_subgraph(self, internal_socket_addr: SocketAddress) -> None:
        """
        Handles a request to expose an internal socket of a subgraph as a proxy
        socket on the parent SubGraphNode.

        This is typically triggered by dragging an edge from an internal node's socket
        to a special socket on a SubgraphPromoterNode within the subgraph's view.
        """
        current_stack_state = self.context_stack.current
        assert current_stack_state.origin_subgraph_node is not None, (
            "CORRUPTION: Attempting to expose subgraph socket when not editing within a subgraph context."
        )

        subgraph_node_entity = current_stack_state.origin_subgraph_node
        subgraph_node_entity.add_proxy_socket(internal_socket_addr.name, internal_socket_addr)

        parent_stack_state = self.context_stack.parent
        assert parent_stack_state is not None, (
            "CORRUPTION: Attempting to expose subgraph socket when not editing within a subgraph context."
        )

        from edon_ui.items.factory import create_socket_item

        socket_entity = subgraph_node_entity.sockets[internal_socket_addr.name]
        # We need to get the display state from the socket item that we are exposing, so the behavior
        # is maintained.
        internal_socket_item = self.registry.socket_item_for_address(internal_socket_addr)
        new_socket_item = create_socket_item(
            socket_entity, internal_socket_item.components.display_state
        )

        parent_stack_state.registry.register_socket_item_for_node(new_socket_item)

        subgraph_item = parent_stack_state.registry.node_item_for_id(subgraph_node_entity.id)
        subgraph_item.add_socket_item(new_socket_item)

    @Slot(str, GraphicsScene)
    def handle_ui_node_redraw_request(self, node_id: str, scene: GraphicsScene) -> None:
        state = self.context_stack.context_state_for_scene(scene)
        node_item = state.registry.node_item_for_id(node_id)

        for socket_item in node_item.source_sockets + node_item.target_sockets:
            edges = state.registry.edge_items_for_socket(socket_item.address)
            # Drawing should really happen at the scene level but creating a function to
            # pipe the edge items to the scene just "because" is unnecessary.
            for edge in edges:
                edge.update_path()

    @Slot(SocketAddress, QPointF, GraphicsScene)
    def handle_ui_init_edge_drag_action(
        self, clicked_socket_addr: SocketAddress, pos: QPointF, scene: GraphicsScene
    ) -> None:
        """
        Analyzes a clicked socket and prepares the data needed for the edge drag action.
        """
        socket_item = self.registry.socket_item_for_address(clicked_socket_addr)

        # Check if we need to lift an existing edge
        # This uses the updated find_edge_items_at_socket which calls the registry.
        linked_edges = list(self.registry.edge_items_for_socket(clicked_socket_addr))

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

        # Feed the necessary context to the scene for it to start the edge drag action
        scene.edge_drag_create_action(
            EdgeDragContext(
                source_socket_addr=actual_source_addr,
                source_socket_item=actual_source_socket_item,
                is_lifted_edge=is_lifted,
                valid_targets={
                    addr: self.registry.socket_item_for_address(addr) for addr in valid_targets
                },
                invalid_targets={
                    addr: self.registry.socket_item_for_address(addr) for addr in invalid_targets
                },
            ),
            pos,
        )

    def partition_socket_drop_targets(
        self, drag_origin_socket_addr: SocketAddress
    ) -> tuple[set[SocketAddress], set[SocketAddress]]:
        """
        Determines valid drop target sockets for an edge drag operation.

        This method delegates to EntityGraph.get_connection_targets() to maintain
        proper separation of concerns between UI coordination and business logic.
        """
        valid_targets, invalid_targets = self.graph.partition_valid_link_targets(
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
        return self.registry.edge_items_for_socket(socket_addr)
