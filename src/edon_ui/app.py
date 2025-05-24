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

    def __init__(
        self,
        entity_graph=EntityGraph | None,
        node_registry: dict[str, type[EntityNode]] | None = None,
        log_level: str = "DEBUG",
    ) -> None:
        # Initialize logging as the first step to capture all subsequent initialization messages.
        self._setup_logging(log_level)

        logger.info("Initializing EdonApplication...")

        # Initialize Qt application and UI components
        self._qt_app: QApplication = self._create_qt_application()
        self._qt_app.setStyleSheet(theme.APPLICATION_STYLESHEET)

        # Initialize core data and graph components following the new structure
        self._entity_graph: EntityGraph = entity_graph or EntityGraph()
        self._node_registry: dict[str, type[EntityNode]] = node_registry or {}

        # The initialization order for the core graph components is crucial:
        # 1. GraphController: This is the central logic unit. It needs the data model
        #    (EntityGraph) and type information (NodeRegistry) to function. It's
        #    created first as it doesn't depend on UI elements yet.
        # 2. GraphicsScene: This is the Qt-based representation of the graph. It
        #    requires an existing GraphController to manage its content and interactions.
        #    The controller is passed during construction, ensuring the scene always
        #    has a valid controller.
        # 3. GraphController.set_scene(): After both controller and scene exist,
        #    the controller is explicitly linked to the scene. This step allows the
        #    controller to populate the scene with initial data from the EntityGraph.
        #    This two-step linking (scene gets controller, then controller gets scene)
        #    avoids complex constructor dependencies and ensures both objects are
        #    fully initialized before the link is finalized.
        # 4. GraphicsView: This is the Qt widget that displays the GraphicsScene.
        #    It's created last, taking the fully initialized and populated scene.
        # This sequence ensures that dependencies are met at each step and components
        # are correctly wired together before any user interaction.

        self._graph_controller: GraphController = GraphController(
            entity_graph=self._entity_graph, node_type_registry=self._node_registry
        )

        self._graphics_scene: GraphicsScene = GraphicsScene(controller=self._graph_controller)
        self._graphics_view: GraphicsView = GraphicsView(self._graphics_scene)
        self._graph_controller.set_scene(self._graphics_scene)  # This also populates the scene

        # Initialize public API components
        self.main_window: MainWindow = MainWindow(self._graphics_view)
        self.command_registry: CommandRegistry = CommandRegistry()
        self.key_mapping: KeyMapping = KeyMapping()

        self._setup_command_system()

        logger.info("EdonApplication initialized.")

    @property
    def entity_graph(self) -> EntityGraph:
        return self._entity_graph

    @entity_graph.setter
    def entity_graph(self, value: EntityGraph) -> None:
        """Sets the core data model for the graph.

        Setting this property re-initializes the graph controller and scene
        to reflect the new graph in the UI.
        """
        self._entity_graph = value
        self._reinitialize_graph_components()

    @property
    def node_registry(self) -> dict[str, type[EntityNode]]:
        return self._node_registry

    @node_registry.setter
    def node_registry(self, value: dict[str, type[EntityNode]]) -> None:
        """Sets the registry for mapping node type identifiers to their classes.

        Setting this property re-initializes the graph controller and scene
        to use the new node registry.
        """
        self._node_registry = value
        self._reinitialize_graph_components()

    def _reinitialize_graph_components(self) -> None:
        """
        Re-initializes the GraphController and GraphicsScene when the
        EntityGraph or NodeRegistry changes.
        """
        logger.debug("Reinitializing graph components (Controller and Scene)...")

        # A new GraphController instance is created here because the controller's
        # internal state (e.g., mappings of entity IDs to UI items, edge representations)
        # is tightly coupled with the specific EntityGraph and NodeRegistry instances
        # it was initialized with. If the EntityGraph (e.g., loading a new file) or
        # NodeRegistry (e.g., plugins adding new node types) changes, the existing
        # controller's state would be invalid or inconsistent. Creating a new
        # controller ensures a clean slate, allowing it to accurately build its
        # internal representations based on the new graph data and/or node types.
        # This approach is more robust than trying to update an existing controller's
        # complex internal state in-place.
        self._graph_controller = GraphController(
            entity_graph=self._entity_graph, node_type_registry=self._node_registry
        )

        # Important: The old scene might still be referenced by the view.
        # We need to create a new one and then tell the view to use it.
        # The old scene will be garbage collected if not referenced elsewhere.
        # No need to call clear_graph_elements on the old scene as it will be replaced.
        self._graphics_scene = GraphicsScene(controller=self._graph_controller)
        self._graph_controller.set_scene(self._graphics_scene)  # This also populates the scene

        if self._graphics_view:
            self._graphics_view.setScene(self._graphics_scene)
            # Re-assign key processor if it was set on the view
            if hasattr(self, "_key_processor") and self._key_processor:
                self._graphics_view.key_processor = self._key_processor
        else:
            logger.warning("GraphicsView not available to set new scene during reinitialization.")

        logger.info("Graph components reinitialized.")

    def _setup_logging(self, log_level: str) -> None:
        setup_logging(log_level=log_level)

        # Install Qt message handler
        qInstallMessageHandler(_qt_message_handler)

        logger.debug("Logging system initialized")

    def _create_qt_application(self) -> QApplication:
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
