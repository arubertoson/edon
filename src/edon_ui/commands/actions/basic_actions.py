"""Basic, non-graph-algorithm command actions."""

from loguru import logger

from PySide6.QtCore import QPointF
from PySide6.QtGui import QMouseEvent, QCursor

# XXX: Editor Context should probably be a protocol.
from edon_ui.views.viewer import EditorContext
from edon_ui.items.node import NodeItem
from edon_ui.items.edge import EdgeItem
from edon_ui.widgets.node_spawner import NodeSpawningPanel
from edon.subgraph.node import SubGraphNode


def close_action(context: EditorContext) -> bool:
    """Handles the command to close the main application window.

    Args:
        context: The current editor context, expected to have a `window` attribute
                 referencing the main application window.

    Returns:
        True if the close operation was attempted, False if the window context was missing.
    """
    if not hasattr(context, "window") or context.window is None:
        logger.warning("Close action: No window found in context.")
        return False
    logger.info("Executing close_action.")
    context.window.close()
    return True


def help_action(context: EditorContext) -> bool:
    """Placeholder action for showing a help dialog or help information.

    Currently, this action logs a message and prints to the console.
    It should be implemented to display actual help content.

    Args:
        context: The current editor context (unused in placeholder).

    Returns:
        True, indicating the action was handled (as a placeholder).
    """
    logger.info("Executing help_action (placeholder).")
    print("Help dialog would open here. (Placeholder Implementation)")
    return True


def window_toggle_maximize_action(context: EditorContext) -> bool:
    """Toggles the main application window between fullscreen/maximized and normal states.

    Args:
        context: The current editor context, expected to have a `window` attribute
                 referencing the main application window.

    Returns:
        True if the toggle operation was attempted, False if the window context was missing.
    """
    if not hasattr(context, "window") or context.window is None:
        logger.warning("Toggle maximize action: No window found in context.")
        return False

    current_state = context.window.isFullScreen()
    logger.info(f"Executing window_toggle_maximize_action. Current fullscreen: {current_state}")
    if current_state:
        context.window.showNormal()
    else:
        context.window.showFullScreen()
    return True


def delete_selection_action(context: EditorContext) -> bool:
    """Deletes currently selected nodes and edges from the graph scene.

    Retrieves selected NodeItem and EdgeItem instances from the context
    and requests their deletion via the context's manager.

    Args:
        context: The current editor context, expected to have `selected_items`
                 and a `manager` capable of handling deletion requests.

    Returns:
        True if deletion requests were successfully made or if nothing was selected.
        False if the context was invalid or an error occurred during deletion requests.
    """
    if not context or not hasattr(context, "selected_items") or not hasattr(context, "manager"):
        logger.warning(
            "Delete selection action: Invalid context (missing selected_items or manager)."
        )
        return False

    node_items = [item for item in context.selected_items if isinstance(item, NodeItem)]
    edge_items = [item for item in context.selected_items if isinstance(item, EdgeItem)]

    if not node_items and not edge_items:
        logger.info("Delete selection action: Nothing selected to delete.")
        return False

    logger.info(
        f"Executing delete_selection_action: Deleting {len(node_items)} nodes and {len(edge_items)} edges."
    )

    if node_items:
        node_ids = [node.entity_id for node in node_items]
        try:
            context.controller.handle_ui_node_deletion_request(node_ids)
            logger.debug(f"Requested deletion of nodes: {node_ids}")
        except Exception as e:
            logger.error(f"Error during node deletion request: {e}")
            return False

    if edge_items:
        try:
            edge_ids_for_log = [
                f"{edge.source_socket_item.parent_node_entity_id if edge.source_socket_item else 'N/A'}->{edge.target_socket_item.parent_node_entity_id if edge.target_socket_item else 'N/A'}"
                for edge in edge_items
            ]
            logger.debug(f"Requesting deletion of edges: {edge_ids_for_log}")
            context.controller.handle_ui_edge_deletion_request(edge_items)
        except Exception as e:
            logger.error(f"Error during edge deletion request: {e}")
            return False

    return True


def action_show_node_spawner(context: EditorContext) -> bool:
    """
    Action to show the NodeSpawningPanel.
    The panel is positioned based on mouse event or current cursor position.
    The node spawn position is derived from this.
    """
    logger.debug("Executing action: Show Node Spawner")
    graph_controller = context.controller
    view = context.view

    # Determine global position for the panel itself
    global_pos_for_panel: QPointF
    if context.event and isinstance(context.event, QMouseEvent):
        global_pos_for_panel = context.event.globalPosition()
        logger.trace(f"Node spawner panel position from MouseEvent: {global_pos_for_panel}")
    else:
        # Fallback for hotkey invocation or non-mouse event: use current mouse cursor position
        cursor_pos = QCursor.pos()
        global_pos_for_panel = QPointF(cursor_pos)
        logger.trace(f"Node spawner panel position from QCursor: {global_pos_for_panel}")

    # Determine scene position for the node to be spawned
    # QGraphicsView.mapFromGlobal() expects QPoint, mapToScene() expects QPoint or QPolygon etc.
    view_pos = view.mapFromGlobal(global_pos_for_panel.toPoint())
    scene_pos_for_node = view.mapToScene(view_pos)
    logger.trace(f"Node spawn position in scene coordinates: {scene_pos_for_node}")

    # Ensure the panel is parented to the view or main window to manage its lifecycle and positioning
    # Using view as parent makes sense for a view-specific popup.
    # The panel is WA_DeleteOnClose, so it will clean itself up.
    panel = NodeSpawningPanel(graph_controller, scene_pos_for_node, parent=view)
    panel.show_panel(global_pos_for_panel)
    return True


def action_enter_subgraph(context: EditorContext) -> bool:
    """
    Action to enter the selected SubGraphNode.
    """
    logger.debug("Executing action: Enter Subgraph")
    if not hasattr(context, "controller") or context.controller is None:
        logger.warning("Enter Subgraph action: No controller found in context.")
        return False

    controller = context.controller
    selected_items = context.selected_items

    if len(selected_items) != 1:
        logger.trace(
            f"Expected 1 selected item for subgraph entry, found {len(selected_items)}. No action."
        )
        return False

    item = selected_items[0]
    if not isinstance(item, NodeItem):
        logger.trace(f"Selected item is not a NodeItem. Type: {type(item)}. No action.")
        return False

    entity_id = item.entity_id
    entity_node = context.controller.graph.get_node(entity_id)
    assert entity_node is not None, (
        f"CRITICAL: EntityNode with ID {entity_id} not found in graph despite UI item existing."
    )

    if not isinstance(entity_node, SubGraphNode):
        logger.trace(
            f"Selected NodeItem's entity is not a SubGraphNode. "
            f"Entity ID: {entity_node.id}, Type: {type(entity_node)}. No action."
        )
        return False

    controller.enter_subgraph(item)

    return True


def action_exit_subgraph(context: EditorContext) -> bool:
    """
    Action to exit the current subgraph and return to the parent graph.
    """
    logger.debug("Executing action: Exit Subgraph")
    if not hasattr(context, "controller") or context.controller is None:
        logger.warning("Exit Subgraph action: No controller found in context.")
        return False

    controller = context.controller
    if not controller.graph_context_stack.is_at_root():
        logger.info(f"Exiting subgraph. Current depth: {controller.graph_context_stack.depth}")
        # Assuming exit_subgraph() will be implemented on WorkspaceController
        # based on memory.md.
        # This method is expected to handle popping from the graph_context_stack
        # and updating the view.
        if hasattr(controller, "exit_subgraph"):
            controller.exit_subgraph()
            return True
        else:
            logger.error("WorkspaceController does not have an exit_subgraph method.")
            return False
    else:
        logger.info("Exit Subgraph action: Already at root graph. No action taken.")
        return False
