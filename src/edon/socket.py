from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Type, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from .node import EntityNode  # Forward reference for type hinting
from .errors import SocketConnectionErrorReason, SocketDisconnectionErrorReason


class SocketDirection(Enum):
    """Defines the direction of a socket, either Input or Output."""

    INPUT = 1
    OUTPUT = 2


@dataclass
class EntitySocket:
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
    parent_node: "EntityNode"
    data_type: Type[Any] = Any  # Default to wildcard type
    connections: list["EntitySocket"] = field(default_factory=list)
    value: Any = None

    def __post_init__(self):
        """Post-initialization checks."""
        if not isinstance(self.name, str) or not self.name.strip():
            logger.error("Socket __post_init__: Socket name must be a non-empty string.")
            raise ValueError("Socket name must be a non-empty string.")
        if not isinstance(self.direction, SocketDirection):
            logger.error("Socket __post_init__: Socket direction must be a SocketDirection enum member.")
            raise ValueError("Socket direction must be a SocketDirection enum member.")
        if not isinstance(self.data_type, type) and self.data_type != Any:
            logger.error(
                f"Socket __post_init__: Socket data_type must be a type object or typing.Any, got {self.data_type}"
            )
            raise ValueError(f"Socket data_type must be a type object or typing.Any, got {self.data_type}")

    def is_connected(self) -> bool:
        """Checks if the socket is connected to any other socket."""
        return bool(self.connections)

    def can_connect_to(self, other_socket: "EntitySocket") -> tuple[bool, SocketConnectionErrorReason | None]:
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

        # The Graph.connect_sockets method will handle overwriting (disconnecting old edge)
        # if a new connection is made to an already connected input socket.
        # Therefore, can_connect_to should not block based on INPUT_SOCKET_FULL.

        return True, None

    def add_connection(self, other_socket: "EntitySocket") -> tuple[bool, SocketConnectionErrorReason | None]:
        """
        Connects this socket to another socket if compatible.
        Ensures bidirectional connection.
        Returns:
            A tuple: (bool_success, SocketConnectionErrorReason | None)
        """
        # Check compatibility first
        can_connect_flag, reason = self.can_connect_to(other_socket)
        logger.debug(
            f"Socket '{self.name}' add_connection to '{other_socket.name}': can_connect_to returned {can_connect_flag}, reason: {reason}"
        )
        if not can_connect_flag:
            return False, reason

        # If already connected, it's a success (idempotent)
        if other_socket in self.connections and self in other_socket.connections:
            logger.debug(f"Socket '{self.name}' add_connection to '{other_socket.name}': Already connected.")
            return True, None

        # Graph.connect_sockets is responsible for handling overwrites (disconnecting old connections
        # from an input socket if a new one is made). Socket.add_connection should simply add.

        if other_socket not in self.connections:
            self.connections.append(other_socket)
        if self not in other_socket.connections:
            other_socket.connections.append(self)
        logger.debug(f"Socket '{self.name}' successfully added connection to '{other_socket.name}'")
        return True, None

    def remove_connection(self, other_socket: "EntitySocket") -> tuple[bool, SocketDisconnectionErrorReason | None]:
        """Removes a connection to another socket.
        Returns:
            A tuple: (bool_success, SocketDisconnectionErrorReason | None)
        """
        removed_from_self = False
        if other_socket in self.connections:
            self.connections.remove(other_socket)
            removed_from_self = True

        removed_from_other = False
        if self in other_socket.connections:
            other_socket.connections.remove(self)
            removed_from_other = True
            logger.debug(
                f"Socket '{self.name}' remove_connection: Removed self from '{other_socket.name}'.connections."
            )

        if removed_from_self or removed_from_other:
            logger.debug(
                f"Socket '{self.name}' remove_connection from '{other_socket.name}': Success. Self removed: {removed_from_self}, Other removed: {removed_from_other}"
            )
            return True, None  # Success if at least one side was cleaned up
        else:
            # If neither contained the other, they weren't connected
            logger.warning(
                f"Socket '{self.name}' remove_connection from '{other_socket.name}': Sockets were not connected."
            )
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
