"""Defines the core graph data structure for the Edon node editor.

This module provides the `EntityGraph` class, which serves as the central
representation of the node-based graph. It is responsible for managing the
collection of `EntityNode` instances and their interconnections via `EntitySocket`
objects.

"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TypeAlias

from edon.errors import GraphObjectErrorReason, SocketLinkErrorReason, SocketUnlinkErrorReason
from edon.node import EntityNode
from edon.socket import EntitySocket, SocketRole


@dataclass(frozen=True)
class SocketAddress:
    """Represents a unique socket endpoint within the graph, identifying an entity socket.

    Attributes:
        node_id: The unique identifier of the parent node.
        socket_name: The name of the socket on the node (entity socket name).
    """

    node_id: str
    socket_name: str


@dataclass(frozen=True)
class EdgeKey:
    """Uniquely identifies an edge by its source and target socket addresses.

    Attributes:
        source: The SocketAddress of the source socket.
        target: The SocketAddress of the target socket.
    """

    source: SocketAddress
    target: SocketAddress


NodeMap: TypeAlias = Mapping[str, EntityNode]


@dataclass
class EntityGraph:
    """
    Represents the data structure for a directed graph of `EntityNode` objects,
    managing their links and providing operations for graph manipulation and
    inspection.

    Attributes:
        nodes: A dictionary mapping node IDs (str) to EntityNode instances.
    """

    nodes: NodeMap = field(default_factory=dict)

    def add_node(self, node: EntityNode):
        """Adds a node to the graph.

        Args:
            node: The EntityNode instance to add.

        Raises:
            TypeError: If the provided object is not an instance of EntityNode.
            ValueError: If a node with the same ID already exists in the graph.
        """
        if node.id in self.nodes:
            raise ValueError(f"Node with ID '{node.id}' already exists in the graph.")
        self.nodes[node.id] = node

    def remove_node(self, node_id: str):
        """
        Removes a node from the graph and unlink all its sockets.

        If the node_id is not found, the method returns silently.

        Args:
            node_id: The unique identifier of the node to remove.
        """
        node_to_remove = self.nodes.pop(node_id, None)
        if not node_to_remove:
            return

        all_sockets_to_unlink: list[EntitySocket] = []
        all_sockets_to_unlink.extend(node_to_remove.source_sockets.values())
        all_sockets_to_unlink.extend(node_to_remove.target_sockets.values())

        for sock_to_unlink in all_sockets_to_unlink:
            linked_sockets_copy = list(sock_to_unlink.links)
            for other_sock in linked_sockets_copy:
                sock_to_unlink.unlink_from(other_sock)

    def get_node(self, node_id: str) -> EntityNode | None:
        """Retrieves a node by its ID.

        Args:
            node_id: The unique identifier of the node to retrieve.

        Returns:
            The EntityNode instance if found, otherwise None.
        """
        return self.nodes.get(node_id)

    def _has_path(self, start_node_id: str, end_node_id: str) -> bool:
        """
        Checks if a path exists from a start node to an end node.

        This method uses a depth-first search (DFS) algorithm to traverse the graph
        by following source socket links. It's primarily used for cycle
        detection before creating new links.

        Args:
            start_node_id: The ID of the node to start the path search from.
            end_node_id: The ID of the target node.

        Returns:
            True if `end_node_id` is reachable from `start_node_id`, False otherwise.
        """
        visited = set()
        stack = [start_node_id]
        while stack:
            current_id = stack.pop()
            if current_id == end_node_id:
                return True
            if current_id in visited:
                continue
            visited.add(current_id)
            node = self.get_node(current_id)
            if not node:
                continue
            for source_socket in node.target_sockets.values():
                for linked_source_socket in source_socket.links:
                    # Traverse to the parent node of the linked target socket
                    next_node = linked_source_socket.node
                    if next_node and next_node.id not in visited:
                        stack.append(next_node.id)
        return False

    def link_sockets(
        self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """
        Links an source socket of one node to an target socket of another node.

        Before attempting the link, this method validates the existence of nodes
        and sockets, checks their directions, and performs cycle detection to prevent
        circular dependencies in the graph.

        Args:
            source_socket_addr: The SocketAddress for the source socket.
            target_socket_addr: The SocketAddress for the target socket.

        Returns:
            A tuple: (success: bool, reason: Enum | None).
            If successful, `success` is True and `reason` is None.
            If unsuccessful, `success` is False and `reason` is an enum value from
            SocketLinkErrorReason or GraphObjectErrorReason indicating the failure.
        """
        source_node_id = source_socket_addr.node_id
        source_socket_name = source_socket_addr.socket_name
        target_node_id = target_socket_addr.node_id
        target_socket_name = target_socket_addr.socket_name

        source_node = self.get_node(source_node_id)
        if not source_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        target_node = self.get_node(target_node_id)
        if not target_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        if self._has_path(target_node_id, source_node_id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        source_socket = source_node.source_sockets.get(source_socket_name)
        if not source_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND
        if source_socket.direction != SocketRole.SOURCE:
            return False, GraphObjectErrorReason.SOCKET_DIRECTION_INVALID

        target_socket = target_node.target_sockets.get(target_socket_name)
        if not target_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND
        if target_socket.direction != SocketRole.TARGET:
            return False, GraphObjectErrorReason.SOCKET_DIRECTION_INVALID

        return target_socket.link_to(source_socket)

    def unlink_sockets(
        self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress
    ) -> tuple[bool, SocketUnlinkErrorReason | GraphObjectErrorReason | None]:
        """
        Unlinks a specific link between an output socket and an input socket.

        This method validates the existence of the specified nodes and sockets before
        attempting the unlinking.

        Args:
            source_socket_addr: The SocketAddress for the source socket.
            target_socket_addr: The SocketAddress for the target socket.

        Returns:
            A tuple: (success: bool, reason: Enum | None).
            If successful, `success` is True and `reason` is None.
            If unsuccessful, `success` is False and `reason` is an enum value from
            SocketUnlinkErrorReason or GraphObjectErrorReason indicating the failure.
        """
        source_node_id = source_socket_addr.node_id
        source_socket_name = source_socket_addr.socket_name
        target_node_id = target_socket_addr.node_id
        target_socket_name = target_socket_addr.socket_name

        source_node = self.get_node(source_node_id)
        if not source_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        target_node = self.get_node(target_node_id)
        if not target_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        source_socket = source_node.source_sockets.get(source_socket_name)
        if not source_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND

        target_socket = target_node.target_sockets.get(target_socket_name)
        if not target_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND

        return target_socket.unlink_from(source_socket)

    def __repr__(self) -> str:
        return f"Graph(nodes_count={len(self.nodes)})"
