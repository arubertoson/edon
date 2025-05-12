from dataclasses import dataclass, field

# Optional is no longer needed from typing if we use Node | None
# from typing import Optional
# Assuming node.py and socket.py are accessible
from edon.node import EntityNode
from edon.socket import Socket, SocketDirection

from .errors import GraphObjectErrorReason, SocketConnectionErrorReason, SocketDisconnectionErrorReason  # Import enums


@dataclass
class EntityGraph:
    """
    Manages a collection of nodes and their interconnections.
    """

    nodes: dict[str, EntityNode] = field(default_factory=dict)  # Modern dict

    def add_node(self, node: EntityNode):
        """Adds a node to the graph."""
        if not isinstance(node, EntityNode):
            raise TypeError("Only Node instances can be added to the graph.")
        if node.id in self.nodes:
            raise ValueError(f"Node with ID '{node.id}' already exists in the graph.")
        self.nodes[node.id] = node
        # print(f"Node '{node.name}' (ID: {node.id}) added to graph.") # Verbose print, can be removed

    def remove_node(self, node_id: str):
        """
        Removes a node from the graph and disconnects all its sockets.
        """
        node_to_remove = self.nodes.pop(node_id, None)
        if not node_to_remove:
            return

        all_sockets_to_disconnect: list[Socket] = []
        all_sockets_to_disconnect.extend(node_to_remove.input_sockets.values())
        all_sockets_to_disconnect.extend(node_to_remove.output_sockets.values())

        for sock_to_clear in all_sockets_to_disconnect:
            connected_sockets_copy = list(sock_to_clear.connections)
            for other_sock in connected_sockets_copy:
                sock_to_clear.remove_connection(other_sock)

    def get_node(self, node_id: str) -> EntityNode | None:  # Modern optional type
        """Retrieves a node by its ID, returns None if not found."""
        return self.nodes.get(node_id)

    def _has_path(self, start_node_id: str, end_node_id: str) -> bool:
        """
        Returns True if end_node_id is reachable from start_node_id by following output socket connections.
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
        output_ref is (node_id, socket_name) for the output socket.
        input_ref is (node_id, socket_name) for the input socket.

        Returns:
            A tuple: (bool_success, ReasonEnum | None)
            ReasonEnum can be SocketConnectionErrorReason or GraphObjectErrorReason.
        """
        output_node_id, output_socket_name = output_ref
        input_node_id, input_socket_name = input_ref

        output_node = self.get_node(output_node_id)
        if not output_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        input_node = self.get_node(input_node_id)
        if not input_node:
            return False, GraphObjectErrorReason.NODE_NOT_FOUND

        # Cycle prevention: check if connecting output_node -> input_node would create a cycle
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

        # Socket.add_connection now returns a tuple (bool, SocketConnectionErrorReason | None)
        return input_socket.add_connection(output_socket)

    def disconnect_sockets(
        self, output_ref: tuple[str, str], input_ref: tuple[str, str]
    ) -> tuple[bool, SocketDisconnectionErrorReason | GraphObjectErrorReason | None]:
        """
        Disconnects a specific connection between an output socket and an input socket.
        output_ref is (node_id, socket_name) for the output socket.
        input_ref is (node_id, socket_name) for the input socket.

        Returns:
            A tuple: (bool_success, ReasonEnum | None)
            ReasonEnum can be SocketDisconnectionErrorReason or GraphObjectErrorReason.
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
        # No direction check needed for disconnect, as long as sockets exist

        input_socket = input_node.input_sockets.get(input_socket_name)
        if not input_socket:
            return False, GraphObjectErrorReason.SOCKET_NOT_FOUND
        # No direction check needed for disconnect

        # Socket.remove_connection is bidirectional and now returns (bool, SocketDisconnectionErrorReason | None)
        return input_socket.remove_connection(output_socket)

    def __repr__(self) -> str:
        return f"Graph(nodes_count={len(self.nodes)})"
