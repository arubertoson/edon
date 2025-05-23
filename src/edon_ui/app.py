"""Provides the main EdonApplication class for managing the Edon UI.

This class encapsulates the setup of the Qt application, main window,
command system, and other core components, offering a simplified entry point
for running or extending the Edon UI.
"""

import sys

from loguru import logger
from PySide6.QtCore import QtMsgType, qInstallMessageHandler, QMessageLogContext
from PySide6.QtWidgets import QApplication

from edon.graph import EntityGraph
from edon.logging import setup_logging
from edon.node import EntityNode

from edon_ui.commands import (
    ALL_COMMAND_DEFINITIONS,
    CommandRegistry,
    KeyMapping,
    KeyProcessor,
)
from edon_ui.graph import GraphController
from edon_ui.views import GraphicsScene, GraphicsView, MainWindow
from edon_ui import theme


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

    def __init__(self, log_level: str = "DEBUG", node_registry: dict[str, type[EntityNode]] | None = None) -> None:
        # Initialize logging as the first step to capture all subsequent initialization messages.
        self._setup_logging(log_level)

        logger.info("Initializing EdonApplication...")

        # Initialize Qt application and UI components
        self._qt_app: QApplication = self._create_qt_application()
        self._qt_app.setStyleSheet(theme.APPLICATION_STYLESHEET)

        self._graphics_scene: GraphicsScene = GraphicsScene()
        self._graphics_view: GraphicsView = GraphicsView(self._graphics_scene)

        # Initialize public API components
        # These are the main interfaces that users of EdonApplication will interact with
        self.main_window: MainWindow = MainWindow(self._graphics_view)
        self.command_registry: CommandRegistry = CommandRegistry()
        self.key_mapping: KeyMapping = KeyMapping()
        self._entity_graph: EntityGraph = EntityGraph()
        self._node_registry: dict[str, type[EntityNode]] = node_registry or {}

        # Set up command system
        self._setup_command_system()

        # Set up graph system
        self._graph_controller: GraphController = self._update_graph_system()

        logger.info("EdonApplication initialized.")

    @property
    def entity_graph(self) -> EntityGraph:
        """The core data model representing nodes and links."""
        return self._entity_graph

    @entity_graph.setter
    def entity_graph(self, value: EntityGraph) -> None:
        """Sets the core data model for the graph.

        Setting this property re-initializes the graph controller to reflect
        the new graph in the UI.
        """
        self._entity_graph = value
        self._update_graph_system()

    @property
    def node_registry(self) -> dict[str, type[EntityNode]]:
        """Registry mapping node type string identifiers to `EntityNode` subclasses."""
        return self._node_registry

    def _update_graph_system(self) -> GraphController:
        """Initializes or re-initializes the graph controller.

        This method ensures the UI's graph representation is synchronized with the
        application's core data. It creates and configures a `GraphController`
        instance, connecting the current `entity_graph` and `node_registry`
        to the `GraphicsScene`. This is typically invoked during application
        setup or when the underlying graph data or node types change.
        """
        # Create graph controller and connect it to the scene, the GraphController serves as
        # the bridge between the entity graph model and the UI. It handles synchronization
        # of nodes/edges and translates UI actions to model operations.
        self._graph_controller = GraphController(
            entity_graph=self.entity_graph,
            ui_scene=self._graphics_scene,
            node_type_registry=self.node_registry,
        )

        # Connect signals from UI components to the graph controller to handle user interactions
        # This enables the UI to request node/edge creation, deletion, and other graph operations
        logger.debug(f"GraphController created with {len(self.entity_graph.nodes)} existing nodes")
        self._graphics_scene.controller = self._graph_controller

        return self._graph_controller

    @node_registry.setter
    def node_registry(self, value: dict[str, type[EntityNode]]) -> None:
        """Sets the registry for mapping node type identifiers to their classes.

        Setting this property re-initializes the graph controller to use the
        new node registry.
        """
        self._node_registry = value
        self._update_graph_system()

    def _setup_logging(self, log_level: str) -> None:
        # Set up loguru
        setup_logging(log_level=log_level)

        # Install Qt message handler
        qInstallMessageHandler(_qt_message_handler)

        logger.debug("Logging system initialized")

    def _create_qt_application(self) -> QApplication:
        """Creates or retrieves the global `QApplication` instance."""
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
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
        # Populate the graphics scene from the entity graph. This is done here to ensure
        # the graph is visually represented before the main window is shown.
        self._graph_controller.sync_scene_from_graph()

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
