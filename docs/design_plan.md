# Detailed Design and Implementation Plan for Node and Connection Drawing

**Phase 1: Core Node and Socket Rendering**

1.  **`SocketItem` Class (`src/edon_ui/socket_item.py`)**:
    *   **Purpose**: Represents a single input or output socket on a node.
    *   **Inheritance**: `QGraphicsObject` (to allow signals, e.g., for hover or connection events).
    *   **Properties**:
        *   `socket_data`: Reference to the logical socket definition from `edon.socket.Socket` (or similar).
        *   `is_input`: Boolean.
        *   `data_type`: (e.g., "int", "string", "any") - influences color/shape.
        *   `label`: Optional text label for the socket.
        *   `index`: Order of the socket on the node.
        *   `position`: Relative to its parent `NodeItem`.
    *   **Drawing (`paint` method)**:
        *   Draw a shape (e.g., circle, square) based on `data_type` or `is_input`.
        *   Fill with a color from `theme.py` based on `data_type` and connection status.
        *   Draw an outline.
        *   Optionally draw the `label` next to the socket.
    *   **Interaction**:
        *   `hoverEnterEvent`, `hoverLeaveEvent`: Change appearance (e.g., highlight).
        *   `mousePressEvent`, `mouseMoveEvent`, `mouseReleaseEvent`: Handle the start, dragging, and completion of creating a connection.
    *   **Parenting**: Will be a child item of `NodeItem`.

2.  **Enhance `NodeItem` Class (`src/edon_ui/node_item.py`)**:
    *   **Socket Management**:
        *   `self._input_sockets`: List of `SocketItem` instances.
        *   `self._output_sockets`: List of `SocketItem` instances.
        *   `add_socket(socket_data)`: Method to create a `SocketItem` from logical socket data and add it to the appropriate list and as a child QGraphicsItem.
        *   `layout_sockets()`: Method to calculate and set the positions of all `SocketItem`s. This needs to be called during initialization and potentially on resize or content changes. Sockets are typically aligned to the left (inputs) and right (outputs) edges of the node, distributed vertically.
    *   **Title Area Refinement**:
        *   The `paint()` method will still draw the title bar background.
        *   The `self.title_text_item` will continue to display the title.
        *   Consider adding a small clickable icon area (e.g., a triangle placeholder) in the title bar for future collapsibility. This icon would initially do nothing.
        *   Ensure `theme.NODE_TITLE_HEIGHT` provides enough space for text and potential icons.
    *   **Content Area and `content_rect()`**:
        *   Reaffirm that `content_rect()` defines the usable space *below* the title bar and *inside* any node padding.
        *   This is where node-specific UI elements will be placed.
    *   **Abstract Content Rendering (Initial Stub)**:
        *   Add a `draw_content(self, painter, option, widget)` method to `NodeItem`.
        *   Initially, this method can be empty or draw a placeholder text like "Node Content Area".
        *   The actual rendering of specific content (dropdowns, etc.) will be deferred to Phase 2.
    *   **Initialization**:
        *   `__init__` will take an `edon.node.Node` instance.
        *   It will set its title from the node.
        *   It will iterate through the logical node's sockets and call `add_socket()` for each.
        *   Call `layout_sockets()`.

3.  **`ConnectionItem` Class (`src/edon_ui/connection_item.py`)**:
    *   **Purpose**: Represents a visual connection (line/curve) between two `SocketItem`s.
    *   **Inheritance**: `QGraphicsPathItem` (ideal for drawing curves).
    *   **Properties**:
        *   `source_socket_item`: Reference to the starting `SocketItem`.
        *   `target_socket_item`: Reference to the ending `SocketItem` (can be `None` while dragging).
        *   `_source_pos`: `QPointF`, scene position of the source socket.
        *   `_target_pos`: `QPointF`, scene position of the target socket or current mouse cursor during drag.
    *   **Drawing (`paint` method and `setPath`)**:
        *   Draw a Bezier curve (or straight line) between `_source_pos` and `_target_pos`.
        *   Style (color, thickness) can be from `theme.py`.
    *   **Updating**:
        *   `update_positions()`: Method to be called when connected nodes or sockets move. It will get the current scene positions of its `source_socket_item` and `target_socket_item` and update its path.
        *   If connected to `SocketItem.parentItem().positionChanged` (which is `NodeItem.positionChanged`), it can auto-update.
    *   **Interaction**:
        *   Allow selection and deletion (e.g., pressing Delete key when selected).

4.  **`GraphicsScene` Enhancements (`src/edon_ui/graphics_scene.py`)**:
    *   **Connection Management**:
        *   `self.connection_items`: List to track `ConnectionItem` instances.
        *   `self.temp_connection`: Stores the `ConnectionItem` being dragged before it's finalized.
    *   **Connection Logic**:
        *   `start_connection(socket_item)`: Called by `SocketItem` on mouse press. Creates a `ConnectionItem`, sets its source, adds it to the scene, and stores it in `self.temp_connection`.
        *   `update_dragged_connection(mouse_scene_pos)`: Called by `SocketItem` or `GraphicsScene` on mouse move during connection drag. Updates the target position of `self.temp_connection`.
        *   `finish_connection(target_socket_item)`: Called by `SocketItem` on mouse release over a valid target.
            *   Validates if the connection is allowed (e.g., input to output, data type compatibility - this logic might reside in `edon.graph.Graph` or a validation helper).
            *   If valid:
                *   Finalizes the `self.temp_connection` by setting its `target_socket_item`.
                *   Adds it to `self.connection_items`.
                *   Updates the underlying logical graph in `edon.graph.Graph`.
            *   If invalid or dropped on empty space: Removes `self.temp_connection` from the scene.
        *   `cancel_connection()`: If drag ends not on a socket.
    *   **Node Deletion**: When a `NodeItem` is deleted, any connected `ConnectionItem`s must also be removed from the scene and the logical graph.

**Phase 2: Node-Specific Content Rendering**

1.  **Content Renderer Design**:
    *   Define a base class `BaseNodeContentRenderer` in a new file, e.g., `src/edon_ui/content_renderers.py`.
        *   `__init__(self, node_item, node_data)`
        *   `paint(self, painter, content_rect, option)`: Abstract method to draw content.
        *   `layout_widgets(self, content_rect)`: Method to position any child QGraphicsWidgets if used.
        *   `desired_height(self)`: Method to suggest how tall the content area needs to be. `NodeItem` can use this to adjust its own height dynamically.
    *   Create concrete renderer implementations for different node types:
        *   `DefaultContentRenderer`: Shows basic properties or a placeholder.
        *   `LabelContentRenderer`: Displays simple text labels.
        *   `DropdownContentRenderer`: Would involve creating/managing a `QGraphicsProxyWidget` embedding a `QComboBox` or a custom painted dropdown.
        *   `TextInputContentRenderer`: Similar, for `QLineEdit`.
2.  **`NodeItem` Content Integration**:
    *   `NodeItem.__init__`: Instantiate the appropriate `ContentRenderer` based on `node_data.type`.
    *   `NodeItem.paint`: Call `self.content_renderer.paint(...)` if it exists, passing the `content_rect()`.
    *   `NodeItem.boundingRect`: May need to be adjusted if content can dynamically change the node's height. The `desired_height()` from the renderer will be key.
    *   The `ContentRenderer` will be responsible for creating and managing any child `QGraphicsItem`s or `QGraphicsWidget`s that represent the node's specific UI. These items should be added as children to the `NodeItem` to be part of its coordinate system and rendering.

**Phase 3: UI Polish and Advanced Features**

1.  **Collapsible Nodes**:
    *   Add a boolean `is_collapsed` property to `NodeItem`.
    *   Modify `NodeItem.paint()`: If collapsed, only draw the title bar. Sockets and content are hidden.
    *   Modify `NodeItem.boundingRect()`: Return a smaller rect if collapsed.
    *   The clickable icon in the title bar toggles `is_collapsed` and triggers an update/layout.
    *   Connections should ideally still attach to the "logical" socket positions even if the socket visuals are hidden, or they might visually "snap" to the collapsed node's edge.
2.  **Dynamic Node Resizing**:
    *   `NodeItem`'s height could be dynamically calculated based on:
        *   Title bar height.
        *   Number of sockets and their vertical spacing.
        *   `desired_height()` of its `ContentRenderer`.
    *   Implement a `update_node_layout()` method in `NodeItem` that recalculates total height, re-layouts sockets, and informs its content renderer about the new `content_rect()`.
3.  **Context Menus**:
    *   Refine `context_menu.py` for nodes, sockets, and connections (e.g., "Delete Node", "Disconnect Socket").
4.  **Theming and Styling**:
    *   Expand `theme.py` with more options for connection appearance (e.g., different colors for different data types), socket states (hovered, connected), and content elements.

**Workflow for Implementation:**

1.  **Start with `SocketItem`**: Create the file, define the class, and implement basic drawing (shape, color).
2.  **Modify `NodeItem`**:
    *   Add socket lists and `add_socket`, `layout_sockets`.
    *   In `__init__`, create placeholder `SocketItem`s (e.g., 2 inputs, 1 output for testing) and position them.
    *   Ensure `NodeItem.paint()` is called and sockets (as child items) are also painted.
3.  **Implement `ConnectionItem`**: Basic drawing of a line/curve.
4.  **Integrate into `GraphicsScene`**:
    *   Implement `start_connection`, `update_dragged_connection`, `finish_connection`.
    *   Basic mouse interaction in `SocketItem` to trigger these scene methods.
    *   At this stage, you should be able to draw nodes, see sockets, and drag lines between them.
5.  **Refine Connection Logic**: Add validation, logical graph updates.
6.  **Implement `BaseNodeContentRenderer` and a `DefaultContentRenderer`**:
    *   Modify `NodeItem` to use a content renderer.
    *   Update `NodeItem.paint()` to call the renderer's paint method.
7.  **Iterate**: Add more content renderers, refine drawing, add features from Phase 3. 