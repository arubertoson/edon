"""SubGraphNode implementation for hierarchical node graphs.

This module provides the SubGraphNode class, which allows an EntityNode to
encapsulate an entire EntityGraph, creating reusable hierarchical components.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger

from edon.node import EntityNode
from edon.graph import EntityGraph
from edon.socket import EntitySocket
from edon.types import (
    SocketAddress,
    SocketDef,
    SocketRole,
    current_execution_engine_context,
)
from .parameters import ParameterMapping

if TYPE_CHECKING:
    pass  # edon.executor.ExecutionEngine is no longer directly imported for instantiation


@dataclass
class SubGraphNode(EntityNode):
    """A node that encapsulates an entire EntityGraph.

    This node acts as a regular EntityNode in its parent graph, but internally
    contains a complete graph with its own nodes and connections. External
    sockets on this node are mapped to specific sockets within the internal graph.
    """

    internal_graph: EntityGraph = field(default_factory=EntityGraph)

    proxy_target_mappings: dict[str, SocketAddress] = field(default_factory=dict)
    proxy_source_mappings: dict[str, SocketAddress] = field(default_factory=dict)

    # Parameter system - expose internal sockets as configurable parameters
    parameter_mappings: list[ParameterMapping] = field(default_factory=list)
    parameter_values: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initializes the SubGraphNode.

        This involves:
        - Resolving 'name' and 'node_type' using instance, class, or derived values.
          (This logic mirrors EntityNode.__post_init__ for consistency, as
           SubGraphNode does not call super().__post_init__ and manages its sockets
           differently.)
        - Initializing an empty socket dictionary, as sockets are created dynamically
          based on proxy mappings to the internal graph.
        - Creating these proxy sockets.
        """
        cls = self.__class__

        # Resolve 'name': Instance > Class > Derived
        if self.name is None:
            self.name = getattr(cls, "name", None)
            if (
                self.name is None
            ):  # cls is always a subclass of EntityNode (SubGraphNode itself or further subclassed)
                self.name = cls.__name__.replace("Node", "")

        # Resolve 'node_type': Instance > Class > Derived
        if self.node_type is None:
            self.node_type = getattr(cls, "node_type", None)
            if self.node_type is None:  # cls is always a subclass of EntityNode
                self.node_type = cls.__name__.lower().replace("Node", "")

        # SubGraphNode manages its sockets dynamically based on proxy mappings,
        # not from declarative socket_definitions like EntityNode.
        self.sockets = {}
        self._create_proxy_sockets()

    def _create_proxy_sockets(self) -> None:
        """Create sockets based on proxy mappings to internal graph sockets."""

        # Create target (input) proxy sockets
        for proxy_name, internal_addr in self.proxy_target_mappings.items():
            internal_socket = self._get_internal_socket(internal_addr)
            socket_def = SocketDef(
                name=proxy_name,
                socket_type=internal_socket.type_info,
                default=internal_socket.default_value,
            )
            self._add_socket_internal(socket_def, SocketRole.TARGET)

            logger.trace(f"Created target proxy socket '{proxy_name}' -> {internal_addr}")

        # Create source (output) proxy sockets
        for proxy_name, internal_addr in self.proxy_source_mappings.items():
            internal_socket = self._get_internal_socket(internal_addr)
            socket_def = SocketDef(
                name=proxy_name,
                socket_type=internal_socket.type_info,
                default=None,  # Output sockets don't need defaults
            )
            self._add_socket_internal(socket_def, SocketRole.SOURCE)

            logger.trace(f"Created source proxy socket '{proxy_name}' -> {internal_addr}")

    def _get_internal_socket(self, socket_addr: SocketAddress) -> EntitySocket:
        """Get a socket from the internal graph by its address."""
        assert socket_addr.node_id in self.internal_graph.nodes, (
            f"Node '{socket_addr.node_id}' not found in internal graph"
        )

        node = self.internal_graph.nodes[socket_addr.node_id]
        assert socket_addr.name in node.sockets, (
            f"Socket '{socket_addr.name}' not found on node '{socket_addr.node_id}'"
        )

        socket = node.sockets[socket_addr.name]
        assert socket.role == socket_addr.role, (
            f"Socket role mismatch: expected {socket_addr.role}, got {socket.role}"
        )

        return socket

    def add_proxy_socket(
        self, proxy_name: str, internal_addr: SocketAddress, is_input: bool
    ) -> None:
        """Dynamically add a new proxy socket mapping.

        This method allows runtime modification of the sub-graph's external interface
        by exposing additional internal sockets.
        """
        # Validate the internal socket exists
        internal_socket = self._get_internal_socket(internal_addr)

        # Add to appropriate mapping
        if is_input:
            assert internal_addr.role == SocketRole.TARGET, (
                "Input proxy sockets must map to target sockets"
            )
            self.proxy_target_mappings[proxy_name] = internal_addr
        else:
            assert internal_addr.role == SocketRole.SOURCE, (
                "Output proxy sockets must map to source sockets"
            )
            self.proxy_source_mappings[proxy_name] = internal_addr

        # Recreate all sockets to include the new one
        self.sockets.clear()
        self._create_proxy_sockets()

        logger.info(f"Added {'input' if is_input else 'output'} proxy socket '{proxy_name}'")

    def remove_proxy_socket(self, proxy_name: str) -> None:
        """Remove a proxy socket mapping."""
        removed = False

        if proxy_name in self.proxy_target_mappings:
            del self.proxy_target_mappings[proxy_name]
            removed = True

        if proxy_name in self.proxy_source_mappings:
            del self.proxy_source_mappings[proxy_name]
            removed = True

        assert removed, f"Proxy socket '{proxy_name}' not found"

        # Recreate sockets without the removed one
        self.sockets.clear()
        self._create_proxy_sockets()

        logger.info(f"Removed proxy socket '{proxy_name}'")

    def expose_socket_as_parameter(self, socket_addr: SocketAddress, param_name: str) -> None:
        """Expose an internal socket as a configurable parameter."""
        internal_socket = self._get_internal_socket(socket_addr)

        # Check if parameter name already exists
        existing_names = {mapping.parameter_name for mapping in self.parameter_mappings}
        assert param_name not in existing_names, f"Parameter '{param_name}' already exists"

        # Add parameter mapping
        mapping = ParameterMapping(parameter_name=param_name, target_socket_addr=socket_addr)
        self.parameter_mappings.append(mapping)

        # Set initial value from socket default
        self.parameter_values[param_name] = internal_socket.value

        logger.info(f"Exposed socket {socket_addr} as parameter '{param_name}'")

    def get_parameter_type(self, param_name: str) -> Any:
        """Get parameter type by looking up the target socket."""
        mapping = self._get_parameter_mapping(param_name)
        target_socket = self._get_internal_socket(mapping.target_socket_addr)
        return target_socket.type_info

    def get_parameter_default(self, param_name: str) -> Any:
        """Get parameter default from the target socket."""
        mapping = self._get_parameter_mapping(param_name)
        target_socket = self._get_internal_socket(mapping.target_socket_addr)
        return target_socket.value

    def set_parameter_value(self, param_name: str, value: Any) -> None:
        """Set a parameter value with type validation."""
        mapping = self._get_parameter_mapping(param_name)
        target_socket = self._get_internal_socket(mapping.target_socket_addr)

        # Basic type validation
        expected_type = target_socket.type_info.python_type
        if expected_type != Any and not isinstance(value, expected_type):
            logger.warning(
                f"Parameter '{param_name}' type mismatch: expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

        self.parameter_values[param_name] = value
        logger.debug(f"Set parameter '{param_name}' = {value}")

    def _get_parameter_mapping(self, param_name: str) -> ParameterMapping:
        """Get parameter mapping by name."""
        for mapping in self.parameter_mappings:
            if mapping.parameter_name == param_name:
                return mapping
        raise ValueError(f"Parameter '{param_name}' not found")

    def _propagate_inputs_to_internal_graph(self) -> None:
        """Transfer data from proxy input sockets to internal graph sockets."""
        for proxy_name, internal_addr in self.proxy_target_mappings.items():
            proxy_socket = self.sockets[proxy_name]
            internal_socket = self._get_internal_socket(internal_addr)

            internal_socket.value = proxy_socket.value
            logger.trace(f"Propagated input: {proxy_name} -> {internal_addr}")

    def _apply_parameters_to_internal_graph(self) -> None:
        """Apply parameter values to their target sockets in the internal graph."""
        for mapping in self.parameter_mappings:
            param_value = self.parameter_values.get(mapping.parameter_name)
            if param_value is not None:
                internal_socket = self._get_internal_socket(mapping.target_socket_addr)
                internal_socket.value = param_value
                logger.trace(f"Applied parameter: {mapping.parameter_name} = {param_value}")

    def _propagate_outputs_from_internal_graph(self) -> None:
        """Transfer data from internal graph sockets to proxy output sockets."""
        for proxy_name, internal_addr in self.proxy_source_mappings.items():
            internal_socket = self._get_internal_socket(internal_addr)
            proxy_socket = self.sockets[proxy_name]
            proxy_socket.value = internal_socket.value
            logger.trace(f"Propagated output: {internal_addr} -> {proxy_name}")

    def process(self) -> None:
        """Execute the sub-graph with proper data flow.

        This method orchestrates the execution of the internal graph:
        1. Transfer input data from proxy sockets to internal sockets
        2. Apply exposed parameters to their target sockets
        3. Execute the internal graph
        4. Transfer output data from internal sockets to proxy sockets
        """
        logger.debug(f"Processing SubGraphNode '{self.name}'")

        # 1. Transfer input data to internal graph
        self._propagate_inputs_to_internal_graph()

        # 2. Apply exposed parameters
        self._apply_parameters_to_internal_graph()

        # 3. Execute internal graph using the active engine
        active_engine = current_execution_engine_context.get()
        assert active_engine is not None, (
            "SubGraphNode.process() called without an active ExecutionEngine context"
        )

        # The active_engine is already managing depth, so it will increment it
        # when it calls execute_graph recursively.
        active_engine.execute_graph(self.internal_graph, context=f"sub-graph: {self.name}")

        # 4. Transfer outputs from internal graph
        self._propagate_outputs_from_internal_graph()

        logger.debug(f"Completed processing SubGraphNode '{self.name}'")
