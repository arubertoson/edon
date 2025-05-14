## Requirements Document: Node Editor Edge Styles

**Version:** 1.0
**Date:** October 26, 2023

**1. Introduction**

This document outlines the requirements for implementing multiple visual styles for edges (connections) within the node editor. The goal is to provide users with visual flexibility and to cater to different aesthetic preferences or information density needs.

**2. General Edge Requirements**

*   **Connection Points:** All edge styles must clearly originate from a source socket and terminate at a target socket (or mouse cursor for temporary edges).
*   **Selection Indication:** All edge styles must visually change when selected (e.g., color, thickness).
*   **Performance:** Edge rendering should be performant, even with a moderate number of edges visible in the scene. Path calculation should be efficient.
*   **Clarity:** Edges should be clearly distinguishable from the background and other scene elements.
*   **Configurability:** The active edge style should be configurable, ideally through a global setting or theme.
*   **Temporary Edge Handling:** All styles must correctly render for temporary edges during drag operations.
*   **Z-Value Management:** All styles should respect Z-value for correct draw order (e.g., active/dragged edge on top).

**3. Specific Edge Styles**

**3.1. Straight Edge**

*   **Description:** A direct straight line connecting the center of the source socket to the center of the target socket.
*   **Visuals:**
    *   Single line segment.
    *   Thickness and color defined by the theme.
*   **Implementation:**
    *   `QPainterPath.moveTo(p1)`
    *   `QPainterPath.lineTo(p2)`
*   **Pros:**
    *   Simplest to implement and render (highest performance).
    *   Very clear for direct connections.
*   **Cons:**
    *   Can lead to visual clutter if many edges cross nodes.
    *   May not be aesthetically pleasing for all graph layouts.
*   **Parameters (Themeable):**
    *   `EDGE_STRAIGHT_THICKNESS`
    *   `EDGE_STRAIGHT_COLOR_DEFAULT`
    *   `EDGE_STRAIGHT_COLOR_SELECTED`

**3.2. Cubic (Orthogonal with Rounded Corners)**

*   **Description:** An edge composed of primarily horizontal and vertical segments, with rounded corners at the bends. This style often aims to create an "orthogonal" or "circuit board" look. Typically involves one or two bends.
*   **Visuals:**
    *   Series of horizontal and vertical line segments.
    *   Bends are rounded using arcs or quadratic/cubic Bezier segments for smoothing.
    *   The path typically goes horizontally from the source socket, then vertically, then horizontally to the target socket.
*   **Implementation (`QPainterPath`):**
    *   `path.moveTo(p1)`
    *   `path.lineTo(corner1_start)`
    *   `path.arcTo(rect_for_corner1, start_angle, sweep_angle)` or `path.quadTo(ctrl_pt_corner1, corner1_end)`
    *   `path.lineTo(corner2_start)`
    *   `path.arcTo(rect_for_corner2, start_angle, sweep_angle)` or `path.quadTo(ctrl_pt_corner2, corner2_end)`
    *   `path.lineTo(p2)`
    *   **Control Point Calculation:**
        *   Determine intermediate points. For a common L-shape or C-shape:
            *   `mid_x = (p1.x() + p2.x()) / 2`
            *   `mid_y = (p1.y() + p2.y()) / 2`
        *   Example path for right-to-left connection (output on right, input on left):
            1.  `p1` to `(mid_x, p1.y)` (horizontal segment)
            2.  Rounded corner at `(mid_x, p1.y)`
            3.  `(mid_x, p1.y)` to `(mid_x, p2.y)` (vertical segment)
            4.  Rounded corner at `(mid_x, p2.y)`
            5.  `(mid_x, p2.y)` to `p2` (horizontal segment)
        *   The number of segments (1 or 2 bends) might depend on the relative positions of `p1` and `p2`. If `p1.y == p2.y`, a U-shape might be needed if they are too close horizontally.
*   **Pros:**
    *   Can create a very organized, clean look, especially for structured graphs.
    *   Reduces ambiguity of edge paths compared to overlapping straight lines.
*   **Cons:**
    *   More complex path calculation than straight lines.
    *   Determining the optimal bend points and corner radii can be tricky to make universally appealing.
    *   May require more segments than Bezier curves, potentially impacting performance slightly if not optimized.
*   **Parameters (Themeable):**
    *   `EDGE_CUBIC_THICKNESS`
    *   `EDGE_CUBIC_COLOR_DEFAULT`
    *   `EDGE_CUBIC_COLOR_SELECTED`
    *   `EDGE_CUBIC_CORNER_RADIUS`
    *   `EDGE_CUBIC_HORIZONTAL_FIRST` (boolean, to decide if the first segment from an output socket is horizontal or vertical - may depend on socket orientation).

**3.3. Curved (Bezier - Current Implementation)**

*   **Description:** A smooth, aesthetically pleasing curve connecting the source and target sockets. Typically implemented using a single cubic Bezier segment.
*   **Visuals:**
    *   Smooth curve.
    *   Control points are typically calculated to extend horizontally from the sockets, creating an S-shape for standard left-to-right connections.
*   **Implementation (`QPainterPath`):**
    *   `path.moveTo(p1)`
    *   `path.cubicTo(ctrl1, ctrl2, p2)`
    *   **Control Point Calculation (as currently implemented):**
        *   `dx = p2.x() - p1.x()`
        *   `offset_magnitude = abs(dx) * factor` (clamped by min/max offset)
        *   `ctrl1 = QPointF(p1.x() + offset_magnitude, p1.y())`
        *   `ctrl2 = QPointF(p2.x() - offset_magnitude, p2.y())`
*   **Pros:**
    *   Generally considered visually appealing and modern.
    *   Relatively simple to implement with `cubicTo`.
    *   Good balance between clarity and aesthetics.
*   **Cons:**
    *   The current simple horizontal control point calculation might not be ideal for all socket orientations (e.g., top-to-bottom connections, or connections where `dx` is small or negative, leading to less intuitive curves). Needs refinement for universal appeal.
    *   Can still overlap if many edges are present, though generally less jarring than straight lines.
*   **Parameters (Themeable):**
    *   `EDGE_BEZIER_THICKNESS`
    *   `EDGE_BEZIER_COLOR_DEFAULT`
    *   `EDGE_BEZIER_COLOR_SELECTED`
    *   `EDGE_BEZIER_HORIZONTAL_FACTOR` (current `horizontal_offset_factor`)
    *   `EDGE_BEZIER_MIN_HORIZONTAL_OFFSET`
    *   `EDGE_BEZIER_MAX_HORIZONTAL_OFFSET`
    *   (Future) `EDGE_BEZIER_ADAPT_TO_SOCKET_ORIENTATION` (boolean, for more advanced control point logic)

**4. Implementation Strategy**

1.  **Theme Configuration:**
    *   Add a global setting in `theme.py` (e.g., `ACTIVE_EDGE_STYLE = "bezier"`) to determine which style is currently active.
    *   Store parameters for each style in `theme.py`.

2.  **`EdgeItem.update_path()` Modification:**
    *   Read the `ACTIVE_EDGE_STYLE` from the theme.
    *   Use an `if/elif/else` structure within `update_path()` to call the appropriate path generation logic based on the active style.

    ```python
    # In EdgeItem.update_path()
    active_style = getattr(theme, "ACTIVE_EDGE_STYLE", "bezier") # Default to bezier

    path = QPainterPath()
    path.moveTo(p1)

    if active_style == "straight":
        # ... straight line logic ...
        path.lineTo(p2)
    elif active_style == "cubic_orthogonal": # Name for the one with corners
        # ... orthogonal with rounded corners logic ...
    elif active_style == "bezier":
        # ... existing Bezier curve logic ...
    else: # Default or fallback
        # ... e.g., bezier or straight ...

    self.setPath(path)
    ```

3.  **Refine Control Point Logic:**
    *   For "bezier" and "cubic_orthogonal", refine the calculation of control points and corner points to handle different socket orientations and relative positions more gracefully. This might involve checking if `self._source_socket_item.is_input` or having socket items store their orientation (e.g., "left", "right", "top", "bottom").

**5. Future Considerations**

*   **Dynamic Style Switching:** Allow users to change the edge style at runtime.
*   **Per-Edge Style:** Potentially allow overriding the global edge style for specific edges or types of connections (more complex).
*   **Advanced Pathfinding:** For very dense graphs, consider algorithms that route edges to avoid overlapping nodes (significantly more complex).
*   **Edge Arrows/Decorations:** Add optional arrowheads or other decorations to indicate data flow direction, compatible with all styles.

--- 