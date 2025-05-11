import sys

# Import Loguru and setup function
from loguru import logger
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from edon.graph import Graph as LogicalGraph
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


def main():
    logger.info("Starting Edon application")

    app = QApplication(sys.argv)
    logger.debug("QApplication initialized")

    window = MainWindow()
    logical_graph = LogicalGraph()
    logger.debug("MainWindow and LogicalGraph created")

    graph_manager = GraphUIManager(logical_graph, window.scene)
    command_registry = setup_commands(graph_manager)
    logger.debug("GraphUIManager and CommandRegistry initialized")

    key_manager = KeyManager(command_registry)
    setup_key_bindings(key_manager)
    logger.debug("KeyManager initialized and bindings set up")

    # Connect key manager to the views
    window.canvas.key_manager = key_manager

    # Connect standard signals
    window.canvas.new_node_requested_at_scene_pos.connect(graph_manager.handle_ui_request_add_node)
    window.canvas.node_deletion_requested.connect(graph_manager.handle_ui_node_deletion_request)
    window.canvas.edge_deletion_requested.connect(graph_manager.handle_ui_edge_deletion_request)
    logger.debug("Connected signals between components")

    window.show()
    logger.info("Main window displayed, starting event loop")

    sys.exit(app.exec())


if __name__ == "__main__":
    # Configure the global Loguru logger singleton for the whole app.
    # All `from loguru import logger` imports refer to this configured logger.
    setup_logging(debug_mode="--debug" in sys.argv)

    # Install custom Qt message handler to redirect Qt's internal logs (debug, warnings, errors)
    # to our Loguru logger, ensuring all application logs appear in the same place with consistent formatting
    qInstallMessageHandler(_qt_message_handler)

    try:
        main()
    except Exception as e:
        logger.opt(exception=True).critical(f"Unhandled exception: {str(e)}")
        sys.exit(1)
