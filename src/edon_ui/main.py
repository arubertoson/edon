import sys
from typing import Callable

from loguru import logger
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from edon.graph import EntityGraph
from edon.node import EntityNode
from edon.logging import setup_logging
from edon_ui.commands import KeyManager, setup_commands, setup_key_bindings
from edon_ui.graph_ui_manager import GraphUIManager
from edon_ui.window import MainWindow


def _qt_message_handler(msg_type, message):
    level = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "CRITICAL",
    }.get(msg_type, "INFO")

    logger.opt(depth=1).log(level, f"Qt: {message}")


def main(entity_graph: EntityGraph | None = None, node_registry: dict[str, type[EntityNode]] | None = None, after_setup_callback: Callable | None = None) -> None:
    # Configure the global Loguru logger singleton for the whole app.
    # All `from loguru import logger` imports refer to this configured logger.
    setup_logging(debug_mode="--debug" in sys.argv)

    # Install custom Qt message handler to redirect Qt's internal logs (debug, warnings, errors)
    # to our Loguru logger, ensuring all application logs appear in the same place with consistent formatting
    qInstallMessageHandler(_qt_message_handler)

    logger.info("Starting Edon application")
    app = QApplication(sys.argv)
    logger.debug("QApplication initialized")

    window = MainWindow()
    logger.debug("MainWindow created (scene initialized within)")

    entity_graph = entity_graph if entity_graph is not None else EntityGraph()
    logger.debug(f"Using entity graph: {entity_graph}")


    # 4. Create the GraphUIManager, linking it to the logical graph and the window's scene
    graph_ui_manager = GraphUIManager(
        entity_graph=entity_graph,
        graphics_scene=window.scene, # Get the scene from the window
        node_type_registry=node_registry,
    )
    logger.debug("GraphUIManager initialized")

    # 5. CRITICAL STEP: Link the scene to the GraphUIManager
    window.scene.graph_manager = graph_ui_manager
    logger.debug("GraphicsScene linked to GraphUIManager")

    # 6. Setup commands, passing the GraphUIManager
    command_registry = setup_commands(graph_ui_manager) # Pass the manager
    logger.debug("CommandRegistry initialized")

    key_manager = KeyManager(command_registry)
    setup_key_bindings(key_manager)
    logger.debug("KeyManager initialized and bindings set up")

    # 8. Connect key manager to the view
    window.canvas.key_manager = key_manager # Assuming canvas is the GraphicsView

    # 9. Connect standard UI signals from GraphicsView to GraphUIManager SLOTS
    # These connections are for UI-initiated actions (like context menu add node)
    # that go through the view directly to the manager.
    window.canvas.new_node_requested_at_scene_pos.connect(graph_ui_manager.handle_ui_node_creation_request)
    window.canvas.node_deletion_requested.connect(graph_ui_manager.handle_ui_node_deletion_request)
    window.canvas.edge_deletion_requested.connect(graph_ui_manager.handle_ui_edge_deletion_request)
    logger.debug("Connected signals between GraphicsView and GraphUIManager")

    # Optional: Populate scene if a pre-populated graph was passed
    # This is more for demo/testing scenarios where main is called with an existing graph.
    # XXX: Later when we can load graphs from files, we can remove this.
    if entity_graph is not None and entity_graph.nodes:
        logger.info("Populating UI from pre-existing entity graph...")
        graph_ui_manager._populate_scene_from_entity_graph()


    # For demos/testing: allow external code to run after full setup
    if after_setup_callback:
        # Pass relevant components for the demo to use
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
