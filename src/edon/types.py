from typing import Any, Protocol
from dataclasses import dataclass
from enum import Enum, auto


class SocketRole(Enum):
    """Defines the direction of a socket, either Input or Output."""

    SOURCE = 1
    TARGET = 2


@dataclass(frozen=True)
class SocketAddress:
    """Represents a unique socket endpoint within the graph, identifying an entity socket.

    It is defined by `node_id`, the unique identifier of its parent node, and
    `socket_name`, the name of the socket on that node.
    """

    node_id: str
    name: str
    role: SocketRole


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

    def __str__(self) -> str:
        return f"{self.name} (Python: {self.python_type.__name__})"


class SocketDisplayState(Enum):
    ALL = auto()
    LINK_LABEL = auto()
    LINK_WIDGET = auto()
    LABEL = auto()
    WIDGET = auto()


@dataclass
class SocketDef:
    """
    Defines the specification for a socket to be created on a node.
    This is used during node initialization.
    """

    name: str
    socket_type: SocketType
    default: Any = None
    display_state: SocketDisplayState = SocketDisplayState.LINK_LABEL

    @property
    def python_type(self) -> type[Any]:
        """Convenience property to access the Python data type."""
        return self.socket_type.python_type

    @property
    def visual_key_for_widget_factory(self) -> SocketType:
        """Convenience property; the enum member itself is the key."""
        return self.socket_type

    def __repr__(self):
        return (
            f"SocketDef(name='{self.name}', socket_type='{self.socket_type.name}', "
            f"python_type={self.python_type.__name__}, "
            f"display_state={self.display_state.name}, default={self.default!r})"
        )


@dataclass(frozen=True)
class EdgeKey:
    """Uniquely identifies an edge by its source and target socket addresses.

    It is defined by its `source` and `target` `SocketAddress` instances,
    representing the two endpoints of the connection.
    """

    source: SocketAddress
    target: SocketAddress


class ProcessableNode(Protocol):
    """A protocol for nodes that define a core processing logic.

    This protocol ensures that conforming objects (typically `EntityNode` subclasses)
    implement a `process` method, which is called by the execution engine
    to perform the node's primary computation or action.
    """

    def process(self) -> None:
        """
        The core computational logic of the node. Returns None.

        This method is intended to be overridden by concrete node implementations
        to define their specific behavior. It typically involves:
        1. Accessing input sockets via `self.source_sockets`.
        2. Retrieving input values (respecting their `data_type` as defined by
           the node's `SocketDef`s).
        3. Performing computations.
        4. Setting output values on `self.target_sockets` (again, respecting
           their `data_type`).

        The method signature is `-> None` because data is read from and written
        to the node's own `EntitySocket` instances, which manage type compatibility
        at the connection level. The `process` method itself orchestrates this
        internal data flow based on the node's defined socket types.
        """
        ...
