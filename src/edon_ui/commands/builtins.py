from dataclasses import dataclass
from typing import Any
from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow
from edon_ui.item.edge import EdgeItem
from edon_ui.item.node import NodeItem

@dataclass
class KeyBinding:
    key: int
    modifiers: Qt.KeyboardModifier
    command_name: str
    description: str = ""

class DeleteSelectionCommand:
    def __init__(self, graph_manager):
        self.graph_manager = graph_manager

    def execute(self, context: Any = None) -> bool:
        if not context:
            logger.warning("DeleteSelectionCommand executed with empty context")
            return False
        node_items = [item for item in context if isinstance(item, NodeItem)]
        edge_items = [item for item in context if isinstance(item, EdgeItem)]
        logger.info(f"DeleteSelectionCommand: Deleting {len(node_items)} nodes and {len(edge_items)} edges")
        if node_items:
            node_ids = [node.node_entity_id for node in node_items]
            self.graph_manager.handle_ui_node_deletion_request(node_ids)
        if edge_items:
            edge_info = []
            for edge in edge_items:
                if edge.source_socket_item and edge.target_socket_item:
                    source = edge.source_socket_item.parent_node_entity_id
                    target = edge.target_socket_item.parent_node_entity_id
                    edge_info.append(f"{source}->{target}")
                else:
                    edge_info.append("incomplete_edge")
            logger.debug(f"Deleting edges: {edge_info}")
            self.graph_manager.handle_ui_edge_deletion_request(edge_items)
        return True

class ToggleFullscreenCommand:
    def execute(self, context: QMainWindow = None) -> bool:
        if not context:
            logger.warning("ToggleFullscreenCommand executed with invalid context (not a window)")
            return False
        current_state = context.isFullScreen()
        new_state = not current_state
        logger.info(f"Toggling fullscreen: {current_state} -> {new_state}")
        if current_state:
            context.showNormal()
        else:
            context.showFullScreen()
        return True

class AddNodeCommand:
    def __init__(self, graph_manager):
        self.graph_manager = graph_manager

    def execute(self, context: Any = None) -> bool:
        if not context or 'node_type' not in context:
            logger.warning("AddNodeCommand executed with invalid context")
            return False
        node_type = context['node_type']
        position = context.get('position', None)
        try:
            self.graph_manager.handle_ui_node_creation_request(node_type, position)
            logger.info(f"AddNodeCommand: Added node of type {node_type} at {position}")
            return True
        except Exception as e:
            logger.error(f"AddNodeCommand failed: {e}")
            return False 