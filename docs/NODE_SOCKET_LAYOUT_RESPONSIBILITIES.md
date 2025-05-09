# Architectural Decision: NodeItem and SocketItem Layout Responsibilities

## Principle: Delegated Layout and Sizing

To achieve a flexible and extensible node-based UI where sockets can have varying complexities and sizes (e.g., simple circles, labels, embedded widgets), the responsibilities for layout and sizing are distributed between `NodeItem` and `SocketItem` (and its potential subclasses) as follows:

### `SocketItem` Responsibilities:

1.  **Self-Sizing:**
    *   Each `SocketItem` (or its subclass) is responsible for determining its own required dimensions.
    *   It must provide methods like:
        *   `get_required_height() -> float`: Returns the total vertical space this socket and its internal content (e.g., circle, label, widget) need.
        *   `get_required_width() -> float`: Returns the total horizontal space this socket and its internal content occupy. This is particularly relevant for `NodeItem` when positioning output sockets or if sockets had significant width.
2.  **Internal Rendering:**
    *   A `SocketItem` is responsible for drawing all its visual elements (e.g., connection point circle, text labels, embedded widgets) within its own bounding rectangle, relative to its own `(0,0)` origin.
    *   The `NodeItem` will position the `SocketItem`'s `(0,0)` (top-left corner). The `SocketItem` then handles all drawing relative to this origin.
    *   For example, it will center its connection circle vertically within its `get_required_height()` and position it at the appropriate horizontal edge (left for inputs, right for outputs) of its `get_required_width()`.
3.  **Bounding Rectangle:**
    *   Its `boundingRect()` method must return the rectangle covering its entire allocated space, as defined by `get_required_width()` and `get_required_height()`, with `(0,0)` as its top-left.

### `NodeItem` Responsibilities:

1.  **Socket Instantiation:**
    *   (Future) When a logical `edon.node.Node` is visualized, `NodeItem` will be responsible for creating the appropriate `SocketItem` (or specialized subclass) instances for each logical socket defined in the backend node.
2.  **Socket Positioning (Orchestration):**
    *   `NodeItem`'s `layout_sockets()` method orchestrates the placement of its `SocketItem` children.
    *   It iterates through its input sockets:
        *   Queries each `SocketItem` for its `get_required_height()`.
        *   Positions the `SocketItem` by setting its top-left origin `(0,0)` at `(0, current_y_position)` (for input sockets, placing them at the left edge of the `NodeItem`).
        *   Updates `current_y_position` by adding the `get_required_height()` of the socket just placed.
    *   It performs a similar iteration for output sockets:
        *   Queries for `get_required_height()` and `get_required_width()`.
        *   Positions the `SocketItem`'s top-left origin `(0,0)` at `(self._width - socket_item.get_required_width(), current_y_position)` (for output sockets, aligning their right edge with the `NodeItem`'s right edge).
        *   Updates `current_y_position` for outputs.
3.  **Dynamic Node Sizing:**
    *   `NodeItem` calculates its own total height based on:
        *   The height of its title bar.
        *   The cumulative height of its input socket column (sum of `get_required_height()` for all inputs).
        *   The cumulative height of its output socket column (sum of `get_required_height()` for all outputs).
        *   The height of its main content area (to be determined by a "content renderer" in the future).
        *   Appropriate padding values (e.g., `theme.SOCKET_PADDING`).
    *   The node's overall height will be the maximum required to accommodate these sections.
4.  **Content Area Management:**
    *   `NodeItem` will provide a `content_rect()` which defines the area available for node-specific content (labels, widgets not directly part of a socket's internal drawing). The positioning of sockets helps define the vertical extent of this content area.

## General Plan Going Forward:

*   **Specialized `SocketItem` Subclasses:** For sockets that need to display more than just a circle (e.g., sockets with inline labels, input fields, or dropdowns), new subclasses of `SocketItem` will be created. These subclasses will:
    *   Implement `get_required_height()` and `get_required_width()` to reflect their more complex content.
    *   Override `paint()` (and potentially add child `QGraphicsWidget`s) to render their specific UI.
*   **Node Content Renderers:** The main area of the node (between input and output socket columns, below the title) will be drawn by a dedicated "content renderer" associated with the `NodeItem`, based on the node type. This renderer will be responsible for drawing labels and widgets that correspond to the sockets (e.g., the "Mesh 1" label next to a mesh input socket).

This separation ensures that `NodeItem` acts as a container and layout orchestrator, while each `SocketItem` is an autonomous component responsible for its own appearance and spatial requirements. This promotes modularity and makes it easier to extend the system with new, visually rich socket types. 