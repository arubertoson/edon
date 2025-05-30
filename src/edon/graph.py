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

    It is defined by `node_id`, the unique identifier of its parent node, and
    `socket_name`, the name of the socket on that node.
    """

    node_id: str
    socket_name: str


@dataclass(frozen=True)
class EdgeKey:
    """Uniquely identifies an edge by its source and target socket addresses.

    It is defined by its `source` and `target` `SocketAddress` instances,
    representing the two endpoints of the connection.
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

    It primarily consists of `nodes`, a mapping from node IDs to `EntityNode`
    instances, which forms the core storage of the graph's structure.
    """

    nodes: NodeMap = field(default_factory=dict)

    def add_node(self, node: EntityNode):
        """Adds a given `EntityNode` instance to the graph.

        If a node with the same ID already exists, a `ValueError` is raised.
        """
        if node.id in self.nodes:
            raise ValueError(f"Node with ID '{node.id}' already exists in the graph.")
        self.nodes[node.id] = node

    def remove_node(self, node_id: str):
        """Removes a node, identified by `node_id`, from the graph.

        All links connected to the sockets of the removed node are also unlinked.
        If the `node_id` is not found, the method completes silently.
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

    def get_node(self, node_id: str) -> EntityNode:
        """Retrieves an `EntityNode` from the graph by its `node_id`.

        Returns the `EntityNode` instance if found, otherwise `None`.
        """
        return self.nodes[node_id]

    def _has_path(self, start_node_id: str, end_node_id: str) -> bool:
        """Determines if a directed path exists from a start node to an end node.

        This check is crucial for cycle detection before establishing new links
        between nodes. It employs a depth-first search (DFS) algorithm, traversing
        the graph by following established links from source sockets to target sockets.
        The search proceeds from the node specified by `start_node_id` towards
        the node specified by `end_node_id`.

        Returns `True` if `end_node_id` is reachable from `start_node_id` following
        the directed edges of the graph, and `False` otherwise.
        """
        visited: set[str] = set()
        # Stack stores node IDs to visit for DFS
        stack: list[str] = [start_node_id]

        while stack:
            current_node_id = stack.pop()

            if current_node_id == end_node_id:
                # Path found from start_node_id to end_node_id.
                # If start_node_id == end_node_id, this means a zero-length path,
                # which is true. In the context of cycle detection, this call
                # is made with start_node_id != end_node_id (target_node.id, source_node.id),
                # because self-links are caught by EntitySocket.can_link_to.
                return True

            if current_node_id in visited:
                continue
            visited.add(current_node_id)

            current_node = self.get_node(current_node_id)
            if not current_node:
                # This can happen if start_node_id or an intermediate node_id is not in the graph.
                continue

            # Explore outgoing edges: from source sockets of current_node
            # to target sockets of neighbor_nodes.
            for source_socket in current_node.source_sockets.values():
                for linked_target_socket in source_socket.links:
                    # linked_target_socket is a socket on another node.
                    # Its parent node is the neighbor in the graph.
                    neighbor_node = linked_target_socket.node
                    if neighbor_node:  # Should always be true if graph is consistent
                        if neighbor_node.id not in visited:
                            stack.append(neighbor_node.id)
                            # Optimization: if neighbor_node.id == end_node_id, could return True here.
                            # However, handling it at the pop() stage is also correct and standard.
        return False

    def _get_socket_and_node(
        self, socket_addr: SocketAddress, expected_role: SocketRole
    ) -> tuple[EntitySocket | None, EntityNode | None, GraphObjectErrorReason | None]:
        """Retrieves a socket and its parent node, validating against an expected role.

        If the node or socket (in the expected role's collection) is not found,
        or if the socket's actual direction does not match the expected role,
        an appropriate error reason is returned.
        """
        node = self.get_node(socket_addr.node_id)
        if not node:
            return None, None, GraphObjectErrorReason.NODE_NOT_FOUND

        # XXX: Need to observe if this is working correclty.
        socket_collection: Mapping[str, EntitySocket]
        if expected_role == SocketRole.SOURCE:
            socket_collection = node.source_sockets
        elif expected_role == SocketRole.TARGET:
            socket_collection = node.target_sockets
        else:
            # This case should ideally not be reached if called with valid SocketRole.
            # Adding an assertion for robustness during development.
            raise AssertionError(f"Invalid expected_role: {expected_role}")

        socket = socket_collection.get(socket_addr.socket_name)
        assert socket, f"CORRUPTION: failed lookup for {SocketAddress}, in {node}"
        if not socket:
            return None, node, GraphObjectErrorReason.SOCKET_NOT_FOUND

        # Sockets fetched from node.source_sockets or node.target_sockets
        # are guaranteed by EntityNode's structure to have the correct direction.
        # Thus, an explicit check like `if socket.direction != expected_role:`
        # is redundant here and has been removed.
        return socket, node, None

    def link_sockets(
        self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """Establishes a directed link from a source socket to a target socket."""
        source_socket, source_node, error = self._get_socket_and_node(source_socket_addr, SocketRole.SOURCE)
        if error:
            return False, error

        target_socket, target_node, error = self._get_socket_and_node(target_socket_addr, SocketRole.TARGET)
        if error:
            return False, error

        if self._has_path(target_node.id, source_node.id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        return target_socket.link_to(source_socket)

    def unlink_sockets(
        self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress
    ) -> tuple[bool, SocketUnlinkErrorReason | GraphObjectErrorReason | None]:
        """Removes a specific link between a source socket and a target socket."""
        source_socket, _, error = self._get_socket_and_node(source_socket_addr, SocketRole.SOURCE)
        if error:
            return False, error

        target_socket, _, error = self._get_socket_and_node(target_socket_addr, SocketRole.TARGET)
        if error:
            return False, error

        return target_socket.unlink_from(source_socket)

    def can_form_link(
        self, prospective_source_addr: SocketAddress, prospective_target_addr: SocketAddress
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """Determines if a new directed edge can be validly formed."""
        source_socket, source_node, src_error = self._get_socket_and_node(prospective_source_addr, SocketRole.SOURCE)
        target_socket, target_node, trg_error = self._get_socket_and_node(prospective_target_addr, SocketRole.TARGET)
        assert src_error is None and trg_error is None, "CORRUPTION: unable to get existing entities."

        # Check 1: Basic link compatibility (type, role, self-connection etc.)
        can_link, reason = target_socket.can_link_to(source_socket)
        if not can_link:
            return False, reason

        # Check 2: Prevent cyclical dependencies
        if self._has_path(target_node.id, source_node.id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        return True, None

    def __repr__(self) -> str:
        return f"Graph(nodes_count={len(self.nodes)})"
