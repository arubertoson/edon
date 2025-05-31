"""Defines the `EntitySocket` class, representing connection points on nodes.

This module provides `EntitySocket`, the core component for defining data input
and output points on `EntityNode` instances within the `EntityGraph`. Sockets
are responsible for managing their data type, current value, and connections
to other sockets.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

from edon.errors import SocketLinkErrorReason
from edon.types import SocketAddress, SocketRole, SocketType

if TYPE_CHECKING:
    from edon.node import EntityNode


@dataclass
class EntitySocket:
    """
    Represents a connection point on a Node for data input or output.
    """

    name: str
    role: SocketRole
    node: EntityNode
    type_info: SocketType
    value: Any | None = None
    links: list[EntitySocket] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._address: SocketAddress | None = None

    @property
    def data_type(self) -> type[Any]:
        """The Python data type this socket handles, for connection compatibility."""
        return self.type_info.python_type

    @property
    def address(self) -> SocketAddress:
        if self._address is None:
            self._address = SocketAddress(self.node.id, self.name, self.role)
        return self._address

    def is_linked(self) -> bool:
        """Checks if the socket is connected to any other socket.

        Returns:
            True if the socket has one or more connections, False otherwise.
        """
        return bool(self.links)

    def can_link_to(self, target: EntitySocket) -> tuple[bool, SocketLinkErrorReason | None]:
        """
        Determines if this socket can connect to another socket based on a set of rules.
        """
        if self == target:
            return False, SocketLinkErrorReason.CANNOT_LINK_TO_SELF
        if self.role == target.role:
            return False, SocketLinkErrorReason.DIRECTIONS_NOT_OPPOSITE
        if self.node == target.node:
            return False, SocketLinkErrorReason.SAME_PARENT_NODE
        if target in self.links and self in target.links:
            return True, SocketLinkErrorReason.ALREADY_LINKED

        # Determine which socket is output and which is input for type checking
        source = self if self.role == SocketRole.TARGET else target
        target = target if self.role == SocketRole.TARGET else self

        # Check for type compatibility, allowing Any or matching/subclass relationships.
        types_are_compatible = False
        if source.data_type == Any or target.data_type == Any:
            types_are_compatible = True
        elif isinstance(source.data_type, type) and isinstance(target.data_type, type):
            if issubclass(source.data_type, target.data_type):
                types_are_compatible = True

        if not types_are_compatible:
            return False, SocketLinkErrorReason.TYPE_MISMATCH

        return True, None

    def link_to(self, target: EntitySocket) -> tuple[bool, SocketLinkErrorReason | None]:
        """
        Link this socket to another socket if compatible, ensuring a bidirectional link.

        This method first checks if the target is linkable using the internal rule set.
        If compatible, it adds the other socket to its link list and itself to the
        target's list. The method is idempotent: if already connected, it returns success
        without changes.
        """
        can_link_flag, reason = self.can_link_to(target)
        if not can_link_flag or (can_link_flag and reason):  # Either can't link or already linked
            return False, reason

        self.links.append(target)
        target.links.append(self)

        logger.debug(f"Socket '{self.name}' successfully linked to '{target.name}'")
        return True, None

    def unlink_from(self, target: EntitySocket) -> None:
        """
        Removes a connection to another socket, ensuring the link is broken bidirectionally.
        """
        assert self in target.links and target in self.links, (
            f"CORRUPTION: Trying to unlink sockets that doesn't have a link {self.address}::{target.address}"
        )

        self.links.remove(target)
        target.links.remove(self)

    def __repr__(self) -> str:
        parent_node_repr = self.node.name
        data_type_repr = self.data_type.__name__ if self.data_type != Any else "Any"
        if not isinstance(self.data_type, type) and self.data_type is not Any:
            data_type_repr = str(self.data_type)

        return (
            f"Socket(name='{self.name}', direction={self.role.name}, "
            f"data_type={data_type_repr}, parent_node='{parent_node_repr}', "
            f"connections_count={len(self.links)})"
        )
