# Detailed Design and Implementation Plan for Node and Connection Drawing

**Phase 1: Core Node and Socket Rendering**

1.  **`SocketCircleItem` and `SocketRowItem` Classes (in `src/edon_ui/socket.py`)**:
    *   **`SocketCircleItem` (formerly `SocketItem`)**:
        *   **Purpose**: Represents *only* the interactive circular connection point. (Done)
        *   **Inheritance**: `QGraphicsObject`. (Done)
        *   **Properties**: `is_input`, `identifier`, `visual_type_key`. (Done)
        *   **Drawing (`paint` method)**: Draws a themed circle. (Done)
        *   **Interaction**: `hoverEnter/Leave`, mouse events for connections. (Partially done - hover acceptance set; events to be fully implemented for connections).
        *   **Parenting**: Child of `SocketRowItem`. (Done)
    *   **`SocketRowItem` (New Class)**:
        *   **Purpose**: Represents a full row for a socket, containing the `SocketCircleItem` and a placeholder for content (currently a `QGraphicsRectItem`, intended to be a label and/or widget). (Done)
        *   **Inheritance**: `QGraphicsObject`. (Done)
        *   **Properties**: `is_input`, `socket_identifier`, `socket_visual_type`, placeholder content attributes. (Done)
        *   **Self-Sizing**: `get_required_height()`, `get_required_width()` based on its internal components (circle, placeholder content/label, padding). (Done)
        *   **Internal Layout (`_layout_socket_row` or `_do_layout`)**: Positions its `SocketCircleItem` and placeholder content/label. (Done)
        *   **Parenting**: Child of `NodeItem`. (Done)

2.  **Enhance `NodeItem` Class (`src/edon_ui/node_item.py`)**:
    *   **Socket Row Management**:
        *   `self._input_sockets`, `self._output_sockets` lists now store `SocketRowItem` instances. (Done)
        *   `add_socket_row(logical_socket_data)`: (Conceptual - placeholder `SocketRowItem`s are created directly for now. This method will be for logical node integration).
        *   `layout_socket_rows()` (formerly `layout_sockets`): Calculates and sets positions of `SocketRowItem`s. (Done)
    *   **Title Area Refinement**:
        *   `paint()` draws title bar background. (Done, improved)
        *   `title_text_item` displays title, centered. (Done)
        *   Collapsibility icon placeholder. (Not started)
    *   **Dynamic Sizing**:
        *   `_height` is dynamically calculated based on title, `SocketRowItem` heights, and padding. (Done)
        *   `_width` is dynamically calculated based on the maximum `SocketRowItem` width, node padding, and minimums. (Done)
        *   `prepareGeometryChange()` is used correctly before setting final dimensions. (Done)
    *   **`boundingRect()`**: Returns dynamic `QRectF(0, 0, self._width, self._height)`. (Done)
    *   **Content Area and `content_rect()`**:
        *   Defines usable space. (Basic version exists; needs refinement when central content renderers are added if socket rows don't span full width).
    *   **Abstract Content Rendering (Initial Stub)**: (Not started)
    *   **Initialization**:
        *   `__init__` takes title, x, y, min_width, min_height. (Done)
        *   (Future) Will take an `edon.node.Node` instance (from the core library).
        *   (Future) Will iterate through the logical node's sockets to create `SocketRowItem`s, translating data.
        *   Calls `layout_socket_rows()` and `_update_title_text_position()`. (Done)

3.  **`ConnectionItem` Class (`src/edon_ui/connection_item.py`)**: (Not started)
    *   **Purpose**: Represents a visual connection (line/curve) between two `SocketCircleItem`s.
    *   **Inheritance**: `QGraphicsPathItem`.
    *   **Properties**: `source_socket_circle_item`, `target_socket_circle_item`, positions.
    *   **Drawing**: Bezier curve or straight line.
    *   **Updating**: `update_positions()` method.
    *   **Interaction**: Selection, deletion.

4.  **`GraphicsScene` Enhancements (`src/edon_ui/graphics_scene.py`)**: (Not started for connections)
    *   **Connection Management**: `connection_items` list, `temp_connection`.
    *   **Connection Logic**: `start_connection(socket_circle_item)`, `update_dragged_connection`, `finish_connection(target_socket_circle_item)`, `cancel_connection`.
    *   **Node Deletion**: Handle removal of connected `ConnectionItem`s.
    *   Signal for view updates (`scene_changed`) for general scene state. (Done)

**Phase 2: Node-Specific Content Rendering** (Not started)
    *   ... (details remain largely the same, focusing on the area *not* occupied by `SocketRowItem`s if they are compact, or integrating with `SocketRowItem`s if they contain more complex widgets) ...

**Phase 3: UI Polish and Advanced Features** (Not started)
    *   ... (details remain largely the same) ...

**Updated Workflow for Implementation (Reflecting Current State & Next Steps):**

1.  **Define Core Socket UI Elements (in `src/edon_ui/socket.py`)**:
    *   `SocketCircleItem`: Visual representation of the connection point. (Done)
    *   `SocketRowItem`: Container for a `SocketCircleItem` and its associated content (currently a placeholder rect, to be a label/widget area), manages its own internal layout and required dimensions. (Done)
2.  **Modify `NodeItem` (`src/edon_ui/node_item.py`)**:
    *   Manage lists of `SocketRowItem`s. (Done)
    *   Implement `layout_socket_rows()` to position `SocketRowItem`s. (Done)
    *   Implement dynamic calculation of `_width` and `_height` based on `SocketRowItem` dimensions, title, padding, and minimums. Use `prepareGeometryChange()`. (Done)
    *   Create placeholder `SocketRowItem`s in `__init__` for testing. (Done)
    *   Ensure `NodeItem.paint()` correctly draws the node frame (border, title bar background). (Done, improved)
3.  **Refine Visuals & Basic Interaction (Current Focus/Next Minor Steps):**
    *   Ensure `SocketRowItem` internal layout (circle and placeholder/label) is visually correct and robust for both inputs and outputs, aligning with the target UI style (e.g., "Mesh Boolean" node). (Ongoing refinement based on visual feedback)
    *   Re-integrate `QGraphicsTextItem` for labels within `SocketRowItem` (replacing or complementing the placeholder rect), ensuring `get_required_width()` correctly uses the label's `boundingRect()`.
    *   (Optional) Add simple hover effects to `SocketCircleItem` (e.g., slight color change).
4.  **Implement `ConnectionItem` (`src/edon_ui/connection_item.py`)**: Basic drawing of a line/curve between `SocketCircleItem`s.
5.  **Integrate Connection Logic into `GraphicsScene` (`src/edon_ui/graphics_scene.py`)**:
    *   Implement `start_connection`, `update_dragged_connection`, `finish_connection`.
    *   Add mouse press/move/release event handling to `SocketCircleItem` to initiate and manage connection dragging via scene methods.
    *   At this stage, you should be able to draw nodes with socket rows, and drag connection lines between `SocketCircleItem`s.
6.  **Dynamic `NodeItem` based on Logical `edon.node.Node`**:
    *   Modify `NodeItem.__init__` to accept an `edon.node.Node` instance (from the core library).
    *   Iterate through the logical node's sockets (from `edon.node.Node.input_sockets` / `output_sockets`).
    *   For each logical socket, create a `SocketRowItem`, translating logical data (name, type, default value, etc.) to UI parameters (`label_text`, `socket_visual_type`, initial widget state). This is the adapter/bridge step.
7.  **Refine Connection Logic**: Add validation (e.g., input to output, data type compatibility based on logical socket data), and update the underlying logical graph (`edon.graph.Graph`).
8.  **Implement Node Content Renderers / Rich `SocketRowItem`s**:
    *   For simple nodes, `SocketRowItem`s might be sufficient.
    *   For nodes with central content (like dropdowns in "Mesh Boolean" not tied to one socket row), implement a `NodeContentRenderer` system.
    *   For sockets with inline editable values (e.g., an int input field directly in the row), create specialized `SocketRowItem` subclasses that embed `QGraphicsProxyWidget`s for `QLineEdit`, `QSpinBox`, `QComboBox`, etc. These subclasses will override `get_required_width/height` and `_do_layout`.
9.  **Iterate**: Add features from Phase 3 (collapsible nodes, context menus, etc.).