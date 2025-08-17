# Feature Request: Rename EntitySocket.connections to EntitySocket.edges

## 1. Problem Description

The `EntitySocket` class currently has an attribute named `connections`, which is a `list["EntitySocket"]`. This list stores references to other sockets that this socket is directly connected to. While "connections" is descriptive, in graph theory, the links between nodes (or in this case, sockets forming part of a node-to-node link) are commonly referred to as "edges."

Using the term "connections" might be slightly less precise or intuitive for developers thinking in terms of standard graph data structures and algorithms.

## 2. Proposed Solution

Rename the `connections` attribute of the `EntitySocket` dataclass to `edges`.

```python
# In src/edon/socket.py
@dataclass
class EntitySocket:
    # ... other attributes ...
    edges: list["EntitySocket"] = field(default_factory=list) # Renamed from 'connections'
    # ...
```

This change would require updating all internal references to this attribute within the `EntitySocket` class methods (e.g., `is_connected`, `add_connection`, `remove_connection`, `__repr__`) and any external code that directly accesses this attribute.

## 3. Benefits

-   **Improved Terminological Alignment:** Using "edges" aligns more closely with standard graph theory terminology, potentially making the code more intuitive for developers familiar with these concepts.
-   **Enhanced Clarity:** For discussions related to graph structure, traversal algorithms, or data model representation, "edges" can be a clearer term than "connections."
-   **Consistency:** If other parts of the codebase or documentation refer to graph edges, this change would improve consistency.

## 4. Affected Components & Implementation Notes

-   **Primary File:**
    -   `src/edon/socket.py`:
        -   Rename the `connections` attribute to `edges` in the `EntitySocket` dataclass definition.
        -   Update all methods within `EntitySocket` that reference this attribute (e.g., `is_connected`, `add_connection`, `remove_connection`, `__repr__`).
-   **Potential Cascade:**
    -   `src/edon/graph.py`:
        -   The `_has_path` method iterates through `output_socket.connections`. This would need to be updated to `output_socket.edges`.
        -   The `remove_node` method iterates through `sock_to_clear.connections`. This would need to be updated to `sock_to_clear.edges`.
    -   `src/edon/executor.py`:
        -   The `_topological_sort` method iterates through `output_socket.connections`. This would need to be updated to `output_socket.edges`.
    -   Any other part of the codebase (including potential UI components or controllers if they introspect `EntitySocket` deeply) that directly accesses `some_socket.connections` will need to be updated.
-   **Action Items:**
    1.  Rename the attribute in `EntitySocket`.
    2.  Update all internal uses within `EntitySocket`.
    3.  Identify and update all external call sites/access points in `EntityGraph`, `ExecutionEngine`, and elsewhere.
    4.  Ensure comprehensive testing of connection, disconnection, graph traversal, and execution logic.

## 5. Justification

Adopting more standard and precise terminology for core data structures like graph components can improve the overall clarity, maintainability, and understandability of the codebase, especially as the project grows or involves more developers. 