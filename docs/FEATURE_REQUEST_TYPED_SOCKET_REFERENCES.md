# Feature Request: Typed Socket References

## 1. Problem Description

Currently, methods like `EntityGraph.connect_sockets` and `EntityGraph.disconnect_sockets` accept `output_ref` and `input_ref` arguments as `tuple[str, str]`. This representation, while concise, has several drawbacks:

-   **Readability:** Accessing elements by index (e.g., `ref[0]`, `ref[1]`) within the methods is less clear than named attribute access.
-   **Self-documentation:** The type `tuple[str, str]` does not inherently convey the meaning of its elements (i.e., `node_id` and `socket_name`) without consulting docstrings or implementation details.
-   **Type Explicitness:** It's a generic type that doesn't specifically denote a "socket reference," making the code's intent less obvious.

## 2. Proposed Solution

Introduce a dedicated type for socket references using `typing.NamedTuple`. This new type, `SocketReference`, will be defined as follows:

```python
from typing import NamedTuple

class SocketReference(NamedTuple):
    """Represents a reference to a specific socket on a specific node."""
    node_id: str
    socket_name: str
```

The signatures of `connect_sockets` and `disconnect_sockets` in `EntityGraph` will be updated to use `SocketReference`:

```python
def connect_sockets(
    self, output_ref: SocketReference, input_ref: SocketReference
) -> tuple[bool, SocketConnectionErrorReason | GraphObjectErrorReason | None]:
    # ...

def disconnect_sockets(
    self, output_ref: SocketReference, input_ref: SocketReference
) -> tuple[bool, SocketDisconnectionErrorReason | GraphObjectErrorReason | None]:
    # ...
```

Internal access within these methods will change from indexed access to named attribute access (e.g., `output_ref.node_id`, `output_ref.socket_name`).

## 3. Benefits

-   **Enhanced Readability:** Code becomes more intuitive and easier to understand (e.g., `output_ref.node_id` vs. `output_ref[0]`).
-   **Improved Self-Documentation:** The `SocketReference` type itself makes the purpose and structure of the data clear.
-   **Better Type Safety & Explicitness:** Provides a more specific type than a generic tuple, improving static analysis and reducing potential errors.
-   **Alignment with Project Guidelines:** Promotes clearer, more narrative code structure.

## 4. Affected Components & Implementation Notes

-   **Primary Files:**
    -   `src/edon/graph.py`: Definition of `SocketReference` and modification of `connect_sockets` and `disconnect_sockets`.
-   **Potential Cascade:**
    -   Any modules that call `EntityGraph.connect_sockets` or `EntityGraph.disconnect_sockets` will need to be updated to instantiate and pass `SocketReference` objects instead of `tuple[str, str]`. This includes, but may not be limited to:
        -   `GraphController` in `edon_ui` if it directly calls these methods.
        -   Command actions that manipulate graph connections.
-   **Action Items:**
    1.  Define `SocketReference` in `src/edon/graph.py`.
    2.  Update signatures and internal logic of `connect_sockets` and `disconnect_sockets`.
    3.  Identify all call sites of these methods throughout the codebase.
    4.  Update these call sites to use the new `SocketReference` type.
    5.  Ensure comprehensive testing of connection/disconnection functionality.

## 5. Justification

This change aligns with the Edon project's emphasis on code clarity, readability ("read like a book"), and robust typing. It's a proactive step to improve maintainability and reduce ambiguity in a core part of the graph engine. 