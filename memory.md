# SubGraph Navigation and Interaction Plan

## I. Core Navigation Mechanism (Scene Switching with Context Stack)

The primary approach for navigating into and out of subgraphs will involve switching `GraphicsScene` instances displayed in the main `GraphicsView`. A dedicated state management class, `GraphContextStack`, will track the hierarchy of active graphs, their corresponding scenes, and UI data registries.

### 1. `GraphContextStack` Implementation
   - **Status**: DONE
   - **Files Affected**: `src/edon_ui/graph/context.py` (new file)
   - **Summary of Implementation**:
     - Created `NavigationState` data class to hold `graph: EntityGraph`, `scene: GraphicsScene`, `registry: GraphUIDataRegistry`, and `originating_subgraph_node: SubGraphNode | None`.
     - Created `GraphContextStack` class to manage a `list[NavigationState]`.
     - Implemented methods:
       - `initialize(root_graph, root_scene, root_registry)`: Sets up the initial state for the root graph.
       - `push_level(subgraph_internal_graph, subgraph_scene, subgraph_registry, entered_subgraph_node)`: Adds a new level to the stack when entering a subgraph.
       - `pop_level()`: Removes the top level, returning to the parent graph.
     - Implemented properties:
       - `current_level`: Returns the `NavigationState` at the top of the stack.
       - `current_graph`, `current_scene`, `current_registry`: Accessors for the components of the `current_level`.
       - `current_path_nodes`: Returns a list of `SubGraphNode`s representing the navigation path.
       - `is_at_root()`: Boolean indicating if the current level is the root.
       - `depth`: Current depth of navigation.

### 2. Integrate `GraphContextStack` into `WorkspaceController`
   - **Status**: DONE
   - **Files Affected**: `src/edon_ui/graph/controller.py`, `src/edon_ui/app.py`, `src/edon_ui/graph/context.py`
   - **Summary of Implementation**:
     - `WorkspaceController.__init__` now instantiates its own `GraphicsView` and an initial `GraphicsScene`.
     - It initializes `self.graph_context_stack` with a root `NavigationState` comprising an empty `EntityGraph`, the newly created `initial_scene`, and a fresh `GraphUIDataRegistry`.
     - `EdonApplication.__init__` instantiates `WorkspaceController` (without passing view or scene arguments) and retrieves the `GraphicsView` from `controller.view` to pass to `MainWindow`.
     - `WorkspaceController` properties (`graph`, `scene`, `data`) correctly delegate to `self.graph_context_stack.current_level` to provide context-specific instances.
     - `WorkspaceController.load_graph()`:
       - Asserts that it's called only when `graph_context_stack.is_at_root()`.
       - Re-initializes the `graph_context_stack` with the loaded graph as the new root, along with a new scene and registry.
       - Calls `_populate_scene_from_graph_data()` (which now takes no arguments) to populate the new root scene.
     - `WorkspaceController._populate_scene_from_graph_data()`:
       - Signature changed to `_populate_scene_from_graph_data(self) -> None`.
       - Operates on `self.graph` (current graph from stack) to populate `self.scene` (current scene from stack).
     - `WorkspaceController._register_node_internal()`:
       - No longer attempts to add the `EntityNode` to `self.graph`, as this is now the responsibility of the caller (e.g., `request_add_node`) or assumed if populating from an existing graph.
     - `WorkspaceController.request_add_node()`:
       - Explicitly calls `self.graph.add_node(new_entity_node)` before calling `_register_node_internal()`.
     - `WorkspaceController._clear_all_ui()`:
       - Now correctly resets the `registry` on the `current_level` of the `graph_context_stack`.
       - Delegates item removal to `self.scene.clear()`, addressing the `XXX` comment.

- **[DONE]** 3. UI Trigger for Entering Subgraph
   - **Files Affected**:
     - `src/edon_ui/commands/actions/basic_actions.py`: Added `action_enter_subgraph` and `action_exit_subgraph`.
     - `src/edon_ui/commands/builtins.py`: Defined `graph.enter_subgraph` (Ctrl+E) and `graph.exit_subgraph` (Ctrl+U) commands.
     - `src/edon_ui/graph/controller.py` (`WorkspaceController`): Implemented `enter_subgraph`, `exit_subgraph`, and `get_selected_subgraph_node_item` methods. Logic updated to use `entity_id` from `NodeItem` to fetch `EntityNode`.
     - `src/edon_ui/commands/key_processor.py`: Modified to process commands only on `KeyPress` events to prevent double execution.
     - `tests/edon_ui/graph/test_subgraph_navigation.py`: Added integration tests for enter/exit subgraph workflows and conditional logic.
   - **Summary of Implementation**:
     - Commands `graph.enter_subgraph` (hotkey `Ctrl+E`) and `graph.exit_subgraph` (hotkey `Ctrl+U`) were created, calling `action_enter_subgraph` and `action_exit_subgraph` respectively.
     - These actions use `EditorContext` to access the `WorkspaceController` and relevant UI state (like selected items for entering).
     - `WorkspaceController.get_selected_subgraph_node_item()` retrieves the selected `NodeItem` if it's a unique `SubGraphNode`. It fetches the `EntityNode` using `entity_id` from the `NodeItem` and `self.graph.get_node()`.
     - `WorkspaceController.enter_subgraph(subgraph_node_item: NodeItem)`:
       - Retrieves the `SubGraphNode` entity from `subgraph_node_item.entity_id`.
       - Asserts it's a `SubGraphNode` and retrieves its `internal_graph`.
       - Creates a new `GraphicsScene`, `GraphUIDataRegistry`, and `NavigationState`.
       - Pushes the `NavigationState` onto `self.graph_context_stack`.
       - Populates the new scene from the `internal_graph` and updates the view.
     - `WorkspaceController.exit_subgraph()`:
       - Asserts not at root, then pops from `graph_context_stack`.
       - Updates the view to the parent scene and refreshes its display.
     - The `KeyProcessor` was updated to ensure commands tied to hotkeys are only executed on `KeyPress` events, preventing double execution. An `XXX` comment was added to note future enhancements for press/release specific commands.
     - Integration tests were added to `tests/edon_ui/graph/test_subgraph_navigation.py` verifying the enter/exit workflows and conditional logic.

### 4. UI for Exiting Subgraph
   - **Status**: DONE
   - **Files to Affect**: `src/edon_ui/views/window.py` (`MainWindow` or a toolbar widget)
   - **Tasks**:
     - Add a `QPushButton` (e.g., "Back" or "Up").
     - Connect its `clicked` signal to `workspace_controller.exit_subgraph()`.
     - Connect a slot to `workspace_controller.navigation_changed` signal:
       - This slot will update the "Back" button's enabled state: `button.setEnabled(not workspace_controller.graph_context_stack.is_at_root())`.
     - (Optional) Implement breadcrumb display based on `workspace_controller.graph_context_stack.current_path_nodes`.

## II. SubGraph Interface Management (Proxy Sockets)

This phase focuses on how users define and modify the external interface (proxy sockets) of a `SubGraphNode` when they are "inside" editing its internal graph.

### 5. Dynamic Proxy Socket Management from Subgraph View (using a "Proxy Promoter Node")
   - **Status**: PLANNED
   - **Concept**: When editing *inside* a subgraph, the user interacts with a special node (e.g., `SubgraphInterfacePromoterNode`) to indicate which internal sockets should become proxy sockets on the `SubGraphNode` visible in the parent graph.
   - **Phase 1: Setup and "Expose" Workflow**
     1.  **Create `SubgraphInterfacePromoterNode` Entity:**
         - **File:** `src/edon/node.py` (or `src/edon/nodes/utility_nodes.py`)
         - **Action:** Define `SubgraphInterfacePromoterNode(EntityNode)` with two predefined input sockets (e.g., `expose_input_target`, `expose_output_target`) to act as drop targets.
         - **Note:** This node type should only be addable when editing inside a subgraph.
     2.  **Modify `SubGraphNode` Entity:**
         - **File:** `src/edon/graph.py`
         - **Action:** Add methods to `SubGraphNode`:
           - `add_proxy_socket(self, internal_socket_addr: SocketAddress, desired_proxy_socket_name: str, proxy_socket_role: SocketRole) -> SocketDef`: Creates proxy `SocketDef`, adds to self, stores mapping (e.g., `self.proxy_to_internal_map: dict[str, SocketAddress]`).
           - `remove_proxy_socket(self, proxy_socket_name: str) -> SocketDef | None`: Removes `SocketDef` and mapping.
     3.  **Controller Logic for "Expose" Request:**
         - **File:** `src/edon_ui/graph/controller.py`
         - **Action:** Implement `WorkspaceController.request_expose_subgraph_socket(self, internal_source_socket_addr: SocketAddress, target_promoter_socket_addr: SocketAddress)`.
         - **Details:**
           - Called by `GraphicsScene` on edge drop onto `SubgraphInterfacePromoterNode`'s special sockets.
           - Gets `originating_subgraph_node_entity` from `GraphContextStack`.
           - Calls `originating_subgraph_node_entity.add_proxy_socket(...)`.
           - Triggers UI update for `SubGraphNodeItem` in parent graph context using `_handle_entity_node_socket_structure_change`.
           - Creates visual edge to `SubgraphInterfacePromoterNode` in current subgraph scene.
     4.  **Implement UI Update Helpers:**
         - **File:** `src/edon_ui/graph/controller.py`: `_handle_entity_node_socket_structure_change(...)`.
         - **File:** `src/edon_ui/items/node.py`: `NodeItem.rebuild_socket_ui_from_entity(...)`.
         - **File:** `src/edon_ui/graph/registry.py`: `GraphUIDataRegistry.clear_all_socket_items_for_node(...)`, `GraphUIDataRegistry.reregister_all_socket_items_for_node(...)`.
     5.  **Scene Logic for Triggering Expose Request:**
         - **File:** `src/edon_ui/views/scene.py`
         - **Action:** Modify `GraphicsScene.finalize_dragging_edge`.
         - **Details:** If target is `SubgraphInterfacePromoterNode`'s special socket, call `controller.request_expose_subgraph_socket(...)`.

   - **Phase 2: "Unexpose" Workflow**
     1.  **Controller Logic for "Unexpose" Request (Triggered by Edge Deletion):**
         - **File:** `src/edon_ui/graph/controller.py`
         - **Action:** Modify `WorkspaceController.request_remove_edge(self, edge_key: EdgeKey)`.
         - **Details:**
           - If current graph is internal to a subgraph and edge involves `SubgraphInterfacePromoterNode`:
             - Identify `internal_socket_addr` and corresponding `proxy_socket_name` on `originating_subgraph_node_entity`.
             - **Crucial:** Remove all *external* edges connected to this `proxy_socket_name` in the parent graph using `_remove_edges_connected_to_socket` (helper needs parent context).
             - Call `originating_subgraph_node_entity.remove_proxy_socket(proxy_socket_name)`.
             - Trigger UI update for `SubGraphNodeItem` in parent graph.
     2.  **Implement `_remove_edges_connected_to_socket` Helper:**
         - **File:** `src/edon_ui/graph/controller.py`
         - **Action:** `_remove_edges_connected_to_socket(self, socket_address: SocketAddress, graph: EntityGraph, registry: GraphUIDataRegistry, scene: GraphicsScene)`.
         - **Details:** Uses `graph.get_edges_for_socket`, then `graph.unlink_sockets`, `registry.unregister_edge`, `scene.remove_edge` for each.

## III. Persistence and Usability Enhancements

### 7. Node Position Persistence Per Graph Context
   - **Status**: PENDING
   - **Files to Affect**: `src/edon/graph.py` (potentially to store layout hints), `WorkspaceController` (save/load logic), `NodeItem` (position reporting).
   - **Tasks**:
     - Determine how and where node positions are stored. Ideally, each `EntityGraph` (whether root or an `internal_graph` of a `SubGraphNode`) should maintain its own node layout.
     - When `_populate_scene_and_registry` is called, `NodeItem` positions should be set based on this stored layout for the specific graph being displayed.
     - When nodes are moved in the UI, the new positions should be saved back to the layout information of the *currently active graph* in the `GraphContextStack`.

### 8. Saving/Loading SubGraphs
   - **Status**: PENDING
   - **Details**: This is a larger topic. Subgraphs might be saved as part of the main graph file or as separate, referenced files. The current plan focuses on in-memory representation and navigation. Serialization will be addressed later.

---

**Task List & Status:**

- **[DONE]** 1. `GraphContextStack` Implementation
  - *Summary*: Created `NavigationState` and `GraphContextStack` in `src/edon_ui/graph/context.py` with methods for stack manipulation and properties for accessing current context.
- **[DONE]** 2. Integrate `GraphContextStack` into `WorkspaceController`
- **[DONE]** 3. UI Trigger for Entering Subgraph (`NodeItem.mouseDoubleClickEvent`)
- **[DONE]** 4. UI for Exiting Subgraph ("Back" button and `navigation_changed` signal handling)
- **[PLANNED]** 5. Dynamic Proxy Socket Management from Subgraph View (using a "Proxy Promoter Node")
- **[PENDING]** 6. Node Position Persistence Per Graph Context
- **[PENDING]** 7. Saving/Loading SubGraphs (Future)
