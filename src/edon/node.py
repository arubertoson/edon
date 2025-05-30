"""Defines the core `EntityNode` class and related structures for the Edon graph.

This module provides the `EntityNode`, which is the base representation for all
nodes within the `EntityGraph`. Nodes are the primary computational units and
data containers in the graph. They manage their input and output sockets
(`EntitySocket` instances) and encapsulate specific processing logic.

The design facilitates a declarative approach for creating custom node types:
users can subclass `EntityNode` and define class-level attributes for `name`,
`node_type`, and lists of `SocketDef` objects to specify `source_socket_definitions`
and `target_socket_definitions`. The `EntityNode`'s `__post_init__` method
handles the instantiation of these sockets.

"""

from enum import Enum, auto
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from edon.socket import EntitySocket, SocketRole, SocketType


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


@dataclass
class EntityNode:
    """
    Represents a single node in the node editor graph. Nodes manage their input and output sockets
    and define core processing logic.

    Subclasses can be defined declaratively by setting class attributes:

    - `name: str` (optional): Defaults to the subclass name (e.g., "MyNode" -> "My").
    - `node_type: str` (optional): Defaults to the subclass name lowercased (e.g., "MyNode" -> "my").
    - `source_socket_definitions: list[SocketDef]` (optional): Defines input sockets.
    - `target_socket_definitions: list[SocketDef]` (optional): Defines output sockets.

    Example:
        ```python
        class MySimpleNode(EntityNode):
            node_type = "custom.simple"
            target_socket_definitions = [SocketDef(name="result", type=int, default=0)]

            def process(self):
                self.target_sockets["result"].value = 42
        ```

    Attributes:
        name (str | None): Display name of the node. If None, resolved from class name.
        node_type (str | None): String identifier for the type of this node. If None, resolved from class name.
        source_socket_definitions (list[SocketDef] | None): Instance definitions passed at creation.
                                                        Defaults to `None` to enable class attribute fallback.
        target_socket_definitions (list[SocketDef] | None): Instance definitions passed at creation.
                                                         Defaults to `None` to enable class attribute fallback.
        id (str): Unique identifier for the node instance.
        source_sockets (dict[str, EntitySocket]): Dictionary of created input Socket objects.
        target_sockets (dict[str, EntitySocket]): Dictionary of created output Socket objects.
    """

    # --- Instance Attributes (can be passed via __init__ generated by @dataclass) ---
    # These allow overriding class attributes or direct instantiation without subclassing.
    name: str | None = field(default=None)
    node_type: str | None = field(default=None)

    # Socket definitions default to `None` at the instance level.
    # This allows `__post_init__` to distinguish between "not provided" (use class attr)
    # and "provided as empty list []" (use the empty list).
    source_socket_definitions: list[SocketDef] | None = field(default=None)
    target_socket_definitions: list[SocketDef] | None = field(default=None)

    # --- Internal Attributes ---
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_sockets: dict[str, EntitySocket] = field(default_factory=dict, init=False)
    target_sockets: dict[str, EntitySocket] = field(default_factory=dict, init=False)

    def __post_init__(self):
        """Finalizes node initialization after dataclass setup.

        This method resolves the node's actual name, type, and socket definitions
        by considering instance attributes, then class attributes, and finally
        applying defaults. It then creates the socket instances.
        """
        cls = self.__class__

        # --- Determine Final Configuration ---
        # Priority: Instance Value -> Class Attribute -> Default
        self.name = cls.name or cls.__name__.replace("Node", "")
        self.node_type = cls.node_type or cls.__name__.lower().replace("node", "")

        # Resolve source_socket_definitions: Use instance `self.input_socket_definitions` if provided (i.e., not None),
        # otherwise, try the class attribute `self.__class__.source_socket_definitions`, else default to an empty list.
        # This allows subclasses to define sockets purely via class attributes.
        source_defs: list[SocketDef] = (
            self.source_socket_definitions
            if self.source_socket_definitions is not None
            else getattr(cls, "source_socket_definitions", [])
        )
        target_defs: list[SocketDef] = (
            self.target_socket_definitions
            if self.target_socket_definitions is not None
            else getattr(cls, "target_socket_definitions", [])
        )

        # --- Create Sockets ---
        # Iterate using the final resolved definitions determined above.
        for sock_def in target_defs:
            self._add_socket_internal(sock_def, SocketRole.TARGET)
        for sock_def in source_defs:
            self._add_socket_internal(sock_def, SocketRole.SOURCE)

    def _add_socket_internal(
        self,
        socket_def: SocketDef,
        role: SocketRole,
    ) -> EntitySocket:
        """
        Internal method to create and add a socket to the node.

        The `parent_node` for the socket is automatically set to this node instance.
        """
        if socket_def.name in self.source_sockets or socket_def.name in self.target_sockets:
            raise ValueError(f"Socket with name '{socket_def.name}' already exists on node '{self.name}'.")

        socket_instance = EntitySocket(
            name=socket_def.name,
            role=role,
            node=self,
            type_info=socket_def.socket_type,
            value=socket_def.default,
        )

        if role == SocketRole.SOURCE:
            self.source_sockets[socket_instance.name] = socket_instance
        else:
            self.target_sockets[socket_instance.name] = socket_instance
        return socket_instance

    def process(self):
        """
        The core computational logic of the node. Returns None.

        This method MUST be overridden by subclasses to define the node's behavior.
        It is called by the `ExecutionEngine` when the node is ready to be processed.

        Subclasses should typically:
        1. Access input sockets via `self.source_sockets['socket_name']`.
        2. Get input values:
           - Check `socket.is_connected()`.
           - If connected, access the value from the connected output socket,
             typically via `socket.connections[0].value`. The `ExecutionEngine`
             ensures upstream nodes are processed first.
           - If not connected, use the input socket's own `socket.value` as a
             default or based on node logic.
           - Ensure operations respect the `data_type` of the socket.
        3. Compute results based on these input values and the node's purpose.
        4. Set output values directly on output sockets:
           `self.target_sockets['socket_name'].value = result_value`.
           - Ensure the `result_value` is compatible with the output socket's `data_type`.

        The method signature is `-> None` because data is read from and written
        to the node's own `EntitySocket` instances. These sockets handle data type
        management and connection compatibility. The `process` method orchestrates
        the node's internal data transformation and state changes.
        """
        raise NotImplementedError(f"Node class '{self.__class__.__name__}' must implement the process() method.")

    def __repr__(self) -> str:
        return (
            f"Node(name='{self.name}', type='{self.node_type}', id='{self.id}', "
            f"sources={list(self.source_sockets.keys())}, targets={list(self.target_sockets.keys())})"
        )
