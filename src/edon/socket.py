from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node  # Forward reference for type hinting
from .errors import SocketConnectionErrorReason, SocketDisconnectionErrorReason


class SocketDirection(Enum):
    """Defines the direction of a socket, either Input or Output."""

    INPUT = 1
    OUTPUT = 2


@dataclass
class Socket:
    """
    Represents a connection point on a Node for data input or output.

    Attributes:
        name: The display name of the socket.
        direction: The direction of the socket (INPUT or OUTPUT).
        parent_node: The Node this socket belongs to.
        data_type: The Python type this socket handles (e.g., int, str, list,
                   a custom class, or typing.Any for a wildcard).
        connections: A list of other Sockets this socket is connected to.
        value: The current data value held by this socket.
    """

    name: str
    direction: SocketDirection
    parent_node: "Node"
    data_type: Type[Any] = Any  # Default to wildcard type
    connections: list["Socket"] = field(default_factory=list)
    value: Any = None

    def __post_init__(self):
        """Post-initialization checks."""
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Socket name must be a non-empty string.")
        if not isinstance(self.direction, SocketDirection):
            raise ValueError("Socket direction must be a SocketDirection enum member.")
        # parent_node type check will be more effective once Node is defined.
        if not isinstance(self.data_type, type) and self.data_type != Any:
            raise ValueError(f"Socket data_type must be a type object or typing.Any, got {self.data_type}")

    def is_connected(self) -> bool:
        """Checks if the socket is connected to any other socket."""
        return bool(self.connections)

    def can_connect_to(self, other_socket: "Socket") -> tuple[bool, SocketConnectionErrorReason | None]:
        """
        Determines if this socket can connect to another socket.
        Rules:
        1. Cannot connect to itself.
        2. Directions must be opposite.
        3. Cannot connect if the other socket belongs to the same parent node.
        4. Data types must be compatible:
           - If one is INPUT and other is OUTPUT:
             Output's data_type must be a subtype of Input's data_type,
             or either type is typing.Any.
        5. Input sockets are limited to one connection by default.
        Returns:
            A tuple: (bool_success, SocketConnectionErrorReason | None)
        """
        if not other_socket:
            return False, SocketConnectionErrorReason.TARGET_SOCKET_INVALID

        if self == other_socket:
            return False, SocketConnectionErrorReason.CANNOT_CONNECT_TO_SELF
        if self.direction == other_socket.direction:
            return False, SocketConnectionErrorReason.DIRECTIONS_NOT_OPPOSITE
        if self.parent_node == other_socket.parent_node:
            return False, SocketConnectionErrorReason.SAME_PARENT_NODE

        # Determine which socket is output and which is input for type checking
        output_socket = self if self.direction == SocketDirection.OUTPUT else other_socket
        input_socket = other_socket if self.direction == SocketDirection.OUTPUT else self

        if not (output_socket.direction == SocketDirection.OUTPUT and input_socket.direction == SocketDirection.INPUT):
            return False, SocketConnectionErrorReason.DIRECTIONS_NOT_OPPOSITE

        # Type compatibility check
        can_types_connect = False
        if output_socket.data_type == Any or input_socket.data_type == Any:
            can_types_connect = True
        elif isinstance(output_socket.data_type, type) and isinstance(input_socket.data_type, type):
            try:
                if issubclass(output_socket.data_type, input_socket.data_type):
                    can_types_connect = True
            except TypeError:
                if output_socket.data_type == input_socket.data_type:
                    can_types_connect = True

        if not can_types_connect:
            return False, SocketConnectionErrorReason.TYPE_MISMATCH

        # Input sockets can generally only have one connection.
        if self.direction == SocketDirection.INPUT and self.is_connected():
            if not (len(self.connections) == 1 and other_socket in self.connections):
                return False, SocketConnectionErrorReason.INPUT_SOCKET_FULL

        if other_socket.direction == SocketDirection.INPUT and other_socket.is_connected():
            if not (len(other_socket.connections) == 1 and self in other_socket.connections):
                return False, SocketConnectionErrorReason.INPUT_SOCKET_FULL

        return True, None

    def add_connection(self, other_socket: "Socket") -> tuple[bool, SocketConnectionErrorReason | None]:
        """
        Connects this socket to another socket if compatible.
        Ensures bidirectional connection.
        Returns:
            A tuple: (bool_success, SocketConnectionErrorReason | None)
        """
        # Check compatibility first
        can_connect_flag, reason = self.can_connect_to(other_socket)
        if not can_connect_flag:
            return False, reason

        # If already connected, it's a success (idempotent)
        if other_socket in self.connections and self in other_socket.connections:
            return True, None

        # Proceed with connection
        # Input socket specific check for arity (should be covered by can_connect_to, but good as a safeguard before modification)
        # Considering `self` is the one on which `add_connection` is called (typically an input socket by convention from Graph.connect_sockets)
        if self.direction == SocketDirection.INPUT and self.is_connected():
            # This means self is an input, is_connected, but other_socket was not in its connections
            # (otherwise the previous check would have caught it). This implies trying to add a second distinct connection.
            return False, SocketConnectionErrorReason.INPUT_SOCKET_FULL

        # Vice-versa for other_socket if it's an input
        if other_socket.direction == SocketDirection.INPUT and other_socket.is_connected():
            return False, SocketConnectionErrorReason.INPUT_SOCKET_FULL

        if other_socket not in self.connections:
            self.connections.append(other_socket)
        if self not in other_socket.connections:
            other_socket.connections.append(self)
        return True, None

    def remove_connection(self, other_socket: "Socket") -> tuple[bool, SocketDisconnectionErrorReason | None]:
        """Removes a connection to another socket.
        Returns:
            A tuple: (bool_success, SocketDisconnectionErrorReason | None)
        """
        if not other_socket:
            # This case should ideally not be hit if logic is sound elsewhere, but good to have.
            return False, SocketDisconnectionErrorReason.UNKNOWN

        removed_from_self = False
        if other_socket in self.connections:
            self.connections.remove(other_socket)
            removed_from_self = True

        removed_from_other = False
        if self in other_socket.connections:
            other_socket.connections.remove(self)
            removed_from_other = True

        if removed_from_self or removed_from_other:
            return True, None  # Success if at least one side was cleaned up
        else:
            # If neither contained the other, they weren't connected
            return False, SocketDisconnectionErrorReason.SOCKETS_NOT_CONNECTED

    def __repr__(self) -> str:
        parent_node_repr = "Detached"
        if hasattr(self, "parent_node") and self.parent_node is not None:
            try:
                parent_node_repr = self.parent_node.name if hasattr(self.parent_node, "name") else "UnnamedNode"
            except AttributeError:  # Should not happen if Node has 'name'
                parent_node_repr = "UnnamedNode"

        data_type_repr = self.data_type.__name__ if self.data_type != Any else "Any"
        if (
            not isinstance(self.data_type, type) and self.data_type is not Any
        ):  # e.g. for typing._GenericAlias like list[int]
            data_type_repr = str(self.data_type)

        return (
            f"Socket(name='{self.name}', direction={self.direction.name}, "
            f"data_type={data_type_repr}, parent_node='{parent_node_repr}', "
            f"connections_count={len(self.connections)})"
        )
