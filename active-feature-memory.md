# Sub-Graph UI Implementation Plan

 This document outlines the plan for implementing the User Interface (UI) and User Experience (UX) aspects of the sub-graph feature. It
 consolidates information from `docs/sub-graph-memory.md` and `docs/sub-graph-architecture.md`.

 ## I. Visual Representation of SubGraphNode

 ### 1.1. Distinct Styling
 -   **Goal**: `SubGraphNode` instances should be visually distinguishable from regular `EntityNode` instances in the parent graph.
 -   **Status**: Implemented. `SubGraphNodeItem` uses a distinct background color (`theme.SUBGRAPH_NODE_BACKGROUND`).
 -   **Considerations**:
     -   Unique shape, color, border, or background.
     -   An icon or overlay indicating it's a container or encapsulates an internal graph.
     -   Visual cues for nesting depth if sub-graphs can be nested (e.g., slight inset, shadow).
 -   **Reference**: `docs/sub-graph-memory.md` (4.1), `docs/sub-graph-architecture.md` (5.3)

 ### 1.2. Proxy Socket Display
 -   **Goal**: Proxy sockets on the `SubGraphNode` (representing exposed internal sockets) should be clearly displayed and interactable.
 -   **Status**: Implemented. Proxy sockets are created as `SocketItem` instances by `create_node_item` factory and displayed on `SubGraphNodeItem`.
 -   **Considerations**:
     -   Appearance consistent with regular `SocketItem`s for linking.
     -   Tooltips or labels to optionally indicate they are proxy sockets and potentially show the name of the internal socket they map to.
 -   **Reference**: `docs/sub-graph-architecture.md` (5.3)

 ### 1.3. Parameter Panels
 -   **Goal**: Provide a UI for viewing and configuring the exposed parameters of a selected `SubGraphNode`.
 -   **Considerations**:
     -   Integration into the existing node properties panel or a dedicated section for sub-graph parameters.
     -   Appropriate UI widgets for different parameter types (e.g., text input, dropdown, checkbox).
 -   **Reference**: `docs/sub-graph-memory.md` (4.1)

 ### 1.4. Nesting Indicators (Optional/Advanced)
 -   **Goal**: If sub-graphs can be nested, provide visual cues for the graph hierarchy.
 -   **Considerations**:
     -   Could be part of the breadcrumb system (see Section III.2).
     -   Minimap visualization (see Section IV.1).
 -   **Reference**: `docs/sub-graph-memory.md` (4.1, 4.3)

 ## II. Sub-Graph Creation Workflow

 ### 2.1. Creation from Selection
 -   **Goal**: Allow users to select a group of existing nodes and convert them into a new `SubGraphNode`.
 -   **UI Action**: A context menu option (e.g., "Group into Sub-Graph", "Convert to Sub-Graph") when multiple nodes are selected.
 -   **Process**:
     1.  The selected nodes are moved into the `internal_graph` of a newly created `SubGraphNode`.
     2.  The system analyzes edges that previously connected selected nodes to unselected nodes (boundary edges).
     3.  Incoming boundary edges to the selection become new target proxy sockets on the `SubGraphNode`.
     4.  Outgoing boundary edges from the selection become new source proxy sockets on the `SubGraphNode`.
     5.  Automatic creation of these proxy sockets and their mappings.
 -   **Reference**: `docs/sub-graph-memory.md` (2.2), `docs/sub-graph-architecture.md` (5.1)

 ### 2.2. Creation from Scratch
 -   **Goal**: Allow users to add a new, empty `SubGraphNode` to the graph.
 -   **UI Action**: An option in the "Add Node" menu/palette (e.g., "New Sub-Graph Node").
 -   **Initial State**: The `SubGraphNode` is created with an empty `internal_graph` and no proxy sockets. Users would then enter the sub-gra
 to build its contents and expose sockets.
 -   **Reference**: `docs/sub-graph-memory.md` (2.2), `docs/sub-graph-architecture.md` (5.1)

 ## III. Sub-Graph Editing Interface and Management

 ### 3.1. Entering/Viewing Sub-Graph Content
 -   **Goal**: Enable users to seamlessly transition into viewing and editing the `internal_graph` of a `SubGraphNode`.
 -   **UI Action**:
     -   Double-click on the `SubGraphNode` in the parent graph.
     -   A context menu option on the `SubGraphNode` (e.g., "Edit Sub-Graph", "Open Sub-Graph").
 -   **Mechanism**:
     -   The graph editor view switches to display the `internal_graph` of the `SubGraphNode`. The parent graph is hidden.
     -   The `GraphController` and `GraphicsScene` will need to manage this context switch.
 -   **Reference**: `docs/sub-graph-memory.md` (4.2), `docs/sub-graph-architecture.md` (5.2), `active-feature-memory.md` (5)

 ### 3.2. Graph Context Navigation
 -   **Goal**: Provide clear orientation and navigation when working with nested sub-graphs.
 -   **Components**:
     -   **Breadcrumb System**: Display the current path in the graph hierarchy (e.g., `Root Graph > OuterSubGraph > InnerSubGraph`). Each pa
 of the breadcrumb should be clickable to navigate to that level.
     -   **"Return to Parent" Button/Action**: A clear and accessible way to navigate up one level in the hierarchy.
 -   **State Management**: Relies on a `GraphContext` system to track the currently active graph being edited.
 -   **Reference**: `docs/sub-graph-memory.md` (2.1, 4.2)

 ### 3.3. Proxy Socket Management UI

 #### 3.3.1. Within Sub-Graph Editor (Defining Exposure)
 -   **Goal**: Allow users, while editing an `internal_graph`, to designate specific sockets of internal nodes to be exposed as proxy sockets
 on the parent `SubGraphNode`.
 -   **UI Action**:
     -   Right-click on a socket of a node within the `internal_graph`.
     -   Context menu options like "Expose as Sub-Graph Input" (for target sockets) or "Expose as Sub-Graph Output" (for source sockets).
     -   An option to "Unexpose" an already exposed socket.
 -   **Feedback**:
     -   Visual indication on internal sockets that are currently exposed (e.g., a special icon or styling).
     -   The `SubGraphNode` in the parent graph should dynamically update its list of sockets to reflect these changes.
 -   **Reference**: `docs/sub-graph-memory.md` (2.3, 4.2), `docs/sub-graph-architecture.md` (5.2)

 #### 3.3.2. From Parent Graph (Managing Existing Proxies)
 -   **Goal**: Allow users to manage some aspects of a `SubGraphNode`'s existing proxy sockets without needing to enter the sub-graph editor.
 -   **UI Action** (on the `SubGraphNode` item in the parent graph):
     -   A section in the node's properties panel listing its proxy sockets.
     -   Possible actions via context menu on the `SubGraphNode` itself or its listed proxy sockets:
         -   Rename the external-facing name of a proxy socket (if this is allowed to differ from the internal socket's name).
         -   Reorder proxy sockets (for visual organization on the `SubGraphNode`).
         -   A shortcut to "Navigate to Internal Socket" which would enter the sub-graph and highlight the mapped internal socket.
 -   **Considerations**: This focuses on the external presentation and management of proxy sockets, not their internal mapping.
 -   **Reference**: `active-feature-memory.md` (5)

 ## IV. Advanced UI Features (Future Considerations / Post-MVP)

 ### 4.1. Minimap for Sub-Graph Contents
 -   **Goal**: Offer an overview of the sub-graph's internal structure, potentially as a small preview on the `SubGraphNode` item itself or i
 a detail panel when the `SubGraphNode` is selected.
 -   **Reference**: `docs/sub-graph-memory.md` (4.3)

 ### 4.2. Visual Parameter-to-Socket Binding UI
 -   **Goal**: For complex parameter mappings (e.g., linking a sub-graph parameter to an internal node's attribute or socket default), provid
 a more visual interface than simple text input, perhaps a mini-editor.
 -   **Reference**: `docs/sub-graph-memory.md` (4.3)

 ### 4.3. Real-time Validation Feedback
 -   **Goal**: Provide immediate visual feedback for errors or warnings related to sub-graph configuration.
 -   **Examples**:
     -   A proxy socket mapping is broken (e.g., internal node/socket deleted).
     -   A parameter's value is incompatible with its target.
     -   Cyclical dependencies introduced through sub-graph linking.
 -   **Reference**: `docs/sub-graph-memory.md` (4.3)

 ## V. Integration with Existing UI Systems

 This section outlines how sub-graph UI features will interact with key existing UI components.

 ### 5.1. `GraphController`
 -   **Responsibilities**:
     -   Handle UI requests for creating `SubGraphNode`s (from selection, from scratch).
     -   Manage the context switch when entering or exiting a sub-graph view (loading the appropriate `EntityGraph` model, updating UI).
     -   Mediate UI actions for exposing/unexposing sockets and updating `SubGraphNode` definitions.
     -   Relay changes in proxy sockets or parameters to the `SubGraphNode` model.

 ### 5.2. `GraphicsScene` / `GraphicsView`
 -   **Responsibilities**:
     -   Render `SubGraphNodeItem`s with their distinct styling and proxy sockets.
     -   Handle UI events on `SubGraphNodeItem`s (e.g., double-click to enter, context menus).
     -   Display navigation elements like breadcrumbs.
     -   Potentially manage different layers or views if sub-graph editing happens in an overlay or separate viewport (though current plan
 favors replacing scene content).

 ### 5.3. `NodeItem` and `SocketItem`
 -   **`SubGraphNodeItem`**: A new class, likely subclassing `NodeItem`, to represent `SubGraphNode`s. It will need custom painting for
 distinct styling and potentially to display summary info or a minimap.
 -   **Proxy `SocketItem`s**: The proxy sockets on a `SubGraphNodeItem` should be standard `SocketItem` instances, behaving like any other
 socket for edge creation and interaction. Their underlying `SocketDef` will be derived from the internal mapped sockets.

 ### 5.4. `GraphUIDataRegistry`
 -   **Responsibilities**:
     -   Correctly register and track `SubGraphNodeItem`s and their associated UI components (proxy sockets).
     -   Handle the change in context: when navigating into a sub-graph, the registry might need to be cleared of parent graph UI items and
 populated with sub-graph UI items, or manage multiple contexts if a hierarchical approach is taken. This needs careful design to ensure
 consistency.

 ### 5.5. `SocketLinkItem` and Dragging Operations
 -   **Considerations**:
     -   Dragging an edge to/from a proxy socket on a `SubGraphNodeItem` should work identically to regular sockets.
     -   The `GraphController::prepare_drag_operation` and `partition_socket_drop_targets` methods will need to correctly handle proxy socket
