# Architectural Decision: UI and Core Logic Decoupling

## Principle: UI Operates on Primitive Data Types

To ensure a clear separation of concerns and maintain loose coupling between the core `edon` library and the `edon_ui` presentation layer, the following principle has been adopted:

**All UI components within `edon_ui` (e.g., `NodeItem`, `SocketItem`, custom widgets) will be designed to operate exclusively on primitive data types (booleans, strings, numbers) or simple, UI-specific data structures composed of these primitives.**

## Data Flow and the Adapter/Bridge Pattern

1.  **Core Logic (`edon` library):**
    *   The `edon` library contains the core domain logic, including rich objects, enums (e.g., for socket types, directions, data types), and complex data structures representing the graph, nodes, and sockets.

2.  **Adapter/Bridge Layer (within `edon_ui` or a dedicated composer):**
    *   A designated part of the codebase, typically residing within the `edon_ui` layer (e.g., within `NodeItem` when it initializes its children, or a dedicated "composer" or "controller" class), acts as an **adapter** or **bridge**.
    *   This layer is responsible for:
        *   Interacting with the rich objects and enums from the `edon` core library.
        *   **Translating** these core concepts into the simple, primitive data types that the UI components expect.
        *   For example, an `edon.socket.SocketDirectionEnum.INPUT` from the core would be translated to `is_input=True` (a boolean) before being passed to `edon_ui.socket_item.SocketItem`. Similarly, a core data type enum would be translated into a string key (e.g., `"integer_type"`) for the UI to use for styling.

3.  **UI Layer (`edon_ui`):**
    *   UI components like `SocketItem` receive these primitive values (e.g., `is_input: bool`, `visual_type_key: str`).
    *   They use these simple values for their rendering, layout, and internal logic.
    *   UI components have **no direct knowledge** of or dependency on the `edon` library's internal enums or complex object structures.
    *   If the UI needs to communicate back to the core (e.g., a user action like creating a connection), it will typically do so by emitting signals with identifiers or primitive data, which the adapter/bridge layer then translates back into actions or updates on the core `edon` objects.

## Benefits

*   **Decoupling:** The UI is not tightly bound to the internal implementation details of the core logic. Changes in the core library (e.g., refactoring enums, altering object structures) are less likely to break the UI, as long as the adapter layer can be updated to maintain the translation contract.
*   **Testability:** UI components can be tested more easily in isolation by providing them with simple primitive data, without needing to mock complex core library objects.
*   **Maintainability:** Clearer separation makes both the UI and core logic easier to understand and maintain independently.
*   **Flexibility:** This approach would allow, in theory, for different UI implementations to be built on top of the same `edon` core library by simply creating new adapter layers.
*   **Serialization:** Working with primitive data at the UI boundary simplifies the process of serializing UI state or converting it to/from formats like JSON, as these formats naturally handle primitives.

## Example Scenario: SocketItem

*   `edon.socket.Socket` (Core): Has `direction: SocketDirectionEnum`, `data_type: CoreDataTypeEnum`.
*   Adapter (e.g., in `NodeItem`):
    *   Reads `logical_socket.direction`. If `INPUT`, sets `ui_is_input = True`.
    *   Reads `logical_socket.data_type`. If `INTEGER`, sets `ui_visual_key = "integer"`.
*   `edon_ui.socket_item.SocketItem`: Receives `__init__(..., is_input=True, visual_type_key="integer", ...)` and uses these directly.

This decision ensures that the `edon_ui` layer remains focused on presentation, driven by simple data, while the `edon` library handles the underlying complex logic. 