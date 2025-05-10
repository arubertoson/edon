import sys

# Import Loguru and setup function
from loguru import logger
from PySide6.QtCore import Qt, QtMsgType
from PySide6.QtWidgets import QApplication, QMessageBox

from edon.graph import Graph as LogicalGraph
from edon.logging import setup_logging
from edon_ui.commands import CommandRegistry, DeleteSelectionCommand, KeyBinding, KeyManager, ToggleFullscreenCommand, AddNodeCommand
from edon_ui.graph_ui_manager import GraphUIManager
from edon_ui.window import MainWindow


def setup_commands(graph_manager):
    """Set up all commands for the application"""
    logger.debug("Setting up commands")
    registry = CommandRegistry()

    registry.register("delete_selection", DeleteSelectionCommand(graph_manager))
    registry.register("toggle_fullscreen", ToggleFullscreenCommand())

    add_node_command = AddNodeCommand(graph_manager)
    registry.register("add_node", add_node_command)

    logger.debug(f"Registered {len(registry.commands)} commands")
    return registry


def setup_key_bindings(key_manager):
    """Set up all key bindings using a more sophisticated system"""
    logger.debug("Setting up key bindings")

    # Define all command bindings in a nested dictionary structure
    bindings = {
        # Selection-related commands
        "delete_selection": {
            "description": "Delete selected items",
            "keys": [
                (Qt.Key_Delete, Qt.KeyboardModifier.NoModifier),
                (Qt.Key_D, Qt.KeyboardModifier.ControlModifier),  # Alternative binding
            ],
            "sequences": [],
        },
        "add_node": {
            "description": "Add a new node",
            "keys": [
                (Qt.Key_A, Qt.KeyboardModifier.ShiftModifier),
            ],
            "sequences": [],
        },
        # Window commands
        "toggle_fullscreen": {
            "description": "Toggle fullscreen mode",
            "keys": [
                (Qt.Key_F11, Qt.KeyboardModifier.NoModifier),
                (Qt.Key_Return, Qt.KeyboardModifier.AltModifier),
            ],
            "sequences": ["Ctrl+K, Ctrl+F"],
        },
        # View commands
        "zoom_in": {
            "description": "Zoom in",
            "keys": [(Qt.Key_Plus, Qt.KeyboardModifier.ControlModifier)],
            "sequences": [],
        },
        "zoom_out": {
            "description": "Zoom out",
            "keys": [(Qt.Key_Minus, Qt.KeyboardModifier.ControlModifier)],
            "sequences": [],
        },
        "reset_zoom": {
            "description": "Reset zoom level",
            "keys": [(Qt.Key_0, Qt.KeyboardModifier.ControlModifier)],
            "sequences": ["Ctrl+K, Ctrl+Z"],
        },
    }

    # Register all bindings
    for command_name, binding_info in bindings.items():
        description = binding_info["description"]

        # Register direct key bindings
        for key, modifiers in binding_info["keys"]:
            key_manager.register_key(KeyBinding(key, modifiers, command_name, description))
            logger.trace(f"Registered key binding: {key} + {modifiers} -> {command_name}")

        # Register sequence bindings
        for sequence in binding_info["sequences"]:
            key_manager.register_sequence(
                sequence, KeyBinding(0, Qt.KeyboardModifier.NoModifier, command_name, description)
            )
            logger.trace(f"Registered sequence binding: {sequence} -> {command_name}")

    logger.debug(
        f"Registered {sum(len(b['keys']) for b in bindings.values())} key bindings and {sum(len(b['sequences']) for b in bindings.values())} sequences"
    )


# Qt message handler that routes to loguru
def qt_message_handler(msg_type, context, message):
    level = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "CRITICAL",
    }.get(msg_type, "INFO")

    logger.opt(depth=1).log(level, f"Qt: {message}")


def show_error_dialog(message, details=None):
    """Show error dialog to user and log the error"""
    logger.error(f"User-facing error: {message}")
    if details:
        logger.debug(f"Error details: {details}")

    error_dialog = QMessageBox()
    error_dialog.setIcon(QMessageBox.Critical)
    error_dialog.setText(message)
    if details:
        error_dialog.setDetailedText(details)
    error_dialog.setWindowTitle("Error")
    error_dialog.setStandardButtons(QMessageBox.Ok)
    error_dialog.exec()


if __name__ == "__main__":
    setup_logging(debug_mode="--debug" in sys.argv)

    # Enable Qt message handler
    from PySide6.QtCore import qInstallMessageHandler

    qInstallMessageHandler(qt_message_handler)

    logger.info("Starting Edon application")

    try:
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
    except Exception as e:
        logger.opt(exception=True).critical(f"Unhandled exception: {str(e)}")
        show_error_dialog("An unexpected error occurred", str(e))
        sys.exit(1)
