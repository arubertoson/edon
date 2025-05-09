import uuid
from dataclasses import dataclass, field
from typing import Any, Type

# Assuming socket.py is in the same directory or accessible in PYTHONPATH
from edon.socket import Socket, SocketDirection


@dataclass
class Node:
    """
    Represents a single node in the node editor graph.
    Nodes manage their input and output sockets. Subclasses will define
    the core processing logic.

    Attributes:
        name: Display name of the node.
        node_type: A string identifier for the type of this node (e.g., "math.add", "file.text_loader").
                   Can be used for categorization (e.g., "category.node_operation").
        input_socket_definitions: Declarations for input sockets, as a list of (name, data_type) tuples.
                                  Used by __post_init__ to create actual Socket objects.
        output_socket_definitions: Declarations for output sockets, as a list of (name, data_type) tuples.
                                   Used by __post_init__ to create actual Socket objects.
        id: Unique identifier for the node instance.
        input_sockets: Dictionary of input Socket objects, keyed by name, created from definitions.
        output_sockets: Dictionary of output Socket objects, keyed by name, created from definitions.
    """

    name: str
    node_type: str
    input_socket_definitions: list[tuple[str, Type[Any]]] = field(default_factory=list)
    output_socket_definitions: list[tuple[str, Type[Any]]] = field(default_factory=list)

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_sockets: dict[str, Socket] = field(default_factory=dict, init=False)
    output_sockets: dict[str, Socket] = field(default_factory=dict, init=False)

    def __post_init__(self):
        """Initializes sockets based on definitions."""
        for sock_name, sock_type in self.input_socket_definitions:
            self._add_socket_internal(sock_name, SocketDirection.INPUT, sock_type)
        for sock_name, sock_type in self.output_socket_definitions:
            self._add_socket_internal(sock_name, SocketDirection.OUTPUT, sock_type)

    def _add_socket_internal(
        self, name: str, direction: SocketDirection, data_type: Type[Any], value: Any = None
    ) -> Socket:
        """
        Internal method to create and add a socket to the node.
        The `parent_node` for the socket is automatically set to this node instance.
        """
        if name in self.input_sockets or name in self.output_sockets:
            raise ValueError(f"Socket with name '{name}' already exists on node '{self.name}'.")

        socket_instance = Socket(name=name, direction=direction, parent_node=self, data_type=data_type, value=value)
        if direction == SocketDirection.INPUT:
            self.input_sockets[name] = socket_instance
        else:  # SocketDirection.OUTPUT
            self.output_sockets[name] = socket_instance
        return socket_instance

    def process(self):
        """
        The core computational logic of the node.
        This method MUST be overridden by subclasses to define the node's behavior.

        Subclasses should:
        1. Access input sockets via `self.input_sockets['socket_name']`.
        2. To get a value from an input socket:
           - Check `input_socket.is_connected()`.
           - If connected, get the value from `input_socket.connections[0].value`
             (assuming the upstream node has processed and set its output socket's value,
              and assuming single connection for inputs).
           - If not connected, use `input_socket.value` (for defaults).
        3. Set output values directly on output sockets:
           `self.output_sockets['socket_name'].value = result_value`.
        """
        raise NotImplementedError("Subclasses must implement the process() method.")

    def __repr__(self) -> str:
        return (
            f"Node(name='{self.name}', type='{self.node_type}', id='{self.id}', "
            f"inputs={list(self.input_sockets.keys())}, outputs={list(self.output_sockets.keys())})"
        )

    def get_input_socket(self, name: str) -> Socket:
        """Returns the specified input socket."""
        if name not in self.input_sockets:
            raise KeyError(f"Node '{self.name}' has no input socket named '{name}'.")
        return self.input_sockets[name]

    def get_output_socket(self, name: str) -> Socket:
        """Returns the specified output socket."""
        if name not in self.output_sockets:
            raise KeyError(f"Node '{self.name}' has no output socket named '{name}'.")
        return self.output_sockets[name]
