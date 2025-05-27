"""Provides the main EdonApplication class for managing the Edon UI.

This class encapsulates the setup of the Qt application, main window,
command system, and other core components, offering a simplified entry point
for running or extending the Edon UI.
"""

import sys

from loguru import logger
from PySide6.QtCore import QMessageLogContext, QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from edon.graph import EntityGraph
from edon.logging import setup_logging
from edon.node import EntityNode
from edon_ui import theme
from edon_ui.commands import (
    ALL_COMMAND_DEFINITIONS,
    CommandRegistry,
    KeyMapping,
    KeyProcessor,
)
from edon_ui.graph import GraphController
from edon_ui.views import GraphicsScene, GraphicsView, MainWindow


def _qt_message_handler(msg_type: QtMsgType, context: QMessageLogContext, message: str) -> None:
    """Redirects Qt log messages to the loguru-based application logger.

    This function processes log messages originating from the Qt framework,
    mapping them to appropriate severity levels and forwarding them to the
    application's central loguru logger. It includes context like source file,
    line number, and function from the Qt message.
    """
    level = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "CRITICAL",
    }.get(msg_type, "INFO")

    def _populate_context() -> str:
        file_info = context.file() or "unknown_file"  # type: ignore
        line_info = context.line() if context.line() is not None else 0  # type: ignore
        func_info = context.function() or "unknown_function"  # type: ignore
        category_info = context.category() or "unknown_category"  # type: ignore

        return f"[{category_info}] ({file_info}:{line_info}, {func_info})"

    log_message = f"Qt: {_populate_context()} - {message}"
    logger.opt(depth=2).log(level, log_message)


class EdonApplication:
    """Main application class for the Edon Node Editor UI.

    This class encapsulates the Qt application, main window, command system,
    and graph management, providing a primary entry point for the Edon UI.
    It orchestrates the core components and manages their lifecycle.
    """

    def __init__(
        self,
        node_registry: dict[str, type[EntityNode]] | None = None,
        log_level: str = "DEBUG",
    ) -> None:
        # Initialize logging as the first step to capture all subsequent initialization messages.
        self._setup_logging(log_level)

        logger.info("Initializing EdonApplication...")

        # Initialize Qt application and UI components
        self._qt_app: QApplication = self._create_qt_application()
        self._qt_app.setStyleSheet(theme.APPLICATION_STYLESHEET)

        # Node registry is passed, but graph data is loaded explicitly later if provided.
        self._node_registry: dict[str, type[EntityNode]] = node_registry or {}
        self._graph_controller: GraphController = GraphController(node_type_registry=self._node_registry)

        # Scene is created with the controller. It will be initially empty.
        scene = GraphicsScene(None)
        scene.controller = self._graph_controller
        self._graph_controller.scene = scene
        self._graphics_view: GraphicsView = GraphicsView(scene)

        # Initialize public API components
        self.main_window: MainWindow = MainWindow(self._graphics_view)
        self.command_registry: CommandRegistry = CommandRegistry()
        self.key_mapping: KeyMapping = KeyMapping()

        self._setup_command_system()

        logger.info("EdonApplication initialized.")

    def load_graph(self, entity_graph: EntityGraph) -> None:
        """
        Loads a new graph, replacing the current one.

        This method is the primary interface for loading saved files,
        importing graphs, or replacing the current workspace content.
        """
        logger.info(f"Application loading new graph with {len(entity_graph.nodes)} nodes")
        self._graph_controller.load_graph(entity_graph)

    def clear_graph(self) -> None:
        """
        Clears the current graph and returns to empty workspace.
        """
        logger.info("Application clearing current graph")
        self._graph_controller.clear_graph()

    @property
    def entity_graph(self) -> EntityGraph:
        """Access to the current entity graph for serialization or inspection."""
        return self._graph_controller.entity_graph

    @entity_graph.setter
    def entity_graph(self, value: EntityGraph) -> None:
        """Sets a new graph via the load_graph mechanism."""
        self.load_graph(value)

    @property
    def node_registry(self) -> dict[str, type[EntityNode]]:
        return self._node_registry

    @node_registry.setter
    def node_registry(self, value: dict[str, type[EntityNode]]) -> None:
        """
        Sets the registry for mapping node type identifiers to their classes.

        Note: This only affects future node creation operations. Existing nodes
        in the graph are not affected by registry changes.
        """
        self._node_registry = value
        # Update the controller's copy of the node registry
        self._graph_controller.node_registry.clear()
        self._graph_controller.node_registry.update(value)
        logger.info(f"Node registry updated in controller with {len(value)} node types")

    def _setup_logging(self, log_level: str) -> None:
        setup_logging(log_level=log_level)

        # Install Qt message handler
        qInstallMessageHandler(_qt_message_handler)

        logger.debug("Logging system initialized")

    def _create_qt_application(self) -> QApplication:
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)

        assert isinstance(app, QApplication)
        return app

    def _setup_command_system(self) -> None:
        """Initializes the application's command system.

        This method configures the infrastructure for handling user commands.
        It populates the `CommandRegistry` with all available command definitions,
        establishes default `KeyMapping` based on these commands, and sets up
        the `KeyProcessor` to interpret input from the `GraphicsView` and
        dispatch corresponding actions.
        """
        logger.debug("Setting up command system... CommandRegistry, KeyMapping and KeyProcessor")

        # Register all built-in commands
        for cmd_def in ALL_COMMAND_DEFINITIONS:
            self.command_registry.register(cmd_def)

        # Create key mapping from command defaults
        self.key_mapping = KeyMapping.from_command_defaults(self.command_registry.get_all_commands())

        # Create key processor for handling input events
        self._key_processor: KeyProcessor = KeyProcessor(self.command_registry, self.key_mapping)
        self._graphics_view.key_processor = self._key_processor

    def run(self) -> int:
        """Shows the main window and starts the Qt application event loop.

        This method is the primary entry point to launch and operate the Edon UI.
        It first ensures the visual graph is synchronized with the underlying data,
        then displays the `main_window`, and finally initiates the Qt application's
        event processing. The application's exit code is returned upon termination.
        """
        logger.info("Running EdonApplication...")

        logger.debug("About to call self.main_window.show()")
        try:
            self.main_window.show()
            logger.debug(
                f"self.main_window.show() called. IsVisible: {self.main_window.isVisible()}, Geometry: {self.main_window.geometry()}"
            )
        except Exception as e:
            logger.exception(f"Exception during main_window.show(): {e}")
            return 1  # Indicate error

        logger.debug("About to call self._qt_app.exec()")
        exit_code = self._qt_app.exec()
        logger.debug(f"self._qt_app.exec() finished with exit_code: {exit_code}")
        return exit_code


if __name__ == "__main__":
    app = EdonApplication(log_level="DEBUG")
    sys.exit(app.run())
