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

    def get_node(self, node_id: str) -> EntityNode | None:
        """Retrieves an `EntityNode` from the graph by its `node_id`.

        Returns the `EntityNode` instance if found, otherwise `None`.
        """
        return self.nodes.get(node_id)

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
        """Establishes a directed link from a source socket to a target socket.

        The connection is made between the socket identified by `source_socket_addr`
        (which must be a source/output socket) and the socket identified by
        `target_socket_addr` (which must be a target/input socket).

        Before linking, this method performs several validations:
        -   Ensures both specified nodes and their respective sockets exist.
        -   Verifies that the socket directions are compatible (source to target).
        -   Checks for type compatibility between the sockets via `EntitySocket.link_to`.
        -   Performs cycle detection to prevent circular dependencies within the graph.
            A link is disallowed if it would create a path from `target_socket_addr.node_id`
            back to `source_socket_addr.node_id`.

        Returns a tuple `(success, reason)`. If `success` is `True`, the link
        was successfully created, and `reason` is `None`. If `success` is `False`,
        the link was not created, and `reason` will be an enum value from
        `SocketLinkErrorReason` or `GraphObjectErrorReason` detailing the cause
        of failure.
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
        """Removes a specific link between a source socket and a target socket.

        The link to be removed is identified by the `source_socket_addr` (the source/output
        end of the link) and `target_socket_addr` (the target/input end of the link).
        This method validates the existence of the specified nodes and sockets
        before attempting to remove the link.

        Returns a tuple `(success, reason)`. If `success` is `True`, the link
        was successfully removed, and `reason` is `None`. If `success` is `False`,
        the link was not removed (e.g., if it didn't exist or nodes/sockets
        were not found), and `reason` will be an enum value from
        `SocketUnlinkErrorReason` or `GraphObjectErrorReason` detailing the cause.
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

    def can_form_edge(
        self, prospective_source_addr: SocketAddress, prospective_target_addr: SocketAddress
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """Determines if a new directed edge can be validly formed.

        This check is performed between a `prospective_source_addr` (an output socket)
        and a `prospective_target_addr` (an input socket).

        The validation process includes:
        -   Ensuring the existence of both nodes and their respective sockets.
        -   Verifying that the `prospective_source_addr` indeed refers to a source/output
            socket and `prospective_target_addr` to a target/input socket.
        -   Assessing fundamental compatibility between the two sockets (e.g., data type,
            role, preventing self-connection), typically delegated to the target socket's
            `can_link_to` method.
        -   Preventing the formation of cycles: an edge from the source node to the
            target node is disallowed if a path already exists from the target node
            back to the source node.

        Returns a tuple `(can_form, reason)`. If `can_form` is `True`, a valid
        edge can be created, and `reason` is `None`. If `can_form` is `False`,
        `reason` will be an enum value from `SocketLinkErrorReason` or
        `GraphObjectErrorReason` explaining why the edge cannot be formed.
        """
        source_node = self.get_node(prospective_source_addr.node_id)
        if not source_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        target_node = self.get_node(prospective_target_addr.node_id)
        if not target_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        source_socket = source_node.source_sockets.get(prospective_source_addr.socket_name)
        if not source_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND
        if source_socket.direction != SocketRole.SOURCE:
            # This implies the provided prospective_source_addr is not actually a source/output socket.
            return False, GraphObjectErrorReason.SOCKET_DIRECTION_INVALID

        target_socket = target_node.target_sockets.get(prospective_target_addr.socket_name)
        if not target_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND
        if target_socket.direction != SocketRole.TARGET:
            # This implies the provided prospective_target_addr is not actually a target/input socket.
            return False, GraphObjectErrorReason.SOCKET_DIRECTION_INVALID

        # Check 1: Basic link compatibility (type, role, self-connection etc.)
        # EntitySocket.can_link_to(self, other) assumes self=Input (target), other=Output (source)
        can_link, reason = target_socket.can_link_to(source_socket)
        if not can_link:
            return False, reason # reason is already a SocketLinkErrorReason

        # Check 2: Prevent cyclical dependencies
        # An edge A (source_node) -> B (target_node) creates a cycle if a path B -> A already exists.
        if self._has_path(target_node.id, source_node.id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        return True, None

    def __repr__(self) -> str:
        return f"Graph(nodes_count={len(self.nodes)})"
