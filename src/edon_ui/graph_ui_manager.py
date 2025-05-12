from typing import TYPE_CHECKING, Type, TypeAlias

from loguru import logger
from PySide6.QtCore import QPointF  # For position handling
from PySide6.QtWidgets import QGraphicsTextItem

from edon.graph import EntityGraph
from edon.node import EntityNode
from edon_ui.item.edge import EdgeItem
from edon_ui.item.node import NodeItem
from edon_ui.item.socket_widgets import IntegerSocketWidget, FloatSocketWidget, StringSocketWidget
from edon_ui.item.socket import SocketRowItem
from edon_ui import theme
from edon_ui.item.factory import create_node_item, create_edge_item

if TYPE_CHECKING:
    from edon_ui.graphics_scene import GraphicsScene

    # EntityNode is already imported, but for consistency if it wasn't:
    # from edon.node import Node as EntityNode
    from edon_ui.item.socket import SocketCircleItem  # For type hinting if needed

# Define a type alias for the edge key for clarity
EdgeKeyType = tuple[tuple[str, str], tuple[str, str]]
SocketRowMap: TypeAlias = dict[tuple[str, str, bool], SocketRowItem]


class GraphUIManager:
    """
    Manages the synchronization between the entity graph (edon.graph.Graph)
    and the UI representation (edon_ui.graphics_scene.GraphicsScene).

    It acts as the intermediary, translating UI actions into model operations
    and reflecting model changes in the UI.
    """

    def __init__(
        self,
        entity_graph: EntityGraph,
        graphics_scene: "GraphicsScene",
        node_type_registry: dict[str, Type[EntityNode]] | None = None,
    ):
        """
        Initializes the GraphUIManager.

        Args:
            entity_graph: The instance of the entity graph (edon.graph.Graph)
                           that this manager will oversee.
            graphics_scene: The QGraphicsScene instance where UI elements will be displayed.
            node_type_registry: Optional dictionary mapping node type hints to node classes.
        """
        self.entity_graph: EntityGraph = entity_graph
        self.graphics_scene: "GraphicsScene" = graphics_scene  # type: ignore
        self.node_map: dict[str, NodeItem] = {}
        self._node_type_registry = node_type_registry if node_type_registry is not None else {}

        # Map for edge entities to EdgeItem instance
        self.edge_map: dict[EdgeKeyType, EdgeItem] = {}

        # Add this to your __init__
        self.socket_row_map: SocketRowMap = {}
        # Key: (node_id, socket_name, is_input)

        logger.info(
            f"GraphUIManager initialized with entity graph: {self.entity_graph} "
            f"and graphics scene: {self.graphics_scene}"
        )
        logger.debug(f"Node type registry: {self._node_type_registry}")
        # Call population after initialization
        # self._populate_scene_from_entity_graph() # Caller will typically do this

    def _clear_scene_for_population(self):
        """Helper to clear the scene before populating it from the model."""
        # Assuming graphics_scene.clear() is the standard Qt method that removes all items.
        # If GraphicsScene has custom lists like self.node_items, self.edge_items,
        # it should have its own comprehensive clear method that also clears those lists.
        # For now, we rely on the fact that addItem in GraphicsScene seems to manage its own list.

        # Let's iterate and remove items that are NodeItem or EdgeItem to be safe
        # and to allow GraphicsScene's removeItem logic to run (e.g. for disconnecting signals)
        items_to_remove = []
        for item in self.graphics_scene.items():
            if isinstance(item, (NodeItem, EdgeItem)):
                items_to_remove.append(item)

        for item in items_to_remove:
            self.graphics_scene.removeItem(item)  # Use scene's removeItem

        self.node_map.clear()
        self.edge_map.clear()  # Clear edge map as well

    def _register_node_maps(self, entity_node: EntityNode, ui_node: NodeItem):
        node_id = entity_node.id
        if node_id not in self.entity_graph.nodes:
            self.entity_graph.add_node(entity_node)

        self.graphics_scene.addNode(ui_node)
        self.node_map[node_id] = ui_node

        for row in ui_node._input_sockets:
            self.socket_row_map[(node_id, row.socket_entity_name, True)] = row
        for row in ui_node._output_sockets:
            self.socket_row_map[(node_id, row.socket_entity_name, False)] = row

    def _register_edge_map(self, edge_key: EdgeKeyType, edge_item: EdgeItem):
        self.graphics_scene.addEdge(edge_item)
        self.edge_map[edge_key] = edge_item

    def _populate_nodes(self):
        """Populates NodeItems in the scene based on the entity_graph."""
        logger.info(f"Populating UI with {len(self.entity_graph.nodes)} entity nodes.")
        default_x, default_y = 50.0, 50.0
        spacing_x = theme.NODE_MIN_WIDTH + 50.0
        spacing_y = theme.NODE_MIN_HEIGHT + 50.0
        nodes_per_row = 5

        for i, (node_id, entity_node) in enumerate(self.entity_graph.nodes.items()):
            pos_x = default_x + (i % nodes_per_row) * spacing_x
            pos_y = default_y + (i // nodes_per_row) * spacing_y
            logger.debug(f"  Creating NodeItem for '{entity_node.name}' (ID: {node_id}) at ({pos_x}, {pos_y})")

            ui_node = create_node_item(entity_node, pos_x, pos_y)
            self._register_node_maps(entity_node, ui_node)

        logger.debug("Node population complete.")

    def _populate_edges(self):
        """Populates EdgeItems in the scene based on the entity_graph connections."""
        logger.debug("Populating UI edges...")
        processed_connections: set[EdgeKeyType] = set()

        for _, source_entity_node in self.entity_graph.nodes.items():
            for _, source_entity_socket in source_entity_node.output_sockets.items():
                for target_entity_socket in source_entity_socket.connections:
                    edge_key: EdgeKeyType = (
                        (source_entity_node.id, source_entity_socket.name),
                        (target_entity_socket.parent_node.id, target_entity_socket.name),
                    )
                    if edge_key in processed_connections:
                        continue
                    processed_connections.add(edge_key)

                    source_ui_socket_row = self.socket_row_map.get(
                        (source_entity_node.id, source_entity_socket.name, False)
                    )
                    target_ui_socket_row = self.socket_row_map.get(
                        (target_entity_socket.parent_node.id, target_entity_socket.name, True)
                    )

                    logger.debug(
                        f"  Creating EdgeItem: {source_entity_node.id}::{source_entity_socket.name} -> "
                        f"{target_entity_socket.parent_node.id}::{target_entity_socket.name}"
                    )
                    ui_edge = create_edge_item(source_ui_socket_row.socket_circle, target_ui_socket_row.socket_circle)
                    self._register_edge_map(edge_key, ui_edge)

        logger.debug("Edge population complete.")

    def _populate_scene_from_entity_graph(self):
        """
        Clears the current UI scene and repopulates it with NodeItems and EdgeItems
        based on the current state of the self.entity_graph.
        """
        self._clear_scene_for_population()
        self._populate_nodes()
        self._populate_edges()
        logger.info("Scene population complete (nodes and edges).")

    def request_add_node(
        self,
        node_entity_class: type[EntityNode],
        scene_position: QPointF,
        **node_specific_kwargs,
    ) -> NodeItem | None:
        """
        Handles a UI request to add a new node.
        Creates the entity node, adds it to the entity graph,
        then creates the corresponding UI NodeItem and adds it to the scene at scene_position.
        Ensures no dangling entity node is left if UI creation fails.
        """
        node_type = node_entity_class.__name__
        logger.info(f"request_add_node of type {node_type} at {scene_position}")

        try:
            new_entity_node = node_entity_class(**node_specific_kwargs)
            new_ui_node = create_node_item(
                new_entity_node, scene_position.x(), scene_position.y(), self.socket_row_map
            )
            self._register_node_maps(new_entity_node, new_ui_node)

            logger.info(
                f"Successfully created and added node: {new_entity_node.name} (Entity ID: {new_entity_node.id}, UI: {new_ui_node})"
            )
            return new_ui_node
        except Exception as e:
            logger.error(f"Error creating or adding node '{node_type}': {e}")
            return None

    def request_add_edge(
        self, source_ui_socket: "SocketCircleItem", target_ui_socket: "SocketCircleItem"
    ) -> EdgeItem | None:
        """
        Handles a request to create a new edge, typically from a UI interaction.
        Attempts to connect the entity sockets first. If successful, creates and
        adds the UI EdgeItem to the scene and internal tracking.

        Args:
            source_ui_socket: The SocketCircleItem from which the edge originates.
            target_ui_socket: The SocketCircleItem to which the edge connects.

        Returns:
            The created EdgeItem if successful, otherwise None.
        """
        source_node_id = source_ui_socket.parent_node_entity_id
        source_socket_name = source_ui_socket.socket_entity_name
        target_node_id = target_ui_socket.parent_node_entity_id
        target_socket_name = target_ui_socket.socket_entity_name

        logger.info(
            f"GraphUIManager: Requesting to create edge between entity sockets: "
            f"({source_node_id}::{source_socket_name}) -> ({target_node_id}::{target_socket_name})"
        )

        # Check if this connection already exists in the edge_map
        edge_key: EdgeKeyType = ((source_node_id, source_socket_name), (target_node_id, target_socket_name))
        if edge_key in self.edge_map:
            logger.debug(
                f"  Connection already exists between ({source_node_id}::{source_socket_name}) and "
                f"({target_node_id}::{target_socket_name}). No new connection created."
            )
            return None

        # Attempt to connect in the entity graph
        connection_success, reason = self.entity_graph.connect_sockets(
            (source_node_id, source_socket_name), (target_node_id, target_socket_name)
        )

        if connection_success:
            logger.debug("  Entity connection successful. Creating UI EdgeItem.")

            # XXX:
            # node = self.entity_graph.get_node(target_node_id)
            # logger.debug(f"!!!  Node {target_node_id} input sockets: {node.input_sockets[target_socket_name].connections}")

            # Create the UI EdgeItem
            # Ensure source_ui_socket and target_ui_socket are valid QGraphicsItem instances
            # The EdgeItem constructor expects the target position initially, then sets the target socket.
            new_edge_item = EdgeItem(source_ui_socket, target_ui_socket.scenePos())
            new_edge_item.set_target_socket(target_ui_socket)
            new_edge_item.settle_z_value()  # Set to normal Z value for finalized edges

            self.graphics_scene.addEdge(new_edge_item)

            # Store in edge_map. Construct the key similar to _populate_scene_from_entity_graph
            self.edge_map[edge_key] = new_edge_item
            logger.debug(f"  UI EdgeItem created and added to scene/map for edge: {edge_key}")
            return new_edge_item
        else:
            logger.warning(
                f"  Entity connection FAILED between ({source_node_id}::{source_socket_name}) and ({target_node_id}::{target_socket_name}). Reason: {reason}. No UI edge created."
            )
            # Optionally, provide user feedback based on the reason
            # For example, if reason == SocketConnectionErrorReason.TYPE_MISMATCH:
            #   self.graphics_scene.post_status_message("Connection failed: Incompatible types.")
            return None

    def request_remove_node(self, entity_node_id: str):
        """
        Handles a request to remove a node (entity and UI) and its connected edges.
        """
        logger.info(f"GraphUIManager: Requesting to remove node with ID: {entity_node_id}")

        # 1. Remove node from the entity graph
        # This should also handle disconnecting its entity sockets.
        self.entity_graph.remove_node(entity_node_id)
        logger.debug(f"  Node {entity_node_id} removed from entity graph.")

        # 2. Remove the UI NodeItem from the scene and our map
        ui_node_to_remove = self.node_map.pop(entity_node_id, None)
        if ui_node_to_remove:
            self.graphics_scene.removeNode(ui_node_to_remove)
            logger.debug(f"  UI NodeItem for {entity_node_id} removed from graphics scene and node_map.")
        else:
            logger.warning(f"  No UI NodeItem found in node_map for ID {entity_node_id}.")

        # 3. Clean up EdgeItems from the edge_map connected to this node
        # The actual EdgeItem objects should have been removed from the scene by GraphicsScene.removeItem(ui_node_to_remove)
        # if its logic is comprehensive for handling connected edges upon node removal.
        # Here, we primarily clean our edge_map.
        edges_to_remove_from_map: list[EdgeKeyType] = []
        for edge_key, _ in self.edge_map.items():
            # edge_key is ((source_node_id, source_socket_name), (target_node_id, target_socket_name))
            if edge_key[0][0] == entity_node_id or edge_key[1][0] == entity_node_id:
                edges_to_remove_from_map.append(edge_key)

        for edge_key in edges_to_remove_from_map:
            removed_edge_item = self.edge_map.pop(edge_key, None)
            if removed_edge_item:
                logger.debug(f"  Edge {edge_key} removed from edge_map.")
                # The EdgeItem itself should already be removed from the scene by GraphicsScene.removeItem(NodeItem)
                # If GraphicsScene.removeItem(NodeItem) doesn't also call removeItem on the EdgeItem itself,
                # we might need to do it here: self.graphics_scene.removeItem(removed_edge_item)
                # However, GraphicsScene.removeItem for a NodeItem already iterates its self.edge_items and removes them.
            else:
                logger.warning(
                    f"  Edge {edge_key} was in edges_to_remove_from_map but not found in edge_map during pop."
                )

        logger.info(f"GraphUIManager: Node removal process for {entity_node_id} complete.")

    def request_remove_edge(self, ui_edge_item: EdgeItem):
        """
        Handles a request to remove a single edge (entity and UI).

        Args:
            ui_edge_item: The EdgeItem instance to remove.
        """
        if not ui_edge_item or not ui_edge_item.source_socket_item or not ui_edge_item.target_socket_item:
            logger.warning("GraphUIManager: Invalid EdgeItem provided to request_remove_edge. Cannot proceed.")
            return

        source_node_id = ui_edge_item.source_socket_item.parent_node_entity_id
        source_socket_name = ui_edge_item.source_socket_item.socket_entity_name
        target_node_id = ui_edge_item.target_socket_item.parent_node_entity_id
        target_socket_name = ui_edge_item.target_socket_item.socket_entity_name

        edge_repr = f"({source_node_id}::{source_socket_name}) -> ({target_node_id}::{target_socket_name})"
        logger.info(f"GraphUIManager: Requesting to remove edge: {edge_repr}")

        # 1. Disconnect in the entity graph
        disconnection_success, reason = self.entity_graph.disconnect_sockets(
            (source_node_id, source_socket_name), (target_node_id, target_socket_name)
        )

        if disconnection_success:
            logger.debug(f"  Entity disconnection successful for {edge_repr}.")
        else:
            # Log failure but proceed to remove UI element as user requested its deletion directly.
            logger.warning(
                f"  Entity disconnection FAILED for {edge_repr}. Reason: {reason}. Proceeding with UI removal."
            )

        # 2. Remove the UI EdgeItem from the scene
        # GraphicsScene.removeItem will also remove it from its internal edge_items list.
        self.graphics_scene.removeEdge(ui_edge_item)
        logger.debug(f"  UI EdgeItem for {edge_repr} removed from graphics scene.")

        # 3. Remove the edge from our edge_map
        edge_key_to_remove: EdgeKeyType | None = None
        # Construct the key as it would have been stored to find it.
        # Note: The order in the key might be canonicalized (e.g., sorted) during storage.
        # For now, assume direct ((source_id, source_name), (target_id, target_name)) from populate/create.
        # If _populate_scene_from_entity_graph canonicalizes keys, this needs to match.
        # Our current key is: ((source_node.id, source_socket.name), (target_node.id, target_socket.name))
        # This matches how it's added in request_create_edge.

        # We need to find the key that maps to this specific ui_edge_item instance, or reconstruct it.
        # Reconstructing is safer if there's no ambiguity.
        prospective_key = ((source_node_id, source_socket_name), (target_node_id, target_socket_name))

        if prospective_key in self.edge_map and self.edge_map[prospective_key] == ui_edge_item:
            edge_key_to_remove = prospective_key
        else:
            # Fallback: Iterate if direct key lookup fails (e.g. due to key canonicalization issues)
            for key, val in self.edge_map.items():
                if val == ui_edge_item:
                    edge_key_to_remove = key
                    break

        if edge_key_to_remove:
            removed_item = self.edge_map.pop(edge_key_to_remove, None)
            if removed_item:
                logger.debug(f"  Edge {edge_key_to_remove} removed from edge_map.")
            else:
                # Should not happen if edge_key_to_remove was found and valid
                logger.warning(f"  Edge key {edge_key_to_remove} found but pop failed from edge_map.")
        else:
            logger.warning(f"  Could not find edge {edge_repr} (instance: {ui_edge_item}) in edge_map to remove.")

        logger.info(f"GraphUIManager: Edge removal process for {edge_repr} complete.")

    def request_edge_drop_targets(self, source_socket_ui_item: "SocketCircleItem") -> set:
        """
        Return a set of (node_id, socket_name) tuples that are valid drop targets for the given source_socket_ui_item.
        The source_socket_ui_item is the UI representation of the socket being dragged.
        Only input sockets are considered as potential drop targets here, assuming a standard drag from an output.
        If reverse drag (input to output) is fully supported, this logic might need adjustment for the target iteration.
        """
        valid_targets = set()

        source_node_id = source_socket_ui_item.parent_node_entity_id
        source_entity_node = self.entity_graph.get_node(source_node_id)

        if not source_entity_node:
            logger.warning(f"Warning: Could not find entity node for source_socket_ui_item (ID: {source_node_id})")
            return valid_targets

        # Determine if the source_socket_ui_item represents an input or output for entity lookup
        if source_socket_ui_item.is_input:  # This implies a reverse drag scenario for the source
            # If dragging from an input, we'd be looking for output targets. This function currently targets inputs.
            # For now, let's assume standard drag: source_socket_ui_item is an output.
            # If it IS an input, it cannot be a source for connecting to other inputs.
            # This part needs to be robust if reverse drags are intended to be fully supported by this function.
            # For now, if source is input, it won't find valid targets in the loop below.
            entity_source_socket = source_entity_node.input_sockets.get(source_socket_ui_item.socket_entity_name)
            socket_iter = "output_sockets"
        else:  # Standard drag: source_socket_ui_item is an output
            entity_source_socket = source_entity_node.output_sockets.get(source_socket_ui_item.socket_entity_name)
            socket_iter = "input_sockets"

        if not entity_source_socket:
            logger.warning(
                f"Warning: Could not find entity socket for source_socket_ui_item (Node ID: {source_node_id}, Socket: {source_socket_ui_item.socket_entity_name})"
            )
            return valid_targets

        # Iterate over all potential entity target sockets (which must be inputs for a standard drag)
        for target_node in self.entity_graph.nodes.values():
            for target_socket_name, entity_target_input_socket in getattr(target_node, socket_iter).items():
                can_connect, _ = entity_target_input_socket.can_connect_to(entity_source_socket)

                logger.debug(
                    f"  Checking if {entity_target_input_socket.parent_node.id} can connect to {entity_source_socket.parent_node.id}"
                )
                if can_connect:
                    would_cycle = self.entity_graph._has_path(
                        entity_target_input_socket.parent_node.id, entity_source_socket.parent_node.id
                    )
                    if not would_cycle:
                        valid_targets.add((target_node.id, target_socket_name))
        return valid_targets

    def handle_ui_edge_connection_attempt(
        self, source_ui_socket: "SocketCircleItem", target_ui_socket: "SocketCircleItem"
    ):
        """
        Slot to handle the edge_connection_attempted signal from the GraphicsScene.
        If both sockets are None, this indicates a request to disconnect the currently lifted edge.
        """
        logger.debug(
            f"GraphUIManager: Received handle_ui_edge_connection_attempt from "
            f"{source_ui_socket.parent_node_entity_id}::{source_ui_socket.socket_entity_name} to "
            f"{target_ui_socket.parent_node_entity_id}::{target_ui_socket.socket_entity_name}"
        )

        # we need to check if the edge that we are trying to create already exists.
        edge_key = (
            (source_ui_socket.parent_node_entity_id, source_ui_socket.socket_entity_name),
            (target_ui_socket.parent_node_entity_id, target_ui_socket.socket_entity_name),
        )
        if edge_key in self.edge_map:
            logger.warning(f"Edge {edge_key} already exists. Ignoring connection attempt.")
            return

        # If the target socket already has an edge, we remove it, input nodes can only have one edge
        # and we decided on behavior that the new edge will replace the old one.
        if target_ui_socket.connected_edges:
            logger.warning(
                f"Target socket {target_ui_socket.socket_entity_name} already has edges. Ignoring connection attempt."
            )
            edge_to_remove = next(iter(target_ui_socket.connected_edges))
            self.request_remove_edge(edge_to_remove)

        self.request_add_edge(source_ui_socket, target_ui_socket)

    def handle_ui_node_creation_request(self, node_type_hint: str, scene_pos: QPointF):
        """
        Slot to handle the new_node_requested_at_scene_pos signal from the UI (e.g., GraphicsView).
        It determines the entity node class to create based on the hint and then
        calls the main request_add_node method.
        """
        logger.info(
            f"GraphUIManager: Received handle_ui_node_creation_request for type '{node_type_hint}' at {scene_pos}"
        )

        node_class_to_create = self._node_type_registry.get(node_type_hint)

        if not node_class_to_create:
            logger.error(f"  ERROR: Node type hint '{node_type_hint}' not found in registry. Cannot create node.")
            return

        type_count = sum(1 for node in self.entity_graph.nodes.values() if isinstance(node, node_class_to_create))
        node_name = f"{node_class_to_create.__name__} {type_count + 1}"

        self.request_add_node(
            node_entity_class=node_class_to_create,
            name=node_name,
            scene_position=scene_pos,
        )

    def handle_ui_node_deletion_request(self, entity_node_ids: list[str]):
        """
        Slot to handle the node_deletion_requested signal from the GraphicsView.
        """
        logger.info(f"GraphUIManager: Received handle_ui_node_deletion_request for IDs: {entity_node_ids}")
        for node_id in entity_node_ids:
            self.request_remove_node(node_id)

    def handle_ui_edge_deletion_request(self, edge_items: list[EdgeItem]):
        """
        Slot to handle the edge_deletion_requested signal from the GraphicsView.
        """
        logger.info(f"GraphUIManager: Received handle_ui_edge_deletion_request for {len(edge_items)} edge(s).")
        for edge_item in edge_items:
            self.request_remove_edge(edge_item)

    def handle_ui_edge_disconnection_request(self, edge_item: EdgeItem):
        """
        Handles a request to disconnect an edge between two sockets.
        This is called when an edge is lifted for reconnection during drag operations.
        """
        if not edge_item or not edge_item.source_socket_item or not edge_item.target_socket_item:
            logger.warning(
                "GraphUIManager: Invalid EdgeItem provided to handle_ui_edge_disconnection_request. Cannot proceed."
            )
            return

        source_node_id = edge_item.source_socket_item.parent_node_entity_id
        source_socket_name = edge_item.source_socket_item.socket_entity_name
        target_node_id = edge_item.target_socket_item.parent_node_entity_id
        target_socket_name = edge_item.target_socket_item.socket_entity_name

        logger.info(
            f"GraphUIManager: Disconnecting edge between entity sockets: "
            f"({source_node_id}::{source_socket_name}) -> ({target_node_id}::{target_socket_name})"
        )

        disconnection_success, reason = self.entity_graph.disconnect_sockets(
            (source_node_id, source_socket_name), (target_node_id, target_socket_name)
        )

        if disconnection_success:
            logger.debug("Entity disconnection successful.")
            edge_key = ((source_node_id, source_socket_name), (target_node_id, target_socket_name))
            self.edge_map.pop(edge_key, None)
        else:
            logger.warning(f"Entity disconnection FAILED. Reason: {reason}")
