from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .node import Node  # Forward reference for type hinting


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

    def can_connect_to(self, other_socket: "Socket") -> bool:
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
        """
        if self == other_socket:
            return False
        if self.direction == other_socket.direction:
            return False
        if self.parent_node == other_socket.parent_node:
            return False

        # Determine which socket is output and which is input for type checking
        output_socket = self if self.direction == SocketDirection.OUTPUT else other_socket
        input_socket = other_socket if self.direction == SocketDirection.OUTPUT else self

        if not (output_socket.direction == SocketDirection.OUTPUT and input_socket.direction == SocketDirection.INPUT):
            # This case should ideally not be reached if directions are opposite, but as a safeguard:
            return False

        # Type compatibility check
        can_types_connect = False
        if output_socket.data_type == Any or input_socket.data_type == Any:
            can_types_connect = True
        elif isinstance(output_socket.data_type, type) and isinstance(input_socket.data_type, type):
            try:
                # Allow connecting if output type is a subclass of or same as input type
                if issubclass(output_socket.data_type, input_socket.data_type):
                    can_types_connect = True
            except TypeError:
                # issubclass can raise TypeError if args are not classes (e.g. generic aliases like list[int])
                # For now, we'll require exact matches for complex generic types or handle them more specifically later
                if output_socket.data_type == input_socket.data_type:
                    can_types_connect = True
                else:  # Or if one of them is a generic alias that might be compatible
                    pass  # Potentially more advanced logic needed here for generic types like List[int] vs List[Any]

        if not can_types_connect:
            return False

        # Input sockets can generally only have one connection.
        # (This check applies to the one being connected TO if it's an input)
        if (
            input_socket.is_connected() and input_socket not in self.connections
        ):  # if input is already connected to something else
            return False
        # Also check from the perspective of 'self' if 'self' is an input socket.
        if self.direction == SocketDirection.INPUT and self.is_connected() and other_socket not in self.connections:
            return False

        return True

    def add_connection(self, other_socket: "Socket") -> bool:
        """
        Connects this socket to another socket if compatible.
        Ensures bidirectional connection.
        Returns True if connection was successful, False otherwise.
        """
        if self.can_connect_to(other_socket):
            if other_socket not in self.connections:
                self.connections.append(other_socket)
            if self not in other_socket.connections:
                other_socket.connections.append(self)
            return True
        return False

    def remove_connection(self, other_socket: "Socket"):
        """Removes a connection to another socket."""
        if other_socket in self.connections:
            self.connections.remove(other_socket)
        if self in other_socket.connections:
            other_socket.connections.remove(self)

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
