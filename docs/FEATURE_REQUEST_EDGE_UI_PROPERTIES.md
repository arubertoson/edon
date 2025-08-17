# Feature Request: UI-Specific Edge Properties, Rerouting, and Dynamic Styling

## 1. Summary

This feature request proposes an enhancement to allow edges in the UI representation of the graph to have specific properties that control their appearance, behavior, and provide dynamic feedback. This includes attributes like line style (solid, dashed, dotted, potentially animated), thickness (weight), color, path drawing style (Bezier, straight with corners, cubic), and potentially more advanced features like rerouting capabilities (e.g., via intermediate "reroute" or "dot" nodes).

## 2. Motivation

Currently, edges are simple visual connectors. Adding UI-specific properties and dynamic styling would:
-   Enhance visual clarity and organization within complex graphs (e.g., using different styles for different types of connections or data flows).
-   Allow users to customize the look and feel of their graphs.
-   **Provide dynamic visual feedback during graph execution (e.g., animating a dashed line to indicate an active data flow or processing state).**
-   Pave the way for more advanced edge interaction features, such as rerouting edges for better layout management without altering the logical graph structure.
-   Offer users more control over the aesthetic and readability of edges by choosing different path drawing methods (e.g., Bezier curves, straight lines with sharp/rounded corners).

## 3. Proposed Changes

### 3.1. UI Edge Properties & Styling

-   **Data Storage**: The `EdgeItem` class (or a related UI data structure) would need to store these additional properties. These properties are primarily for the UI and might not need to be reflected directly in the core `EntityGraph`'s `EdgeKey` or `EntitySocket.connections` if they don't affect the logical execution of the graph.
-   **Configurable Attributes**:
    -   `line_style`: (e.g., solid, dashed, dotted).
    -   `line_animation`: (e.g., none, "marching ants" for dashed lines, pulsing). This would be controlled dynamically during graph execution.
    -   `line_thickness` (weight): (e.g., float value).
    -   `line_color`: (e.g., QColor or hex string).
    -   `path_drawing_style`: (e.g., "bezier", "straight", "cubic_rounded_corners"). This would affect how `EdgeItem.update_path()` calculates the geometry.
    -   `corner_radius` (if applicable for certain path styles).
    -   `label`: (Optional text displayed along the edge).
-   **Dynamic Updates for Execution Feedback**:
    -   The `GraphController` (or a dedicated execution visualization component) would need a mechanism to temporarily override or update an edge's style (e.g., `line_animation`, `line_color`) during graph execution to reflect its state.
-   **User Interface**:
    -   A mechanism to edit static properties (e.g., a context menu on the edge, a property editor panel when an edge is selected).

### 3.2. Edge Rerouting (Reroute Nodes/Dots)

-   **Concept**: Introduce a special type of UI-only "node" or "dot" that an edge can be routed through. These reroute points would allow users to manually shape the path of an edge without adding a functional node to the `EntityGraph`.
-   **Implementation Sketch**:
    -   A reroute "dot" could be a small draggable `QGraphicsItem`.
    -   An `EdgeItem` could have a list of intermediate reroute points.
    -   `EdgeItem.update_path()` would need to be significantly modified to support different `path_drawing_style` options and incorporate reroute points. For example:
        -   "Bezier": Could draw Bezier segments between source, reroutes, and target.
        -   "Straight": Would draw straight line segments, potentially with an algorithm to create orthogonal-like connections with rounded/sharp corners at reroute points.
    -   Interaction:
        -   Adding a reroute: e.g., double-clicking an edge, or a context menu option.
        -   Moving a reroute: Dragging the dot.
        -   Removing a reroute: e.g., context menu on the dot, or dragging it off the edge.
-   **Impact on `EntityGraph`**: This feature is primarily UI-focused. The `EntityGraph` would still only see a direct connection between the source and target entity sockets. The reroute information would be managed by the `GraphController` and stored with the UI representation of the edge.

## 4. Scope Considerations

-   **Phase 1 (Core Static Properties & Path Styles)**: Implement basic visual properties (style, thickness, color) and a selection of path drawing styles (e.g., current Bezier, simple straight lines).
-   **Phase 2 (Dynamic Styling & Animation)**: Implement the mechanisms for dynamic updates to edge styles for execution feedback.
-   **Phase 3 (Rerouting)**: Implement the reroute node/dot functionality.
-   **Entity Graph vs. UI Graph**: It's important to maintain a clear distinction. The core `EntityGraph` should remain unaware of purely visual edge properties or rerouting logic unless a property has a direct bearing on graph execution. The `GraphController` would be responsible for managing and applying these UI-specific details.

## 5. Potential Challenges

-   **Performance**:
    -   Animating multiple edges simultaneously.
    -   Updating paths for edges with multiple reroute points and complex path styles.
-   **User Experience**:
    -   Designing an intuitive way to edit various path styles and their parameters.
    -   Intuitive interaction for adding, managing, and interacting with reroute points.
-   **Complexity of `EdgeItem.update_path()`**: This method will become significantly more complex to handle different drawing styles and reroute points.
-   **Serialization**: If these UI properties need to be saved and loaded with the graph, a strategy for serializing them alongside the core graph data will be needed, ensuring they don't pollute the logical graph structure.

## 6. Open Questions

-   Should default edge styles be configurable globally or per node/socket type?
-   How deeply should the rerouting interact with snapping or grid features?
-   What is the desired default path drawing style? 