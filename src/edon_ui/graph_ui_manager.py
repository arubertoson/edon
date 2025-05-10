from typing import TYPE_CHECKING, Dict, Tuple, Type

from PySide6.QtCore import QPointF  # For position handling

from edon.graph import Graph as LogicalGraph
from edon.node import Node as EntityNode  # For type hinting and instantiation reference

from edon_ui.item.edge import EdgeItem
from edon_ui.item.node import NodeItem

if TYPE_CHECKING:
    from edon_ui.graphics_scene import GraphicsScene

    # EntityNode is already imported, but for consistency if it wasn't:
    # from edon.node import Node as EntityNode
    from edon_ui.item.socket import SocketCircleItem  # For type hinting if needed

# Define a type alias for the edge key for clarity
EdgeKeyType = Tuple[Tuple[str, str], Tuple[str, str]]


class GraphUIManager:
    """
    Manages the synchronization between the logical graph (edon.graph.Graph)
    and the UI representation (edon_ui.graphics_scene.GraphicsScene).

    It acts as the intermediary, translating UI actions into model operations
    and reflecting model changes in the UI.
    """

    def __init__(
        self,
        logical_graph: LogicalGraph,
        graphics_scene: "GraphicsScene",
        node_type_registry: dict[str, Type[EntityNode]] | None = None,
    ):
        """
        Initializes the GraphUIManager.

        Args:
            logical_graph: The instance of the logical graph (edon.graph.Graph)
                           that this manager will oversee.
            graphics_scene: The QGraphicsScene instance where UI elements will be displayed.
            node_type_registry: Optional dictionary mapping node type hints to node classes.
        """
        self.logical_graph: LogicalGraph = logical_graph
        self.graphics_scene: "GraphicsScene" = graphics_scene  # type: ignore
        self.node_map: dict[str, NodeItem] = {}
        self._node_type_registry = node_type_registry if node_type_registry is not None else {}

        # Map for logical edge identifier to EdgeItem instance
        self.edge_map: Dict[EdgeKeyType, EdgeItem] = {}

        # Connect to scene signals if scene is provided
        if hasattr(self.graphics_scene, "edge_connection_attempted"):
            self.graphics_scene.edge_connection_attempted.connect(self.handle_ui_edge_connection_attempt)
            print("GraphUIManager: Connected to GraphicsScene.edge_connection_attempted")
        else:
            print("GraphUIManager: GraphicsScene does not have 'edge_connection_attempted' signal. Cannot connect.")

        if hasattr(self.graphics_scene, "edge_disconnection_requested"):
            self.graphics_scene.edge_disconnection_requested.connect(self.handle_ui_edge_disconnection_request)
            print("GraphUIManager: Connected to GraphicsScene.edge_disconnection_requested")
        else:
            print("GraphUIManager: GraphicsScene does not have 'edge_disconnection_requested' signal. Cannot connect.")

        # The GraphicsView instance is not directly available here during __init__.
        # Connection for node_deletion_requested will be made by the main application script.
        # Similarly for edge_deletion_requested.

        print(
            f"GraphUIManager initialized with logical graph: {self.logical_graph} "
            f"and graphics scene: {self.graphics_scene}"
        )
        print(f"Node type registry: {self._node_type_registry}")
        # Call population after initialization
        # self._populate_scene_from_logical_graph() # Caller will typically do this

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

    def _populate_scene_from_logical_graph(self):
        """
        Clears the current UI scene and repopulates it with NodeItems and EdgeItems
        based on the current state of the self.logical_graph.
        """
        self._clear_scene_for_population()
        print(f"Populating UI from {len(self.logical_graph.nodes)} logical nodes.")

        # --- 1. Populate Nodes ---
        default_x, default_y = 50.0, 50.0
        spacing_x = NodeItem.MIN_WIDTH_DESIGN + 50.0
        spacing_y = NodeItem.MIN_HEIGHT_DESIGN + 50.0
        nodes_per_row = 5

        for i, (node_id, entity_node) in enumerate(self.logical_graph.nodes.items()):
            # TODO: Implement robust position management.
            # For now, use placeholder grid layout.
            # Ideally, positions would be loaded from entity_node (e.g., entity_node.ui_x)
            # or a dedicated layout store when loading a graph.
            pos_x = default_x + (i % nodes_per_row) * spacing_x
            pos_y = default_y + (i // nodes_per_row) * spacing_y

            print(f"  Creating NodeItem for '{entity_node.name}' (ID: {node_id}) at ({pos_x}, {pos_y})")

            ui_node = NodeItem(
                title=entity_node.name, x=pos_x, y=pos_y, node_entity_id=entity_node.id, entity_node_ref=entity_node
            )
            self.graphics_scene.addNode(ui_node)
            self.node_map[entity_node.id] = ui_node

        print("Node population complete.")

        # --- 2. Populate Edges ---
        print("Populating UI edges...")
        processed_connections: set[EdgeKeyType] = set()

        for entity_node_id, source_entity_node in self.logical_graph.nodes.items():
            for source_entity_socket_name, source_entity_socket in source_entity_node.output_sockets.items():
                for target_entity_socket in source_entity_socket.connections:
                    # target_entity_node_id = target_entity_socket.parent_node.id
                    # target_entity_socket_name = target_entity_socket.name

                    # Create a canonical key for the edge to avoid duplicates and for map keying
                    # Sort by node ID first, then socket name if node IDs are the same (shouldn't happen for distinct nodes)
                    # key_part1 = tuple(sorted((source_entity_node.id, source_entity_socket.name)))
                    # key_part2 = tuple(sorted((target_entity_socket.parent_node.id, target_entity_socket.name)))
                    # Ensure a consistent order for the two ends of the edge in the key
                    # edge_key_tuple_form = tuple(sorted((key_part1, key_part2)))

                    # Cast to the defined EdgeKeyType for type consistency if necessary, though tuple of tuples is fine
                    edge_key: EdgeKeyType = (  # Reconstruct for consistent ((node,sock), (node,sock)) structure for our key
                        (source_entity_node.id, source_entity_socket.name),
                        (target_entity_socket.parent_node.id, target_entity_socket.name),
                    )
                    # Use a simpler sorted tuple of strings for processed_connections to ensure A->B is same as B->A for checking processing
                    # This assumes socket names are strings. The full id,name tuple is better for map keys if needed.
                    canonical_check_key = tuple(
                        sorted(
                            [
                                f"{source_entity_node.id}::{source_entity_socket.name}",
                                f"{target_entity_socket.parent_node.id}::{target_entity_socket.name}",
                            ]
                        )
                    )

                    if canonical_check_key in processed_connections:
                        continue
                    processed_connections.add(canonical_check_key)

                    source_ui_node = self.node_map.get(source_entity_node.id)
                    target_ui_node = self.node_map.get(target_entity_socket.parent_node.id)

                    if not source_ui_node or not target_ui_node:
                        print(
                            f"  Warning: Could not find UI nodes for edge between "
                            f"{source_entity_node.id}::{source_entity_socket.name} and "
                            f"{target_entity_socket.parent_node.id}::{target_entity_socket.name}. Skipping edge."
                        )
                        continue

                    source_ui_socket_row = source_ui_node.get_ui_socket_row_by_name(
                        source_entity_socket.name, is_input=False
                    )
                    target_ui_socket_row = target_ui_node.get_ui_socket_row_by_name(
                        target_entity_socket.name, is_input=True
                    )

                    if not source_ui_socket_row or not target_ui_socket_row:
                        print(
                            f"  Warning: Could not find UI socket rows for edge between "
                            f"{source_entity_node.id}::{source_entity_socket.name} and "
                            f"{target_entity_socket.parent_node.id}::{target_entity_socket.name}. Skipping edge."
                        )
                        continue

                    source_socket_circle_item = source_ui_socket_row.socket_circle
                    target_socket_circle_item = target_ui_socket_row.socket_circle

                    if source_socket_circle_item and target_socket_circle_item:
                        print(
                            f"  Creating EdgeItem between {source_entity_node.id}::{source_entity_socket.name} "
                            f"and {target_entity_socket.parent_node.id}::{target_entity_socket.name}"
                        )

                        ui_edge = EdgeItem(source_socket_circle_item, target_socket_circle_item.scenePos())
                        ui_edge.set_target_socket(target_socket_circle_item)
                        ui_edge.settle_z_value()  # Ensure it's at the correct Z for finalized edges

                        # self.graphics_scene.addItem(ui_edge) # GraphicsScene.addItem adds to its internal node_items list.
                        # Need to ensure it handles EdgeItems correctly or bypass for edges.
                        # For now, assume EdgeItem isn't tracked like NodeItem by GraphicsScene's addItem override.
                        self.graphics_scene.addItem(ui_edge)  # Use super().addItem if scene addItem is only for nodes.
                        # Or ensure GraphicsScene.addItem allows EdgeItems without special tracking.
                        # If GraphicsScene is to track edge_items, then: self.graphics_scene.add_edge_item(ui_edge)

                        # Use the more specific edge_key for the map, not canonical_check_key
                        self.edge_map[edge_key] = ui_edge
                    else:
                        print("  Warning: Could not find UI socket circle items for edge. Skipping edge.")

        print("Scene population complete (nodes and edges).")

    def request_add_node(
        self,
        node_entity_class: type[EntityNode],
        name: str,
        ui_position: QPointF,
        entity_id_override: str | None = None,
        **node_specific_kwargs,
    ):
        """
        Handles a UI request to add a new node.
        Creates the logical entity node, adds it to the logical graph,
        then creates the corresponding UI NodeItem and adds it to the scene at ui_position.
        """
        print(f"request_add_node called for '{name}' of type {node_entity_class.__name__} at {ui_position}")

        entity_constructor_args = {"name": name}
        if entity_id_override:
            entity_constructor_args["id"] = entity_id_override
        entity_constructor_args.update(node_specific_kwargs)

        try:
            new_entity_node = node_entity_class(**entity_constructor_args)
            self.logical_graph.add_node(new_entity_node)
        except Exception as e:
            print(f"Error creating or adding logical node '{name}': {e}")
            return None

        # new_entity_node.id is now definitive. UI position is taken from parameter.
        # If EntityNode were to store ui_x, ui_y, this is where you might set them:
        # new_entity_node.ui_x = ui_position.x()
        # new_entity_node.ui_y = ui_position.y()

        try:
            new_ui_node = NodeItem(
                title=new_entity_node.name,
                x=ui_position.x(),  # Use the requested UI position for the new node
                y=ui_position.y(),
                node_entity_id=new_entity_node.id,
                entity_node_ref=new_entity_node,
            )
            self.graphics_scene.addNode(new_ui_node)
            self.node_map[new_entity_node.id] = new_ui_node
            print(
                f"Successfully created and added node: {new_entity_node.name} (Entity ID: {new_entity_node.id}, UI: {new_ui_node})"
            )
            return new_ui_node
        except Exception as e:
            print(f"Error creating UI node for logical node '{new_entity_node.name}': {e}")
            return None

    def request_create_edge(
        self, source_ui_socket: "SocketCircleItem", target_ui_socket: "SocketCircleItem"
    ) -> EdgeItem | None:
        """
        Handles a request to create a new edge, typically from a UI interaction.
        Attempts to connect the logical sockets first. If successful, creates and
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

        print(
            f"GraphUIManager: Requesting to create edge between logical sockets: "
            f"({source_node_id}::{source_socket_name}) -> ({target_node_id}::{target_socket_name})"
        )

        # Check if this connection already exists in the edge_map
        edge_key: EdgeKeyType = ((source_node_id, source_socket_name), (target_node_id, target_socket_name))
        if edge_key in self.edge_map:
            print(
                f"  Connection already exists between ({source_node_id}::{source_socket_name}) and "
                f"({target_node_id}::{target_socket_name}). No new connection created."
            )
            return None

        # Attempt to connect in the logical graph
        connection_success, reason = self.logical_graph.connect_sockets(
            (source_node_id, source_socket_name), (target_node_id, target_socket_name)
        )

        if connection_success:
            print("  Logical connection successful. Creating UI EdgeItem.")
            # Create the UI EdgeItem
            # Ensure source_ui_socket and target_ui_socket are valid QGraphicsItem instances
            # The EdgeItem constructor expects the target position initially, then sets the target socket.
            new_edge_item = EdgeItem(source_ui_socket, target_ui_socket.scenePos())
            new_edge_item.set_target_socket(target_ui_socket)
            new_edge_item.settle_z_value()  # Set to normal Z value for finalized edges

            self.graphics_scene.addEdge(new_edge_item)

            # Store in edge_map. Construct the key similar to _populate_scene_from_logical_graph
            self.edge_map[edge_key] = new_edge_item
            print(f"  UI EdgeItem created and added to scene/map for edge: {edge_key}")
            return new_edge_item
        else:
            print(
                f"  Logical connection FAILED between ({source_node_id}::{source_socket_name}) and ({target_node_id}::{target_socket_name}). Reason: {reason}. No UI edge created."
            )
            # Optionally, provide user feedback based on the reason
            # For example, if reason == SocketConnectionErrorReason.TYPE_MISMATCH:
            #   self.graphics_scene.post_status_message("Connection failed: Incompatible types.")
            return None

    def handle_ui_edge_connection_attempt(
        self, source_ui_socket: "SocketCircleItem", target_ui_socket: "SocketCircleItem"
    ):
        """
        Slot to handle the edge_connection_attempted signal from the GraphicsScene.
        If both sockets are None, this indicates a request to disconnect the currently lifted edge.
        """
        # Handle edge disconnection request (when lifting an edge)
        if source_ui_socket is None and target_ui_socket is None:
            print("GraphUIManager: Received edge disconnection request (edge lift)")
            return

        print(
            f"GraphUIManager: Received handle_ui_edge_connection_attempt from "
            f"{source_ui_socket.parent_node_entity_id}::{source_ui_socket.socket_entity_name} to "
            f"{target_ui_socket.parent_node_entity_id}::{target_ui_socket.socket_entity_name}"
        )
        self.request_create_edge(source_ui_socket, target_ui_socket)

    def request_remove_node(self, logical_node_id: str):
        """
        Handles a request to remove a node (logical and UI) and its connected edges.
        """
        print(f"GraphUIManager: Requesting to remove node with ID: {logical_node_id}")

        # 1. Remove node from the logical graph
        # This should also handle disconnecting its logical sockets.
        self.logical_graph.remove_node(logical_node_id)
        print(f"  Node {logical_node_id} removed from logical graph.")

        # 2. Remove the UI NodeItem from the scene and our map
        ui_node_to_remove = self.node_map.pop(logical_node_id, None)
        if ui_node_to_remove:
            self.graphics_scene.removeNode(ui_node_to_remove)
            print(f"  UI NodeItem for {logical_node_id} removed from graphics scene and node_map.")
        else:
            print(f"  Warning: No UI NodeItem found in node_map for ID {logical_node_id}.")

        # 3. Clean up EdgeItems from the edge_map connected to this node
        # The actual EdgeItem objects should have been removed from the scene by GraphicsScene.removeItem(ui_node_to_remove)
        # if its logic is comprehensive for handling connected edges upon node removal.
        # Here, we primarily clean our edge_map.
        edges_to_remove_from_map: list[EdgeKeyType] = []
        for edge_key, _ in self.edge_map.items():
            # edge_key is ((source_node_id, source_socket_name), (target_node_id, target_socket_name))
            if edge_key[0][0] == logical_node_id or edge_key[1][0] == logical_node_id:
                edges_to_remove_from_map.append(edge_key)

        for edge_key in edges_to_remove_from_map:
            removed_edge_item = self.edge_map.pop(edge_key, None)
            if removed_edge_item:
                print(f"  Edge {edge_key} removed from edge_map.")
                # The EdgeItem itself should already be removed from the scene by GraphicsScene.removeItem(NodeItem)
                # If GraphicsScene.removeItem(NodeItem) doesn't also call removeItem on the EdgeItem itself,
                # we might need to do it here: self.graphics_scene.removeItem(removed_edge_item)
                # However, GraphicsScene.removeItem for a NodeItem already iterates its self.edge_items and removes them.
            else:
                print(
                    f"  Warning: Edge {edge_key} was in edges_to_remove_from_map but not found in edge_map during pop."
                )

        print(f"GraphUIManager: Node removal process for {logical_node_id} complete.")

    def request_remove_edge(self, ui_edge_item: EdgeItem):
        """
        Handles a request to remove a single edge (logical and UI).

        Args:
            ui_edge_item: The EdgeItem instance to remove.
        """
        if not ui_edge_item or not ui_edge_item.source_socket_item or not ui_edge_item.target_socket_item:
            print("GraphUIManager: Invalid EdgeItem provided to request_remove_edge. Cannot proceed.")
            return

        source_node_id = ui_edge_item.source_socket_item.parent_node_entity_id
        source_socket_name = ui_edge_item.source_socket_item.socket_entity_name
        target_node_id = ui_edge_item.target_socket_item.parent_node_entity_id
        target_socket_name = ui_edge_item.target_socket_item.socket_entity_name

        edge_repr = f"({source_node_id}::{source_socket_name}) -> ({target_node_id}::{target_socket_name})"
        print(f"GraphUIManager: Requesting to remove edge: {edge_repr}")

        # 1. Disconnect in the logical graph
        disconnection_success, reason = self.logical_graph.disconnect_sockets(
            (source_node_id, source_socket_name), (target_node_id, target_socket_name)
        )

        if disconnection_success:
            print(f"  Logical disconnection successful for {edge_repr}.")
        else:
            # Log failure but proceed to remove UI element as user requested its deletion directly.
            print(
                f"  Warning: Logical disconnection FAILED for {edge_repr}. Reason: {reason}. Proceeding with UI removal."
            )

        # 2. Remove the UI EdgeItem from the scene
        # GraphicsScene.removeItem will also remove it from its internal edge_items list.
        self.graphics_scene.removeEdge(ui_edge_item)
        print(f"  UI EdgeItem for {edge_repr} removed from graphics scene.")

        # 3. Remove the edge from our edge_map
        edge_key_to_remove: EdgeKeyType | None = None
        # Construct the key as it would have been stored to find it.
        # Note: The order in the key might be canonicalized (e.g., sorted) during storage.
        # For now, assume direct ((source_id, source_name), (target_id, target_name)) from populate/create.
        # If _populate_scene_from_logical_graph canonicalizes keys, this needs to match.
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
                print(f"  Edge {edge_key_to_remove} removed from edge_map.")
            else:
                # Should not happen if edge_key_to_remove was found and valid
                print(f"  Warning: Edge key {edge_key_to_remove} found but pop failed from edge_map.")
        else:
            print(f"  Warning: Could not find edge {edge_repr} (instance: {ui_edge_item}) in edge_map to remove.")

        print(f"GraphUIManager: Edge removal process for {edge_repr} complete.")

    def handle_ui_request_add_node(self, scene_pos: QPointF, node_type_hint: str):
        """
        Slot to handle the new_node_requested_at_scene_pos signal from the UI (e.g., GraphicsView).
        It determines the logical node class to create based on the hint and then
        calls the main request_add_node method.
        """
        print(f"GraphUIManager: Received handle_ui_request_add_node for type '{node_type_hint}' at {scene_pos}")

        node_class_to_create = self._node_type_registry.get(node_type_hint)

        if not node_class_to_create:
            print(f"  ERROR: Node type hint '{node_type_hint}' not found in registry. Cannot create node.")
            return

        type_count = sum(1 for node in self.logical_graph.nodes.values() if isinstance(node, node_class_to_create))
        node_name = f"{node_class_to_create.__name__} {type_count + 1}"

        self.request_add_node(
            node_entity_class=node_class_to_create,
            name=node_name,
            ui_position=scene_pos,
        )

    def handle_ui_node_deletion_request(self, node_entity_ids: list[str]):
        """
        Slot to handle the node_deletion_requested signal from the GraphicsView.
        """
        print(f"GraphUIManager: Received handle_ui_node_deletion_request for IDs: {node_entity_ids}")
        for node_id in node_entity_ids:
            self.request_remove_node(node_id)

    def handle_ui_edge_deletion_request(self, edge_items: list[EdgeItem]):
        """
        Slot to handle the edge_deletion_requested signal from the GraphicsView.
        """
        print(f"GraphUIManager: Received handle_ui_edge_deletion_request for {len(edge_items)} edge(s).")
        for edge_item in edge_items:
            self.request_remove_edge(edge_item)

    def handle_ui_edge_disconnection_request(self, edge_item: EdgeItem):
        """
        Slot to handle the edge_disconnection_requested signal from the GraphicsScene.
        This is called when an edge is lifted for reconnection.
        """
        if not edge_item or not edge_item.source_socket_item or not edge_item.target_socket_item:
            print("GraphUIManager: Invalid EdgeItem provided to handle_ui_edge_disconnection_request. Cannot proceed.")
            return

        source_node_id = edge_item.source_socket_item.parent_node_entity_id
        source_socket_name = edge_item.source_socket_item.socket_entity_name
        target_node_id = edge_item.target_socket_item.parent_node_entity_id
        target_socket_name = edge_item.target_socket_item.socket_entity_name

        print(
            f"GraphUIManager: Disconnecting edge between logical sockets: "
            f"({source_node_id}::{source_socket_name}) -> ({target_node_id}::{target_socket_name})"
        )

        # Disconnect in the logical graph
        disconnection_success, reason = self.logical_graph.disconnect_sockets(
            (source_node_id, source_socket_name), (target_node_id, target_socket_name)
        )

        if disconnection_success:
            print("  Logical disconnection successful.")
            # Remove from edge_map
            edge_key = ((source_node_id, source_socket_name), (target_node_id, target_socket_name))
            self.edge_map.pop(edge_key, None)
        else:
            print(f"  Logical disconnection FAILED. Reason: {reason}")
