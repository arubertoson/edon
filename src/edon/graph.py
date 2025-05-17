"""Defines the core graph data structure for the Edon node editor.

This module provides the `EntityGraph` class, which serves as the central
representation of the node-based graph. It is responsible for managing the
collection of `EntityNode` instances and their interconnections via `EntitySocket`
objects.

"""

from dataclasses import dataclass, field

from edon.node import EntityNode
from edon.socket import EntitySocket, SocketDirection

from edon.errors import GraphObjectErrorReason, SocketConnectionErrorReason, SocketDisconnectionErrorReason


@dataclass
class EntityGraph:
    """
    Represents the data structure for a directed graph of `EntityNode` objects,
    managing their connections and providing operations for graph manipulation and
    inspection.

    Attributes:
        nodes: A dictionary mapping node IDs (str) to EntityNode instances.
    """

    nodes: dict[str, EntityNode] = field(default_factory=dict)  # Modern dict

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
        Removes a node from the graph and disconnects all its sockets.

        If the node_id is not found, the method returns silently.

        Args:
            node_id: The unique identifier of the node to remove.
        """
        node_to_remove = self.nodes.pop(node_id, None)
        if not node_to_remove:
            return

        # Collect all sockets of the node to ensure all its connections are severed
        all_sockets_to_disconnect: list[EntitySocket] = []
        all_sockets_to_disconnect.extend(node_to_remove.input_sockets.values())
        all_sockets_to_disconnect.extend(node_to_remove.output_sockets.values())

        for sock_to_clear in all_sockets_to_disconnect:
            # Iterate over a copy as remove_connection modifies the original connections set
            connected_sockets_copy = list(sock_to_clear.connections)
            for other_sock in connected_sockets_copy:
                sock_to_clear.remove_connection(other_sock)

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
        by following output socket connections. It's primarily used for cycle
        detection before creating new connections.

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
            for output_socket in node.output_sockets.values():
                for connected_input_socket in output_socket.connections:
                    # Traverse to the parent node of the connected input socket
                    next_node = connected_input_socket.parent_node
                    if next_node and next_node.id not in visited:
                        stack.append(next_node.id)
        return False

    def connect_sockets(
        self, output_ref: tuple[str, str], input_ref: tuple[str, str]
    ) -> tuple[bool, SocketConnectionErrorReason | GraphObjectErrorReason | None]:
        """
        Connects an output socket of one node to an input socket of another node.

        Before attempting the connection, this method validates the existence of nodes
        and sockets, checks their directions, and performs cycle detection to prevent
        circular dependencies in the graph.

        Args:
            output_ref: A tuple (node_id, socket_name) for the output socket.
            input_ref: A tuple (node_id, socket_name) for the input socket.

        Returns:
            A tuple: (success: bool, reason: Enum | None).
            If successful, `success` is True and `reason` is None.
            If unsuccessful, `success` is False and `reason` is an enum value from
            SocketConnectionErrorReason or GraphObjectErrorReason indicating the failure.
        """
        output_node_id, output_socket_name = output_ref
        input_node_id, input_socket_name = input_ref

        output_node = self.get_node(output_node_id)
        if not output_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        input_node = self.get_node(input_node_id)
        if not input_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        if self._has_path(input_node_id, output_node_id):
            return False, SocketConnectionErrorReason.CYCLE_DETECTED

        output_socket = output_node.output_sockets.get(output_socket_name)
        if not output_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND
        if output_socket.direction != SocketDirection.OUTPUT:
            return False, GraphObjectErrorReason.SOCKET_DIRECTION_INVALID

        input_socket = input_node.input_sockets.get(input_socket_name)
        if not input_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND
        if input_socket.direction != SocketDirection.INPUT:
            return False, GraphObjectErrorReason.SOCKET_DIRECTION_INVALID

        return input_socket.add_connection(output_socket)

    def disconnect_sockets(
        self, output_ref: tuple[str, str], input_ref: tuple[str, str]
    ) -> tuple[bool, SocketDisconnectionErrorReason | GraphObjectErrorReason | None]:
        """
        Disconnects a specific connection between an output socket and an input socket.

        This method validates the existence of the specified nodes and sockets before
        attempting the disconnection.

        Args:
            output_ref: A tuple (node_id, socket_name) for the output socket.
            input_ref: A tuple (node_id, socket_name) for the input socket.

        Returns:
            A tuple: (success: bool, reason: Enum | None).
            If successful, `success` is True and `reason` is None.
            If unsuccessful, `success` is False and `reason` is an enum value from
            SocketDisconnectionErrorReason or GraphObjectErrorReason indicating the failure.
        """
        output_node_id, output_socket_name = output_ref
        input_node_id, input_socket_name = input_ref

        output_node = self.get_node(output_node_id)
        if not output_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        input_node = self.get_node(input_node_id)
        if not input_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        output_socket = output_node.output_sockets.get(output_socket_name)
        if not output_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND

        input_socket = input_node.input_sockets.get(input_socket_name)
        if not input_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND

        return input_socket.remove_connection(output_socket)

    def __repr__(self) -> str:
        return f"Graph(nodes_count={len(self.nodes)})"
