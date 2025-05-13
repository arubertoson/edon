import sys
from typing import Callable

from loguru import logger
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication
# For QInputEvent in ContextProvider if we define it here temporarily
# from PySide6.QtGui import QInputEvent # No longer needed here

from edon.graph import EntityGraph
from edon.node import EntityNode
from edon.logging import setup_logging

# Import new command system components
from edon_ui.commands import (
    CommandRegistry,
    KeyMapping,
    KeyProcessor,
    ALL_COMMAND_DEFINITIONS,
    # ContextProvider, # Protocol is implemented by GraphicsView
    # EditorContext as CommandsEditorContextTypeAlias # Type alias from core, not directly used here now
)
# ActualEditorContext is defined and used within graphics_view.py now
# from edon_ui.graphics_view import EditorContext as ActualEditorContext

from edon_ui.graph_ui_manager import GraphUIManager
from edon_ui.graphics.window import MainWindow


def _qt_message_handler(msg_type, message):
    level = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "CRITICAL",
    }.get(msg_type, "INFO")

    logger.opt(depth=1).log(level, f"Qt: {message}")


# Removed Temporary MainContextProvider as GraphicsView now implements ContextProvider


def main(
    entity_graph: EntityGraph | None = None,
    node_registry: dict[str, type[EntityNode]] | None = None,
    after_setup_callback: Callable | None = None,
) -> None:
    setup_logging(debug_mode="--debug" in sys.argv)
    qInstallMessageHandler(_qt_message_handler)

    logger.info("Starting Edon application")
    app = QApplication(sys.argv)

    window = MainWindow()
    logger.debug("MainWindow created (scene initialized within)")

    entity_graph = entity_graph if entity_graph is not None else EntityGraph()
    logger.debug(f"Using entity graph: {entity_graph}")

    graph_ui_manager = GraphUIManager(
        entity_graph=entity_graph,
        graphics_scene=window.scene,
        node_type_registry=node_registry,
    )
    logger.debug("GraphUIManager initialized")

    window.scene.controller = graph_ui_manager
    # logger.debug("GraphicsScene linked to GraphUIManager") # Removed for brevity

    # --- New Command System Setup ---
    logger.info("Setting up new command system...")
    command_registry = CommandRegistry()

    for cmd_def in ALL_COMMAND_DEFINITIONS:
        command_registry.register(cmd_def)
    # logger.debug(f"Registered {len(ALL_COMMAND_DEFINITIONS)} commands.") # Removed for brevity

    hotkey_mapping = KeyMapping.from_command_defaults(command_registry.get_all_commands())
    logger.debug("HotkeyMapping initialized and defaults loaded.")

    key_processor = KeyProcessor(command_registry, hotkey_mapping)
    logger.debug("KeyProcessor initialized.")

    # Assign KeyProcessor to GraphicsView. GraphicsView will use self as ContextProvider.
    window.view.key_processor = key_processor
    # Removed: window.canvas.context_provider = context_provider
    logger.info(
        "KeyProcessor assigned to GraphicsView (window.canvas). GraphicsView will use itself as ContextProvider."
    )
    # --- End New Command System Setup ---

    if entity_graph is not None and entity_graph.nodes:
        logger.info("Populating UI from pre-existing entity graph...")
        graph_ui_manager._populate_scene_from_entity_graph()

    if after_setup_callback:
        after_setup_callback(window, command_registry, graph_ui_manager)

    window.show()
    logger.info("Main window displayed, starting event loop")
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.opt(exception=True).critical(f"Unhandled exception: {str(e)}")
        sys.exit(1)
