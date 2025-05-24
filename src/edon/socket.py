"""Defines the `EntitySocket` class, representing connection points on nodes.

This module provides `EntitySocket`, the core component for defining data input
and output points on `EntityNode` instances within the `EntityGraph`. Sockets
are responsible for managing their data type, current value, and connections
to other sockets.

"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Type, TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from .node import EntityNode  # Forward reference for type hinting
from .errors import SocketLinkErrorReason, SocketUnlinkErrorReason


class SocketRole(Enum):
    """Defines the direction of a socket, either Input or Output."""

    SOURCE = 1
    TARGET = 2


class SocketType(Enum):
    """
    Defines the comprehensive type of a socket, including its underlying
    Python data type and a key for its visual/widget representation.

    The enum member itself serves as the primary key for widget factories.
    The `value` tuple stores (python_data_type, description)
    """

    INTEGER = (int, "integer")
    FLOAT = (float, "float")
    STRING = (str, "string")
    LARGE_STRING = (str, "large_string")

    @property
    def python_type(self) -> type[Any]:
        """The underlying Python data type for this socket type (e.g., int, str)."""
        return self.value[0]

    @property
    def description(self) -> str:
        """A simple tag for debugging or logging, not typically used as a key."""
        return self.value[1]

    def __str__(self):
        return f"{self.name} (Python: {self.python_type.__name__})"


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
    role: SocketRole
    node: "EntityNode"
    type_info: SocketType
    links: list["EntitySocket"] = field(default_factory=list)
    value: Any | None = None

    def __post_init__(self):
        """Performs validation checks after instance initialization.

        Ensures that the socket has a valid name, direction, and data_type.

        Raises:
            ValueError: If name is empty, direction is invalid, or data_type is invalid.
        """
        if not isinstance(self.name, str) or not self.name.strip():
            logger.error("Socket __post_init__: Socket name must be a non-empty string.")
            raise ValueError("Socket name must be a non-empty string.")
        if not isinstance(self.role, SocketRole):
            logger.error("Socket __post_init__: Socket direction must be a SocketDirection enum member.")
            raise ValueError("Socket direction must be a SocketDirection enum member.")
        if not isinstance(self.type_info, SocketType):
            logger.error(f"EntitySocket: data_type={self.data_type!r} (type={type(self.data_type)})")
            logger.error(
                f"Socket __post_init__: Socket data_type must be a type object or typing.Any, got {self.data_type}"
            )
            raise ValueError(f"Socket data_type must be a type object or typing.Any, got {self.data_type}")

    @property
    def data_type(self) -> type[Any]:
        """The Python data type this socket handles, for connection compatibility."""
        return self.type_info.python_type

    def is_linked(self) -> bool:
        """Checks if the socket is connected to any other socket.

        Returns:
            True if the socket has one or more connections, False otherwise.
        """
        return bool(self.links)

    def can_link_to(self, target: "EntitySocket") -> tuple[bool, SocketLinkErrorReason | None]:
        """
        Determines if this socket can connect to another socket based on a set of rules.

        Rules:
        1. Cannot connect to itself.
        2. Directions must be opposite.
        3. Cannot connect if the other socket belongs to the same parent node.
        4. Data types must be compatible (output is subtype of input, or Any is involved).
        5. Input sockets are limited to one connection by default (this rule is now primarily
           enforced by the Graph when overwriting connections, not strictly blocking here).

        Args:
            other_socket: The other EntitySocket instance to check for connectability.

        Returns:
            A tuple: (can_connect: bool, reason: SocketConnectionErrorReason | None).
            `can_connect` is True if connection is possible, False otherwise.
            `reason` provides an error enum if `can_connect` is False, else None.
        """
        if self == target:
            return False, SocketLinkErrorReason.CANNOT_LINK_TO_SELF
        if self.role == target.role:
            return False, SocketLinkErrorReason.DIRECTIONS_NOT_OPPOSITE
        if self.node == target.node:
            return False, SocketLinkErrorReason.SAME_PARENT_NODE

        # Determine which socket is output and which is input for type checking
        source = self if self.role == SocketRole.TARGET else target
        target = target if self.role == SocketRole.TARGET else self

        source_py_type = source.data_type
        target_py_type = target.data_type

        # Check for type compatibility, allowing Any or matching/subclass relationships.
        types_are_compatible = False
        if source.data_type == Any or target.data_type == Any:
            types_are_compatible = True
        elif isinstance(source.data_type, type) and isinstance(target.data_type, type):
            try:
                if issubclass(source.data_type, target.data_type):
                    types_are_compatible = True
            except TypeError:
                # issubclass can raise TypeError if one arg is not a class suitable for checking
                # (e.g., some complex typing constructs, though less common with simple types).
                # Fallback to direct equality check in such edge cases.
                if source.data_type == target.data_type:
                    types_are_compatible = True

        if not types_are_compatible:
            return False, SocketLinkErrorReason.TYPE_MISMATCH

        # The Graph.connect_sockets method will handle overwriting (disconnecting old edge)
        # if a new connection is made to an already connected input socket.
        # Therefore, can_connect_to should not block based on INPUT_SOCKET_FULL.
        return True, None

    def link_to(self, target: "EntitySocket") -> tuple[bool, SocketLinkErrorReason | None]:
        """
        Connects this socket to another socket if compatible, ensuring a bidirectional link.

        This method first checks `can_connect_to`. If compatible, it adds the other socket
        to its connections list and itself to the other socket's list. The method is
        idempotent: if already connected, it returns success without changes.

        Args:
            other_socket: The EntitySocket to connect to.

        Returns:
            A tuple: (success: bool, reason: SocketConnectionErrorReason | None).
            `success` is True if the connection was made or already existed.
            `reason` provides an error enum if connection failed, else None.
        """
        can_link_flag, reason = self.can_link_to(target)
        logger.debug(
            f"Socket '{self.name}' add_connection to '{target.name}': can_connect_to returned {can_link_flag}, reason: {reason}"
        )
        if not can_link_flag:
            return False, reason

        if target in self.links and self in target.links:
            logger.debug(f"Socket '{self.name}' link_to '{target.name}': Already connected.")
            return True, SocketLinkErrorReason.ALREADY_LINKED

        # Graph.connect_sockets is responsible for handling overwrites (disconnecting old connections
        # from an input socket if a new one is made). Socket.add_connection should simply add.
        if target not in self.links:
            self.links.append(target)
        if self not in target.links:
            target.links.append(self)

        logger.debug(f"Socket '{self.name}' successfully linked to '{target.name}'")
        return True, None

    def unlink_from(self, target: "EntitySocket") -> tuple[bool, SocketUnlinkErrorReason | None]:
        """Removes a connection to another socket, ensuring the link is broken bidirectionally.

        Args:
            other_socket: The EntitySocket to disconnect from.

        Returns:
            A tuple: (success: bool, reason: SocketDisconnectionErrorReason | None).
            `success` is True if the connection was found and removed from at least one side.
            `reason` is `SOCKETS_NOT_CONNECTED` if they were not connected, else None.
        """
        unlink_from_source = False
        if target in self.links:
            self.links.remove(target)
            unlink_from_source = True

        unlink_from_target = False
        if self in target.links:
            target.links.remove(self)
            unlink_from_target = True

        if unlink_from_source or unlink_from_target:
            logger.debug(
                f"Socket '{self.name}' unlinked from '{target.name}': Success. source removed: {unlink_from_source}, target removed: {unlink_from_target}"
            )
            return True, None
        else:
            logger.warning(f"Socket '{self.name}' unlink from '{target.name}': Sockets were not linked.")
            return False, SocketUnlinkErrorReason.SOCKETS_NOT_LINKED

    def __repr__(self) -> str:
        parent_node_repr = "Detached"
        if hasattr(self, "parent_node") and self.node is not None:
            try:
                parent_node_repr = self.node.name if hasattr(self.node, "name") else "UnnamedNode"
            except AttributeError:  # Should not happen if Node has 'name'
                parent_node_repr = "UnnamedNode"

        data_type_repr = self.data_type.__name__ if self.data_type != Any else "Any"
        if not isinstance(self.data_type, type) and self.data_type is not Any:
            data_type_repr = str(self.data_type)

        return (
            f"Socket(name='{self.name}', direction={self.role.name}, "
            f"data_type={data_type_repr}, parent_node='{parent_node_repr}', "
            f"connections_count={len(self.links)})"
        )
