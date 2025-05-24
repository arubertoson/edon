"""Basic, non-graph-algorithm command actions."""

from loguru import logger

# XXX: Editor Context should probably be a protocol.
from edon_ui.views.viewer import EditorContext
from edon_ui.items.node import NodeItem
from edon_ui.items.edge import EdgeItem


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
        logger.warning("Delete selection action: Invalid context (missing selected_items or manager).")
        return False

    node_items = [item for item in context.selected_items if isinstance(item, NodeItem)]
    edge_items = [item for item in context.selected_items if isinstance(item, EdgeItem)]

    if not node_items and not edge_items:
        logger.info("Delete selection action: Nothing selected to delete.")
        return False

    logger.info(f"Executing delete_selection_action: Deleting {len(node_items)} nodes and {len(edge_items)} edges.")

    if node_items:
        node_ids = [node.entity_id for node in node_items]
        try:
            context.manager.handle_ui_node_deletion_request(node_ids)
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
            context.manager.handle_ui_edge_deletion_request(edge_items)
        except Exception as e:
            logger.error(f"Error during edge deletion request: {e}")
            return False

    return True
