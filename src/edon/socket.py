"""Defines the `EntitySocket` class, representing connection points on nodes.

This module provides `EntitySocket`, the core component for defining data input
and output points on `EntityNode` instances within the `EntityGraph`. Sockets
are responsible for managing their data type, current value, and connections
to other sockets.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from edon.types import SocketAddress, SocketRole, SocketType, current_graph_context

if TYPE_CHECKING:
    from edon.node import EntityNode


@dataclass
class EntitySocket:
    """
    Pure data representation of a socket connection point on a Node.

    This class only holds data and computed properties. All connection
    management and validation logic is handled by EntityGraph.
    """

    name: str
    role: SocketRole
    node: EntityNode
    type_info: SocketType
    default_value: Any | None = None
    _value: Any | None = field(init=False)

    def __post_init__(self) -> None:
        self._value = self.default_value

    @property
    def data_type(self) -> type[Any]:
        """The Python data type this socket handles, for connection compatibility."""
        return self.type_info.python_type

    @property
    def address(self) -> SocketAddress:
        """Computed socket address for this socket."""
        return SocketAddress(self.node.id, self.name, self.role)

    @property
    def value(self) -> Any:
        # SOURCE sockets are the one we are pulling from, we are not pushing.
        if self.role == SocketRole.SOURCE:
            return self._value

        # Without a proper graph context set we can't figure out our links, a socket
        # needs this context to find it's partner.
        active_graph = current_graph_context.get()
        if active_graph:
            # If we don't find a link here, it just means that the socket doesn't have any
            # links, and we can return the default value, if set.
            source_socket = active_graph.get_source_socket_for_target(self.address)
            if source_socket is not None:
                return source_socket._value

        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        self._value = value

    def __repr__(self) -> str:
        parent_node_repr = self.node.name
        data_type_repr = self.data_type.__name__ if self.data_type != Any else "Any"
        if not isinstance(self.data_type, type) and self.data_type is not Any:
            data_type_repr = str(self.data_type)

        return (
            f"Socket(name='{self.name}', direction={self.role.name}, "
            f"data_type={data_type_repr}, parent_node='{parent_node_repr}')"
        )
