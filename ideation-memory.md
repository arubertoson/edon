# Edon UI Feature Ideation

This file tracks major UI building blocks and features to be implemented in Edon.

## Feature Roadmap (In Order of Implementation)

2.  **Node Inspector / Property Editor:**
    *   **Goal:** Allow users to view and edit parameters/settings of selected nodes that are not directly represented by input/output sockets.
    *   **Examples:** Value of an unlinked `IntegerNode`, configuration of custom nodes, `SubGraphNode` parameters.
    *   **Considerations:** Dedicated UI panel, context-sensitive display based on selected node(s).

3.  **Graph Persistence UI (Save/Load from File):**
    *   **Goal:** Implement full UI workflows for saving the current graph to a file and loading a graph from a file.
    *   **Considerations:** File dialogs, choice of persistence format (e.g., JSON, XML), error handling, user feedback.
    *   **Existing Context:** `EdonApplication.load_graph`, `AppContextMenu._add_file_actions`.

4.  **Undo/Redo System Integration:**
    *   **Goal:** Provide users with the ability to undo and redo graph operations.
    *   **Considerations:** Undo/redo stack, integrating graph operations (node creation/deletion, linking, property changes) as commands, UI elements (menu items, hotkeys).
    *   **Existing Context:** Command system in `src/edon_ui/commands/`.

5.  **Sub-graph Editing Workflow:**
    *   **Goal:** Enable users to seamlessly interact with `SubGraphNode` instances, including viewing and editing their internal structure.
    *   **Considerations:** Mechanisms to "enter" a sub-graph, manage its proxy sockets from the parent graph, navigate between parent and sub-graphs.
    *   **Existing Context:** `SubGraphNode` class.
