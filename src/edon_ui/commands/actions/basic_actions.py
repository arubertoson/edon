"""Basic, non-graph-algorithm command actions."""

from loguru import logger

from edon_ui.graphics.view import EditorContext  # Assuming EditorContext is here
from edon_ui.items.node import NodeItem  # For delete_selection_action
from edon_ui.items.edge import EdgeItem  # For delete_selection_action

# Note: Actual EditorContext might be defined in graphics_view.py or core.py
# Ensure imports are correct based on your project structure.


def close_action(context: EditorContext) -> bool:
    """Closes the main application window."""
    if not hasattr(context, "window") or context.window is None:
        logger.warning("Close action: No window found in context.")
        return False
    logger.info("Executing close_action.")
    context.window.close()
    return True


def help_action(context: EditorContext) -> bool:
    """Shows a help dialog (placeholder)."""
    logger.info("Executing help_action (placeholder).")
    print("Help dialog would open here.")
    return True


def window_toggle_maximize_action(context: EditorContext) -> bool:
    """Toggles the main window's fullscreen/maximized state."""
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
    """Deletes selected nodes and edges from the graph."""
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
        node_ids = [node.node_entity_id for node in node_items]
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
