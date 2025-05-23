# Extending Edon: A Developer's Guide

## 1. Introduction

This guide provides detailed instructions for developers looking to extend the Edon application by adding new node types and custom commands. Edon is designed for modularity, allowing users and developers to tailor it to their specific needs.

Familiarity with the overall [Edon Project Architectural Guidelines](./ARCHITECTURAL_GUIDELINES.md) is recommended before proceeding.

## 2. Adding New Node Types

Creating custom nodes is a core extensibility feature of Edon. This involves defining the node's core logic (data, properties, computation) and its visual representation in the UI.

### 2.1. Core Node Logic (`src/edon/`)

1.  **Subclass `EntityNode`**:
    -   Define your node's data structure and inherent, UI-agnostic logic by subclassing `edon.node.EntityNode` (or a more specialized base node class if available).
    -   Example: `class MyCustomNode(EntityNode): ...`
2.  **Define Properties**:
    -   Implement any custom properties your node type requires. These properties will be part of the node's state and potentially configurable by the user.
3.  **Define Sockets**:
    -   Specify the `Socket`s for your node. Sockets are the points where links (edges) can be formed.
    -   Distinguish between **source sockets** (data flows out) and **target sockets** (data flows in).
    -   Define data types for sockets to ensure link compatibility.
    -   Example:
        ```python
        from edon.node import EntityNode, Socket # Assuming these base classes
        from edon.socket import SocketType # Hypothetical enum for socket direction

        class MyCustomNode(EntityNode):
            def __init__(self, name: str, **kwargs):
                super().__init__(name, **kwargs)
                self.add_socket("input_data", socket_type=SocketType.TARGET, data_type=int)
                self.add_socket("output_result", socket_type=SocketType.SOURCE, data_type=str)
        ```
4.  **Implement Computation (if any)**:
    -   If your node performs a specific computation or transformation as part of the graph's execution, implement this logic within the node itself or in methods it provides for an `Executor`. This logic must remain UI-agnostic.

### 2.2. UI Representation (`src/edon_ui/items/`)

1.  **Subclass `QGraphicsItem`**:
    -   Create a visual representation for your node by subclassing an appropriate Qt `QGraphicsItem` (often a custom base class like `BaseNodeGraphicsItem` if one exists in your project, or `QGraphicsObject` directly).
    -   Example: `class MyCustomNodeGraphicsItem(QGraphicsObject): ...`
2.  **Visual Design**:
    -   Implement the `paint()` method to define how your node looks (shape, color, text).
    -   Implement `boundingRect()` to define its boundaries.
3.  **Socket Visuals**:
    -   Visually represent the sockets defined in your core `EntityNode`. Ensure their positions correspond to where links will be drawn.
4.  **Interaction**:
    -   Handle mouse events for interaction (e.g., selection, dragging sockets to create links).

### 2.3. Registration and Instantiation

The Edon system needs to map a node type identifier (e.g., a unique string like `"my_custom_node"`) to its core `EntityNode` subclass and its UI `QGraphicsItem` subclass.

1.  **Registry**:
    -   This mapping is typically handled by a central registry, often managed within `EdonApplication` or the `GraphController`.
    -   The registry might store tuples like: `("my_custom_node", MyCustomNode, MyCustomNodeGraphicsItem)`.
2.  **`GraphController` Role**:
    -   **Model to View**: When a `MyCustomNode` instance is programmatically added to the `EntityGraph` (the model), the `GraphController` observes this. It uses the registry to find `MyCustomNodeGraphicsItem`, instantiates it, and adds it to the `GraphicsScene` (the view).
    -   **View to Model**: When a user requests to create "My Custom Node" via the UI (e.g., from a menu), a command is typically triggered. This command instructs the `GraphController`. The `GraphController` uses the registry to find `MyCustomNode`, instantiates it, and adds it to the `EntityGraph`.

### 2.4. Example Workflow (Conceptual)

1.  Developer defines `MyCustomNode(EntityNode)` in `src/edon/nodes/my_custom_node.py`.
2.  Developer defines `MyCustomNodeGraphicsItem(QGraphicsObject)` in `src/edon_ui/items/my_custom_node_item.py`.
3.  Developer registers `("my_custom_node", MyCustomNode, MyCustomNodeGraphicsItem)` with the application's node registry during startup.
4.  User selects "Add My Custom Node" from a UI menu.
5.  The corresponding command executes, calling a method on `GraphController` like `create_node_by_type("my_custom_node")`.
6.  `GraphController` instantiates `MyCustomNode` and adds it to `EntityGraph`.
7.  `GraphController` (observing `EntityGraph`) then instantiates `MyCustomNodeGraphicsItem` (passing the `MyCustomNode` instance to it for reference) and adds it to the `GraphicsScene`.

## 3. Adding New Commands

Commands allow users to trigger actions within Edon, often via menus, toolbars, or keyboard shortcuts.

### 3.1. Define Command Logic

1.  **Location**: Implement the command's action, usually as a function or a method of a dedicated class. These are typically located in `src/edon_ui/commands/actions/` or a similar structured path.
2.  **Functionality**: The command logic will interact with various parts of the application, most commonly:
    -   `GraphController`: To modify the graph structure (e.g., add/delete nodes, create links) or trigger view updates.
    -   `EdonApplication`: To access global application state or services (e.g., file dialogs, settings).
    -   Other UI components or managers.

### 3.2. Create `CommandDefinition`

1.  **Purpose**: A `CommandDefinition` is a data structure that describes a command to the system.
2.  **Attributes**: It typically includes:
    -   `id`: A unique string identifier for the command (e.g., `"nodes.create_my_custom_node"`).
    -   `name`: A user-friendly name displayed in menus (e.g., "Create My Custom Node").
    -   `tooltip`: A short description for tooltips.
    -   `default_shortcut`: An optional default keyboard shortcut (e.g., `"Ctrl+Shift+M"`).
    -   `callable_action`: The actual Python function or method that executes the command's logic.

### 3.3. Register the Command

1.  **Automatic Registration**:
    -   Often, projects have a central list or discovery mechanism for commands. For example, an `ALL_COMMAND_DEFINITIONS` list in `src/edon_ui/commands/__init__.py`.
    -   Adding your new `CommandDefinition` instance to this list will allow the `CommandRegistry` to find and register it automatically during application startup.
2.  **Manual Registration**:
    -   Alternatively, commands can be registered manually by calling a method on the `CommandRegistry` instance (e.g., `command_registry.register_command(my_command_definition)`).

### 3.4. UI Integration

-   Once registered, commands can be made accessible through:
    -   **Menus**: Add actions to `QMenu` that trigger the command ID.
    -   **Toolbars**: Add `QAction`s to toolbars.
    -   **Keyboard Shortcuts**: The `KeyProcessor` will listen for key sequences and, using the `KeyMapping` (which is aware of registered commands and their shortcuts), execute the appropriate command.

---
This guide should provide a solid foundation for extending Edon. Always refer to the existing codebase for specific patterns and helper classes that might facilitate these processes. 