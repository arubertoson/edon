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

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Type, TypeAlias

from loguru import logger
from PySide6.QtCore import QPointF

from edon.graph import EdgeKey, EntityGraph, SocketAddress
from edon.node import EntityNode
from edon_ui import theme
from edon_ui.items.edge import EdgeItem
from edon_ui.items.factory import create_edge_item, create_node_item
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketRowItem

if TYPE_CHECKING:
    from edon_ui.views.scene import GraphicsScene
    from edon_ui.items.socket import SocketCircleItem


@dataclass(frozen=True)
class SocketRowAddress(SocketAddress):
    """Uniquely identifies a UI SocketRowItem, extending SocketAddress with direction.

    A SocketRowItem is a UI representation that groups sockets (often a single socket).
    This address helps locate that specific UI row.
    """

    is_target: bool


NodeItemMap: TypeAlias = MutableMapping[str, NodeItem]
SocketItemMap: TypeAlias = MutableMapping[SocketRowAddress, SocketRowItem]
EdgeItemMap: TypeAlias = MutableMapping[EdgeKey, EdgeItem]


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
        graphics_scene: "GraphicsScene",
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
        self.graphics_scene: "GraphicsScene" = graphics_scene
        self._node_type_registry: dict[str, Type[EntityNode]] = (
            node_type_registry if node_type_registry is not None else {}
        )

        # Maps for entity graph to UI items
        self.node_map: NodeItemMap = {}
        self.edge_map: EdgeItemMap = {}
        self.socket_row_map: SocketItemMap = {}

        logger.info(
            f"GraphController initialized with entity graph: {self.entity_graph} "
            f"and graphics scene: {self.graphics_scene}"
        )
        logger.debug(f"Node type registry: {self._node_type_registry}")

    def request_add_node(
        self,
        node_entity_class: type[EntityNode],
        scene_position: QPointF,
        **node_specific_kwargs,
    ) -> NodeItem | None:
        """Processes a request to add a new node to both the data model and the UI.

        This method orchestrates the creation of a new node by:
        1. Instantiating the core `EntityNode` based on the provided class and arguments.
        2. Creating its corresponding `NodeItem` for the UI, positioning it at the
           specified scene coordinates.
        3. Registering both the entity and UI node representations with the controller
           and the underlying `EntityGraph` and `GraphicsScene`.

        If any step in the creation or registration process fails, an error is logged,
        and the method returns `None`. Callers should check the return value.

        Args:
            node_entity_class: The class of the `EntityNode` to instantiate (e.g., `MyCustomNode`).
            scene_position: The `QPointF` coordinates where the top-left of the new
                              UI node should be placed in the scene.
            **node_specific_kwargs: Additional keyword arguments to be passed to the
                                     constructor of the `node_entity_class`.

        Returns:
            The created `NodeItem` if successful, otherwise `None`.
        """
        node_type = node_entity_class.__name__
        logger.info(f"request_add_node of type {node_type} at {scene_position}")

        try:
            new_entity_node = node_entity_class(**node_specific_kwargs)
            # XXX: Review if create_node_item factory truly needs the controller's entire socket_row_map.
            # This argument was intentionally kept as per user's previous edit.
            # Typically, a factory creates internal components, and the controller would register them later.
            new_ui_node = create_node_item(
                new_entity_node, scene_position.x(), scene_position.y(), self.socket_row_map, self
            )
            self._register_new_node(new_entity_node, new_ui_node)

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
        source_socket_addr = SocketAddress(source_ui_socket.node_entity_id, source_ui_socket.socket_entity_name)
        target_socket_addr = SocketAddress(target_ui_socket.node_entity_id, target_ui_socket.socket_entity_name)

        logger.info(
            f"GraphController: Requesting to create edge between entity sockets: "
            f"({source_socket_addr.node_id}::{source_socket_addr.socket_name}) -> "
            f"({target_socket_addr.node_id}::{target_socket_addr.socket_name})"
        )

        edge_key = EdgeKey(source_socket_addr, target_socket_addr)
        if edge_key in self.edge_map:
            logger.debug(
                f"  Connection already exists between {source_socket_addr} and "
                f"{target_socket_addr}. No new connection created."
            )
            return None

        connection_success, reason = self.entity_graph.link_sockets(source_socket_addr, target_socket_addr)

        if connection_success:
            logger.debug("  Entity connection successful. Creating UI EdgeItem.")

            new_edge_item = EdgeItem(source_ui_socket, target_ui_socket.scenePos())
            new_edge_item.set_target_socket(target_ui_socket)
            new_edge_item.settle_z_value()  # Set to normal Z value for finalized edges

            self.graphics_scene.add_edge(new_edge_item)

            self.edge_map[edge_key] = new_edge_item
            logger.debug(f"  UI EdgeItem created and added to scene/map for edge: {edge_key}")
            return new_edge_item
        else:
            logger.warning(
                f"  Entity connection FAILED between {source_socket_addr} and {target_socket_addr}. Reason: {reason}. No UI edge created."
            )
            return None

    def request_remove_node(self, entity_node_id: str):
        """
        Handles a request to remove a node (entity and UI) and its connected edges.
        """
        logger.info(f"GraphController: Requesting to remove node with ID: {entity_node_id}")

        # XXX: This is bad, the order should be reversed and we should use existing functionality
        # for removing things:
        # 1. Remove edges relating to the node first to avoid dangling references
        # 2. Remove nodes from the graph and scene
        #
        # directives: use existing functions to handle deletion. e.g. remove_edge, remove_node
        # looks like the request_add/remove_node is the lowest level function call.

        # 1. Remove node from the entity graph
        # This should also handle disconnecting its entity sockets.
        self.entity_graph.remove_node(entity_node_id)
        logger.debug(f"Node {entity_node_id} removed from entity graph.")

        # 2. Remove the UI NodeItem from the scene and our map
        ui_node_to_remove = self.node_map.pop(entity_node_id, None)
        if ui_node_to_remove:
            self.graphics_scene.remove_node(ui_node_to_remove)
            logger.debug(f"UI NodeItem for {entity_node_id} removed from graphics scene and node_map.")
        else:
            logger.warning(f"No UI NodeItem found in node_map for ID {entity_node_id}.")

        # XXX: We need to refactor to have edge key be a dataclass or something. This is scary weak.
        # This has been addressed by introducing the EdgeKey dataclass.
        # 3. Clean up EdgeItems from the edge_map and scene connected to this node
        edges_to_remove_keys: list[EdgeKey] = []
        for edge_key_iter in self.edge_map:  # Iterate over keys
            if edge_key_iter.source.node_id == entity_node_id or edge_key_iter.target.node_id == entity_node_id:
                edges_to_remove_keys.append(edge_key_iter)

        for edge_key_to_remove in edges_to_remove_keys:
            removed_edge_item = self.edge_map.pop(edge_key_to_remove, None)
            if removed_edge_item:
                self.graphics_scene.remove_edge(removed_edge_item)
                logger.debug(f"  Edge {edge_key_to_remove} and its UI item removed from edge_map and scene.")
            else:
                logger.warning(
                    f"  Edge key {edge_key_to_remove} was marked for removal but not found in edge_map during pop."
                )

        logger.info(f"GraphController: Node removal process for {entity_node_id} complete.")

    def request_remove_edge(self, ui_edge_item: EdgeItem):
        """
        Handles a request to remove a single edge (entity and UI).

        Args:
            ui_edge_item: The EdgeItem instance to remove.
        """
        # XXX: We need to think about what this function should take, remove_edge will most likely come from the
        # scene, but teh scene should be aware of socket addresses and should be able to send a EdgeKey and
        # let the controller manage from there.
        if not ui_edge_item or not ui_edge_item.source_socket_item or not ui_edge_item.target_socket_item:
            logger.warning("GraphController: Invalid EdgeItem provided to request_remove_edge. Cannot proceed.")
            return

        source_socket_addr = SocketAddress(
            ui_edge_item.source_socket_item.node_entity_id, ui_edge_item.source_socket_item.socket_entity_name
        )
        target_socket_addr = SocketAddress(
            ui_edge_item.target_socket_item.node_entity_id, ui_edge_item.target_socket_item.socket_entity_name
        )

        edge_repr = f"({source_socket_addr}) -> ({target_socket_addr})"
        logger.info(f"GraphController: Requesting to remove edge: {edge_repr}")

        # 1. Disconnect in the entity graph
        disconnection_success, reason = self.entity_graph.unlink_sockets(source_socket_addr, target_socket_addr)
        if disconnection_success:
            logger.debug(f"  Entity disconnection successful for {edge_repr}.")
        else:
            # Log failure but proceed to remove UI element as user requested its deletion directly.
            logger.warning(
                f"  Entity disconnection FAILED for {edge_repr}. Reason: {reason}. Proceeding with UI removal."
            )

        # 2. Remove the UI EdgeItem from the scene
        self.graphics_scene.remove_edge(ui_edge_item)
        logger.debug(f"  UI EdgeItem for {edge_repr} removed from graphics scene.")

        # 3. Remove the edge from our edge_map
        edge_key_to_remove: EdgeKey | None = None
        prospective_key = EdgeKey(source_socket_addr, target_socket_addr)

        if prospective_key in self.edge_map and self.edge_map[prospective_key] == ui_edge_item:
            edge_key_to_remove = prospective_key
        else:
            # Fallback: Iterate if direct key lookup fails. This can happen if the
            # ui_edge_item instance was somehow replaced or if the edge_map uses a different instance.
            for key, val in self.edge_map.items():
                if val == ui_edge_item:
                    edge_key_to_remove = key
                    break

        if edge_key_to_remove:
            removed_item = self.edge_map.pop(edge_key_to_remove, None)
            if removed_item:
                self.graphics_scene.remove_edge(removed_item)  # Explicitly remove from scene
                logger.debug(f"  Edge {edge_key_to_remove} and its UI item removed from edge_map and scene.")
            else:
                logger.warning(f"  Edge key {edge_key_to_remove} found but pop failed from edge_map.")
        else:
            logger.warning(f"  Could not find edge {edge_repr} (instance: {ui_edge_item}) in edge_map to remove.")

        logger.info(f"GraphController: Edge removal process for {edge_repr} complete.")

    def request_edge_drop_targets(self, source_socket_ui_item: "SocketCircleItem") -> set[SocketAddress]:
        """
        Return a set of SocketAddress objects that are valid drop targets for the given source_socket_ui_item.
        The source_socket_ui_item is the UI representation of the socket being dragged.
        Only target sockets are considered as potential drop targets here, assuming a standard drag from an output.
        If reverse drag (source to target) is fully supported, this logic might need adjustment for the target iteration.
        """
        valid_targets: set[SocketAddress] = set()

        source_node_id = source_socket_ui_item.node_entity_id
        source_entity_node = self.entity_graph.get_node(source_node_id)

        # This should never happen, there should always be a source.
        assert source_entity_node is not None, f"Source node not found for {source_node_id}"

        logger.debug(source_entity_node)
        logger.debug(source_socket_ui_item.socket_entity_name)

        # Determine if the source_socket_ui_item represents a target or source for entity lookup
        if source_socket_ui_item.is_input:  # This implies a reverse drag scenario for the source
            entity_source_socket = source_entity_node.target_sockets.get(source_socket_ui_item.socket_entity_name)
            socket_iter = "source_sockets"
            logger.debug(f"Source socket is reversed: {source_entity_node.target_sockets}")
        else:  # Standard drag: source_socket_ui_item is an output
            entity_source_socket = source_entity_node.source_sockets.get(source_socket_ui_item.socket_entity_name)
            socket_iter = "target_sockets"
            logger.debug(f"Source socket is normal: {source_entity_node.source_sockets}")

        # This should never happen, there should always be a source.
        assert entity_source_socket is not None, (
            f"Source socket not found for {source_socket_ui_item.socket_entity_name}"
        )

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

    def handle_ui_edge_connection_attempt(
        self, source_ui_socket: "SocketCircleItem", target_ui_socket: "SocketCircleItem"
    ):
        source_socket_addr = SocketAddress(source_ui_socket.node_entity_id, source_ui_socket.socket_entity_name)
        target_socket_addr = SocketAddress(target_ui_socket.node_entity_id, target_ui_socket.socket_entity_name)

        logger.debug(
            f"GraphController: Received handle_ui_edge_connection_attempt from "
            f"{source_socket_addr} to "
            f"{target_socket_addr}"
        )

        # we need to check if the edge that we are trying to create already exists.
        edge_key = EdgeKey(source_socket_addr, target_socket_addr)
        if edge_key in self.edge_map:
            logger.warning(f"Edge {edge_key} already exists. Ignoring connection attempt.")
            return

        # If the target socket already has an edge, we remove it, tartet nodes can only have one edge
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
            f"GraphController: Received handle_ui_node_creation_request for type '{node_type_hint}' at {scene_pos}"
        )

        node_class_to_create = self._node_type_registry.get(node_type_hint)

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
            self.request_remove_edge(edge_item)
