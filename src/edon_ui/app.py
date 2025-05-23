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
    """Redirects Qt log messages to the loguru-based application logger, including context.

    Args:
        msg_type: The type of the Qt message (e.g., debug, warning, critical).
        context: The context information of the message (file, line, function, category).
        message: The actual log message content.
    """
    level = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "CRITICAL",
    }.get(msg_type, "INFO")

    def _populate_context():
        file_info = context.file() or "unknown_file"  # type: ignore
        line_info = context.line() if context.line() is not None else 0  # type: ignore
        func_info = context.function() or "unknown_function"  # type: ignore
        category_info = context.category() or "unknown_category"  # type: ignore

        return f"[{category_info}] ({file_info}:{line_info}, {func_info})"

    log_message = f"Qt: {_populate_context()} - {message}"
    logger.opt(depth=2).log(level, log_message)


class EdonApplication:
    """Main application class for the Edon Node Editor UI.

    This class provides a complete application environment for the Edon Node Editor,
    including command system, UI components, and graph management.

    Public API:
        - main_window: The main application window (QMainWindow)
        - command_registry: Registry for all commands (CommandRegistry)
        - key_mapping: Mapping between key sequences and commands (KeyMapping)
        - entity_graph: The underlying graph data model (EntityGraph)
        - node_registry: Registry mapping node type hints to node classes
        - graph_controller: Controller for graph operations (GraphController)
        - set_entity_graph(): Replace the entity graph and update dependent components
        - run(): Start the application event loop

    Example:
        app = EdonApplication()
        # Register custom commands
        app.command_registry.register(my_custom_command)
        # Set up a custom graph
        app.set_entity_graph(my_graph, my_node_registry)
        # Start the application
        app.run()
    """

    def __init__(self, log_level: str = "DEBUG", node_registry: dict[str, type[EntityNode]] | None = None) -> None:
        """Initialize the Edon application with all required components.

        Args:
            log_level: The log level to use for logging.
            node_registry: Optional dictionary mapping node type hints to node classes.
        """
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
        return self._entity_graph

    @entity_graph.setter
    def entity_graph(self, value: EntityGraph) -> None:
        self._entity_graph = value
        self._update_graph_system()

    @property
    def node_registry(self) -> dict[str, type[EntityNode]]:
        return self._node_registry

    def _update_graph_system(self) -> GraphController:
        """Initializes or re-initializes the graph controller.

        This method creates a new GraphController instance, connecting the
        application's entity graph and node registry to the graphics scene.
        It's typically called during application setup or when the entity graph
        or node registry is replaced.

        Returns:
            The newly created and configured GraphController instance.
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
        self._node_registry = value
        self._update_graph_system()

    def _setup_logging(self, log_level: str) -> None:
        """Set up logging for the application.

        This configures both loguru and Qt message handling.
        """
        # Set up loguru
        setup_logging(log_level=log_level)

        # Install Qt message handler
        qInstallMessageHandler(_qt_message_handler)

        logger.debug("Logging system initialized")

    def _create_qt_application(self) -> QApplication:
        """Creates or retrieves the global QApplication instance.

        Ensures that there is a single QApplication instance for the application.
        If one does not exist, it creates it using sys.argv.

        Returns:
            The QApplication instance.
        """
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        return app

    def _setup_command_system(self) -> None:
        """Initializes the application's command system.

        This involves:
        - Registering all built-in command definitions.
        - Creating key mappings from the default shortcuts of these commands.
        - Instantiating the KeyProcessor and linking it to the graphics view
          to handle user input and trigger commands.
        """
        logger.debug("Setting up command system... CommandRegistry, KeyMapping and KeyProcessor")

        # Register all built-in commands
        for cmd_def in ALL_COMMAND_DEFINITIONS:
            self.command_registry.register(cmd_def)

        # Create key mapping from command defaults
        self.key_mapping = KeyMapping.from_command_defaults(self.command_registry.get_all_commands())

        # Create key processor for handling input events
        self._key_processor = KeyProcessor(self.command_registry, self.key_mapping)
        self._graphics_view.key_processor = self._key_processor

    def run(self) -> int:
        """Show the main window and start the application event loop.

        Returns:
            The exit code from the application.
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
