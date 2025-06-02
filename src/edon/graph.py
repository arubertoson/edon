"""Defines the core graph data structure for the Edon node editor.

This module provides the `EntityGraph` class, which serves as the central
representation of the node-based graph. It is responsible for managing the
collection of `EntityNode` instances and their interconnections via `EntitySocket`
objects.

"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from edon.logging import logger
from edon.errors import GraphObjectErrorReason, SocketLinkErrorReason
from edon.node import EntityNode
from edon.socket import EntitySocket
from edon.types import SocketAddress, SocketRole

if TYPE_CHECKING:
    from edon.types import EdgeKey


NodeMap: TypeAlias = MutableMapping[str, EntityNode]


@dataclass
class EntityGraph:
    """
    Represents the data structure for a directed graph of `EntityNode` objects,
    managing their links and providing operations for graph manipulation and
    inspection.

    It primarily consists of `nodes`, a mapping from node IDs to `EntityNode`
    instances, which forms the core storage of the graph's structure, and
    `edges`, a set of `EdgeKey` objects tracking all connections in the graph.
    """

    nodes: NodeMap = field(default_factory=dict)
    edges: set[EdgeKey] = field(default_factory=set)

    def add_node(self, node: EntityNode) -> None:
        """Adds a given `EntityNode` instance to the graph.

        If a node with the same ID already exists, a `ValueError` is raised.
        """
        assert node.id not in self.nodes, (
            f"CORRUPTION: Node with ID '{node.id} already exists in the graph'"
        )

        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        """Removes a node, identified by `node_id`, from the graph.

        All links connected to the sockets of the removed node are also unlinked.
        """
        node_to_remove = self.nodes.pop(node_id, None)
        assert node_to_remove is not None, (
            f"CORRUPTION: Node ID {node_id} to remove doesn't exist in the graph"
        )

        for sock_to_unlink in node_to_remove.sockets.values():
            linked_sockets_copy = list(sock_to_unlink.links)
            for other_sock in sock_to_unlink.links:
                sock_to_unlink.unlink_from(other_sock)

    def get_node(self, node_id: str) -> EntityNode:
        return self.nodes[node_id]

    def _is_reachable(self, start_node_id: str, end_node_id: str) -> bool:
        """Determines if a directed path exists from a start node to an end node.

        This method employs a depth-first search (DFS) algorithm, traversing
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
                logger.debug("Returning same node")
                return True

            if current_node_id in visited:
                continue
            visited.add(current_node_id)

            current_node = self.get_node(current_node_id)
            if not current_node:
                # This can happen if start_node_id or an intermediate node_id is not in the graph.
                continue

            logger.debug(f"CURRENT NODE: {current_node}")

            # Explore outgoing edges: from source sockets of current_node
            # to target sockets of neighbor_nodes.
            for source_socket in current_node.source_sockets:
                logger.debug(f"SOURCE SOCKET: {source_socket}")
                for linked_target_socket in source_socket.links:
                    logger.debug(f"TARGET SOCKET: {linked_target_socket}")
                    # linked_target_socket is a socket on another node.
                    # Its parent node is the neighbor in the graph.
                    neighbor_node = linked_target_socket.node
                    if neighbor_node.id not in visited:
                        stack.append(neighbor_node.id)
                        # Optimization: if neighbor_node.id == end_node_id, could return True here.
                        # However, handling it at the pop() stage is also correct and standard.

        logger.debug("FOUND NOTHING!")
        return False

    def _get_socket_and_node(self, socket_addr: SocketAddress) -> tuple[EntitySocket, EntityNode]:
        """Retrieves a socket and its parent node.

        This is an internal helper and assumes the socket_addr is valid and refers
        to an existing node and socket within that node.
        """
        node = self.get_node(socket_addr.node_id)
        assert node, f"CORRUPTION: Private node lookup failed on {socket_addr.node_id}"

        socket = node.sockets[socket_addr.name]
        assert socket, f"CORRUPTION: failed lookup for {SocketAddress}, in {node}"

        return socket, node

    def link_sockets(
        self, edge_key: EdgeKey
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """Establishes a directed link from a source socket to a target socket."""
        source_socket, source_node = self._get_socket_and_node(edge_key.source)
        target_socket, target_node = self._get_socket_and_node(edge_key.target)

        if source_socket in target_socket.links:
            return False, SocketLinkErrorReason.ALREADY_LINKED

        if self._is_reachable(target_node.id, source_node.id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        socket_linked_successfully, reason = source_socket.link_to(target_socket)

        if not socket_linked_successfully:
            return False, reason

        self.edges.add(edge_key)
        logger.debug(f"Graph linked sockets: {source_socket.address} -> {target_socket.address}")

        return True, None

        # Perform direct linking, we've already passed validation checks.
        source_socket.links.append(target_socket)
        target_socket.links.append(source_socket)
        self.edges.add(edge_key)

        return True, None

    def unlink_sockets(self, edge_key: EdgeKey) -> None:
        """Removes a specific link between a source socket and a target socket."""
        source_socket, _ = self._get_socket_and_node(edge_key.source)
        target_socket, _ = self._get_socket_and_node(edge_key.target)

        assert source_socket in target_socket.links and edge_key in self.edges, (
            f"CORRUPTION: Can't unlink an edge that doesn't exist, `{edge_key}`"
        )

        target_socket.unlink_from(source_socket)
        self.edges.discard(edge_key)

    def can_form_link(
        self, prospective_source_addr: SocketAddress, prospective_target_addr: SocketAddress
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """Determines if a new directed edge can be validly formed."""
        source_socket, source_node = self._get_socket_and_node(prospective_source_addr)
        target_socket, target_node = self._get_socket_and_node(prospective_target_addr)

        # If target socket has existing links it's a valid drop target. But we don't
        # want to recreate the connection if it's not necessary which is why we
        # pass the error along, the requester can react and stop any further
        # unnecessary execution. But if we are just checking validity it would
        # still give us the correct response.
        if source_socket in target_socket.links:
            return False, SocketLinkErrorReason.ALREADY_LINKED

        # Check for cycles: A cycle is formed if the target node can already reach the source node.
        if self._is_reachable(target_node.id, source_node.id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        # Validates basic link compatibility (type, role, self-connection etc.)
        can_link, reason = source_socket.can_link_to(target_socket)
        if not can_link:
            return False, reason

        return True, None

    def partition_valid_link_targets(
        self, source_socket_addr: SocketAddress
    ) -> tuple[set[SocketAddress], set[SocketAddress]]:
        """Determines valid and invalid drop target sockets for the given source socket.

        Returns a tuple of (valid_targets, invalid_targets) where each is a set of SocketAddress.
        """
        valid_targets: set[SocketAddress] = set()
        invalid_targets: set[SocketAddress] = set()

        # Determine the role of the source socket
        source_node = self.get_node(source_socket_addr.node_id)
        source_role = source_socket_addr.role

        # Iterate through all nodes to categorize their sockets
        for node in self.nodes.values():
            same_role_sockets: list[EntitySocket]
            other_role_sockets: list[EntitySocket]
            if source_role == SocketRole.SOURCE:
                same_role_sockets = node.source_sockets
                other_role_sockets = node.target_sockets
            else:
                same_role_sockets = node.target_sockets
                other_role_sockets = node.source_sockets

            # We iterate over each role list, we know that same role sockets will be
            # part of the invalid list as we have the internal rule when role == role
            # the link is not allowed.
            for socket in same_role_sockets:
                invalid_targets.add(socket.address)

            for socket in other_role_sockets:
                # Determine proper source and target for validation
                if source_role == SocketRole.SOURCE:
                    prospective_source_addr = source_socket_addr
                    prospective_target_addr = socket.address
                else:
                    prospective_source_addr = socket.address
                    prospective_target_addr = source_socket_addr

                can_form, _ = self.can_form_link(prospective_source_addr, prospective_target_addr)

                if can_form:
                    valid_targets.add(socket.address)
                else:
                    invalid_targets.add(socket.address)

        return valid_targets, invalid_targets

    def __repr__(self) -> str:
        return f"Graph(nodes_count={len(self.nodes)}, edges_count={len(self.edges)})"
