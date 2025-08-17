# Sub-Graph Architecture

## 1. Overview

The sub-graph feature allows an `EntityNode` (or a specialized subclass) to encapsulate an entire `EntityGraph` within itself. This "SubGraphNode" acts as a regular node in its parent graph, with its own source and target sockets. These external sockets are mapped to specific sockets of nodes *within* the internal sub-graph, effectively exposing parts of the sub-graph's functionality.

Sub-graphs enable users to:
-   **Abstract complexity**: Package complex logic into reusable components.
-   **Organize graphs**: Improve readability and maintainability of large graphs.
-   **Create custom, high-level nodes**: Build powerful nodes from simpler ones.

## 2. Core Concepts

### 2.1. `SubGraphNode`
-   A specialized type of `EntityNode`.
-   Contains an instance of `EntityGraph` (the "internal graph").
-   Its own `source_sockets` and `target_sockets` are defined by "proxy" sockets that map to sockets within its internal graph.

### 2.2. Proxy Sockets
-   Sockets defined on the `SubGraphNode` itself.
-   Each proxy socket is linked to a specific socket of a node *inside* the sub-graph.
    -   A `SubGraphNode`'s source socket (output) maps to a source socket of an internal node.
    -   A `SubGraphNode`'s target socket (input) maps to a target socket of an internal node.
-   Data flowing into a `SubGraphNode`'s target socket is routed to the corresponding internal socket.
-   Data from an internal source socket (designated as an output of the sub-graph) is routed to the corresponding `SubGraphNode`'s source socket.

### 2.3. Sub-Graph Parameters
-   `SubGraphNode` can expose configurable parameters.
-   These parameters can be linked to attributes or input sockets of nodes within the internal graph.
-   This allows users to customize the behavior of a sub-graph instance without directly editing its internal structure. Example: A "Math Operation" sub-graph might expose a parameter to choose between "Add", "Subtract", "Multiply".

## 3. Data Model Changes

### 3.1. `EntityNode`
-   No direct changes strictly required for the base `EntityNode` to support *being part of* a sub-graph.
-   A new subclass, `SubGraphNode(EntityNode)`, will be introduced.

### 3.2. `SubGraphNode(EntityNode)`
```python
from edon.node import EntityNode
from edon.graph import EntityGraph
from edon.types import SocketDef, SocketAddress

@dataclass
class SubGraphNode(EntityNode):
    internal_graph: EntityGraph = field(default_factory=EntityGraph)
    
    # Mapping from this SubGraphNode's socket names to internal SocketAddresses
    # e.g., {"subgraph_input_A": SocketAddress(node_id="internal_node_1", name="input_X", role=SocketRole.TARGET)}
    proxy_target_mappings: dict[str, SocketAddress] = field(default_factory=dict)
    # e.g., {"subgraph_output_B": SocketAddress(node_id="internal_node_2", name="output_Y", role=SocketRole.SOURCE)}
    proxy_source_mappings: dict[str, SocketAddress] = field(default_factory=dict)

    # Parameters exposed by the sub-graph
    # Key: Parameter name (e.g., "operation_type")
    # Value: Could be a direct value, or a reference to an internal node's attribute/socket
    # This needs further definition: e.g. dict[str, Any] or dict[str, InternalParameterMapping]
    exposed_parameters: dict[str, Any] = field(default_factory=dict) 

    def __post_init__(self):
        # Initialize SubGraphNode's own sockets based on proxy_target_mappings and proxy_source_mappings
        # These definitions would likely be dynamic, based on how the user "exposes" internal sockets.
        # For example, if a user exposes an internal `int` target socket, a corresponding `int` target socket
        # is created on the SubGraphNode.
        
        # Option 1: SocketDefs are pre-defined or loaded (e.g. from a file defining the sub-graph type)
        # self.source_socket_definitions = self._derive_source_socket_defs_from_mappings()
        # self.target_socket_definitions = self._derive_target_socket_defs_from_mappings()
        super().__post_init__() # Creates sockets based on the definitions

    def process(self) -> None:
        # 1. Transfer data from SubGraphNode's target (input) sockets
        #    to the corresponding mapped sockets in the internal_graph.
        for proxy_name, internal_addr in self.proxy_target_mappings.items():
            proxy_socket = self.sockets[proxy_name] # This is a target socket on SubGraphNode
            internal_node = self.internal_graph.get_node(internal_addr.node_id)
            internal_socket = internal_node.sockets[internal_addr.name]
            internal_socket.value = proxy_socket.value # Assume value has been set by parent graph execution

        # 2. Apply exposed parameters to the internal graph.
        #    This might involve setting values on internal nodes/sockets.
        #    (Details TBD based on parameter mapping strategy)

        # 3. Execute the internal_graph.
        #    This requires an ExecutionEngine instance or similar logic.
        #    Consider if ExecutionEngine needs to be passed in or accessible.
        engine = ExecutionEngine() # Or get from a shared context
        engine.execute_graph(self.internal_graph)

        # 4. Transfer data from the mapped source sockets in the internal_graph
        #    to the SubGraphNode's source (output) sockets.
        for proxy_name, internal_addr in self.proxy_source_mappings.items():
            proxy_socket = self.sockets[proxy_name] # This is a source socket on SubGraphNode
            internal_node = self.internal_graph.get_node(internal_addr.node_id)
            internal_socket = internal_node.sockets[internal_addr.name]
            proxy_socket.value = internal_socket.value
```

### 3.3. `EntityGraph`
-   No direct changes required. `EntityGraph` can already contain any `EntityNode` subclass.

### 3.4. `SocketAddress`
-   Remains unchanged. It uniquely identifies a socket within a *specific* graph. When dealing with sub-graphs, context is important (i.e., is this address for the parent graph or an internal graph?).

### 3.5. `EdgeKey`
-   Remains unchanged.

## 4. Execution Flow

1.  The `ExecutionEngine` processes the parent graph.
2.  When it encounters a `SubGraphNode`, it calls its `process()` method.
3.  The `SubGraphNode.process()` method:
    a.  **Input Propagation**: Takes values from its own target sockets (which received data from the parent graph) and sets them on the corresponding mapped target sockets of nodes *within* its `internal_graph`.
    b.  **Parameter Application**: Applies any configured `exposed_parameters` to the relevant parts of the `internal_graph`.
    c.  **Internal Execution**: Invokes an `ExecutionEngine` (or a nested execution logic) to process its `internal_graph`. This engine will topologically sort and execute the nodes within the sub-graph.
    d.  **Output Propagation**: After the `internal_graph` execution is complete, it takes values from the mapped source sockets of nodes *within* its `internal_graph` and sets them on its own source sockets, making them available to the parent graph.
4.  The `ExecutionEngine` continues processing the parent graph.

## 5. UI/UX Considerations

### 5.1. Creating Sub-Graphs
-   **From Selection**: Users select a group of nodes in the current graph and choose an option like "Convert to Sub-Graph" or "Group into Sub-Graph".
    -   The selected nodes are moved into a new `internal_graph` of a new `SubGraphNode`.
    -   Edges that crossed the boundary of the selection become candidates for proxy sockets:
        -   Incoming edges to the selection become target proxy sockets on the `SubGraphNode`.
        -   Outgoing edges from the selection become source proxy sockets on the `SubGraphNode`.
-   **From Scratch**: Users add a "New Sub-Graph" node. This node is initially empty.

### 5.2. Editing Sub-Graphs
-   **"Entering" a Sub-Graph**: Double-clicking a `SubGraphNode` or a context menu option "Edit Sub-Graph" could open a new view/tab displaying the `internal_graph`.
    -   This view is essentially another instance of the graph editor, focused on the sub-graph.
    -   The parent graph context might be shown as breadcrumbs or a "return to parent" button.
-   **Defining Proxy Sockets**:
    -   Inside the sub-graph editor view, users can designate specific sockets of internal nodes as "exposed".
    -   Right-clicking an internal node's socket could offer "Expose as Sub-Graph Input" or "Expose as Sub-Graph Output".
    -   This action would create/update the `proxy_target_mappings` or `proxy_source_mappings` on the `SubGraphNode` and dynamically add/update the corresponding socket on the `SubGraphNode` itself.
-   **Managing Parameters**: A dedicated UI panel when editing a sub-graph or inspecting a `SubGraphNode` to define and link `exposed_parameters`.

### 5.3. Visual Representation
-   A `SubGraphNode` in the parent graph should look distinct from regular nodes (e.g., different styling, an icon indicating it's a container).
-   Its sockets are the proxy sockets.

## 6. Key Challenges & Open Questions

-   **Recursive Execution & Cycles**: How to handle a `SubGraphNode` containing another `SubGraphNode`? The `ExecutionEngine`'s topological sort should handle this naturally if `SubGraphNode.process()` is a blocking call. Cycles involving sub-graphs (e.g., sub-graph output feeding into its own input via the parent graph) need careful cycle detection. The existing cycle detection in `EntityGraph.link_sockets` might need to be aware of sub-graph contexts or be applied hierarchically.
-   **Parameter Complexity**: How are parameters defined and mapped?
    -   Simple value parameters (int, string, bool).
    -   Mapping to specific internal node attributes (e.g., a `FloatNode`'s `value`).
    -   Mapping to internal socket default values.
-   **Serialization/Deserialization**: How are `SubGraphNode`s and their `internal_graph`s saved and loaded? The `internal_graph` is a nested `EntityGraph`.
-   **Performance**: Deeply nested sub-graphs could impact performance if not managed carefully. Each level of sub-graph execution adds overhead.
-   **Error Handling and Debugging**: How are errors within a sub-graph propagated to the parent graph or reported to the user? Debugging execution flow through sub-graphs needs clear visual indicators.
-   **Scope and Naming**: How to avoid naming conflicts for nodes/sockets if sub-graphs are copied or reused? Node IDs are UUIDs, which helps. Socket names within a sub-graph are local to it.
-   **Dynamic Socket Definition**: `EntityNode` currently creates sockets in `__post_init__` based on static `SocketDef` lists. `SubGraphNode` will need to dynamically update its sockets if the user exposes/unexposes internal sockets *after* the `SubGraphNode` is created. This might require a mechanism to re-initialize or modify sockets on an existing node.

## 7. Future Enhancements
-   **Sub-Graph Library**: Allow users to save and reuse `SubGraphNode` definitions.
-   **Password Protection/Locking**: Prevent accidental editing of complex sub-graphs.
-   **Versioning**: For shared sub-graph definitions.

This document provides a foundational architecture. Details for each component, especially parameter handling and UI interactions, will require further iteration.
