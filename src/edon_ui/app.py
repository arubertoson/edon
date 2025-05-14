"""Provides the main EdonApplication class for managing the Edon UI.

This class encapsulates the setup of the Qt application, main window,
command system, and other core components, offering a simplified entry point
for running or extending the Edon UI.
"""

import sys

from loguru import logger
from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from edon.graph import EntityGraph
from edon.logging import setup_logging
from edon.node import EntityNode

from .commands import (
    ALL_COMMAND_DEFINITIONS,
    CommandRegistry,
    KeyMapping,
    KeyProcessor,
)
from .graph_controller import GraphController
from .graphics import GraphicsScene, GraphicsView, MainWindow
from . import theme


def _qt_message_handler(msg_type, message):
    """Handler for Qt messages that redirects them to loguru."""
    level = {
        QtMsgType.QtDebugMsg: "DEBUG",
        QtMsgType.QtInfoMsg: "INFO",
        QtMsgType.QtWarningMsg: "WARNING",
        QtMsgType.QtCriticalMsg: "ERROR",
        QtMsgType.QtFatalMsg: "CRITICAL",
    }.get(msg_type, "INFO")

    logger.opt(depth=1).log(level, f"Qt: {message}")


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

    def __init__(self, debug_mode: bool = False, node_registry: dict[str, type[EntityNode]] | None = None) -> None:
        """Initialize the Edon application with all required components.

        Args:
            debug_mode: Whether to enable debug logging.
            node_registry: Optional dictionary mapping node type hints to node classes.
        """
        # Set up logging first
        self._setup_logging(debug_mode)

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
        # Create graph controller and connect it to the scene, the GraphController serves as
        # the bridge between the entity graph model and the UI. It handles synchronization
        # of nodes/edges and translates UI actions to model operations.
        self._graph_controller = GraphController(
            entity_graph=self.entity_graph,
            graphics_scene=self._graphics_scene,
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

    def _setup_logging(self, debug_mode: bool) -> None:
        """Set up logging for the application.

        This configures both loguru and Qt message handling.
        """
        # Set up loguru
        setup_logging(debug_mode=debug_mode)

        # Install Qt message handler
        qInstallMessageHandler(_qt_message_handler)

        logger.debug("Logging system initialized")

    def _create_qt_application(self) -> QApplication:
        """Create or get the Qt application instance."""
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        return app

    def _setup_command_system(self) -> None:
        logger.debug("Setting up command system... CommandRegistry, KeyMapping and KeyProcessor")

        # Register all built-in commands
        for cmd_def in ALL_COMMAND_DEFINITIONS:
            self.command_registry.register(cmd_def)

        # Create key mapping from command defaults
        self.key_mapping = KeyMapping.from_command_defaults(self.command_registry.get_all_commands())

        # Create key processor for handling input events
        self._key_processor = KeyProcessor(self.command_registry, self.key_mapping)
        self._graphics_view.key_processor = self._key_processor
        logger.debug("Command system initialized with key processor")

    def run(self) -> int:
        """Show the main window and start the application event loop.

        Returns:
            The exit code from the application.
        """
        logger.info("Running EdonApplication...")
        # Initialize the scene with the current entity graph

        logger.info("Populating scene from entity graph...")
        self._graph_controller._populate_scene_from_entity_graph()

        self.main_window.show()
        return self._qt_app.exec()


if __name__ == "__main__":
    app = EdonApplication(debug_mode="--debug" in sys.argv)
    sys.exit(app.run())
