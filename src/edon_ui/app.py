"""Provides the main EdonApplication class for managing the Edon UI.

This class encapsulates the setup of the Qt application, main window,
command system, and other core components, offering a simplified entry point
for running or extending the Edon UI.
"""

import sys

from loguru import logger
from PySide6.QtCore import QEvent, QMessageLogContext, QObject, QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from edon.graph import EntityGraph
from edon.logging import setup_logging
from edon.node import EntityNode
from edon_ui import theme
from edon_ui.commands import (
    CommandRegistry,
    KeyMapping,
    KeyProcessor,
    default_command_registry,
)
from edon_ui.graph import WorkspaceController
from edon_ui.views import MainWindow


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


class EdonLoggingApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        logger.info("EdonLoggingApplication initialized with custom notify() method.")

    def notify(self, receiver: QObject, event: QEvent) -> bool:
        """
        Overrides QCoreApplication.notify to catch and log exceptions
        that occur during event handling before they are potentially
        suppressed by Qt's C++ layer from reaching sys.excepthook.
        """
        receiver_class_name = "UnknownReceiver"
        event_type_name = "UnknownEvent"
        try:
            receiver_class_name = receiver.__class__.__name__
            # QEvent.Type is an enum, .name gives its string representation (e.g., "MouseButtonRelease")
            event_type_name = QEvent.Type(event.type()).name
        except Exception:
            # In case receiver or event is in an odd state
            pass

        try:
            # Call the original notify() method, which dispatches the event
            # to the receiver's specific event handler (e.g., mouseReleaseEvent).
            # Any exception escaping that handler will be caught by our except block.
            return super().notify(receiver, event)
        except Exception as e:
            log_context = (
                f"Receiver: {receiver_class_name}, "
                f"Event Type: {event_type_name} (ID: {event.type()})"
            )
            logger.error(
                f"<<<<<<<<<< Exception during Qt event dispatch ({log_context}) START >>>>>>>>>>"
            )
            # Use logger.opt(exception=...) for full traceback
            logger.opt(exception=(type(e), e, e.__traceback__)).critical(
                f"Unhandled Python exception caught in EdonLoggingApplication.notify(): {log_context}"
            )
            logger.error(
                f"<<<<<<<<<< Exception during Qt event dispatch ({log_context}) END >>>>>>>>>>"
            )
            logger.error(f"QNAME:: ---- > {receiver.objectName()}, {receiver.__class__.__name__}")
            check = "parent" if not hasattr(receiver, "parentItem") else "parentItem"
            value = getattr(receiver, check)()
            logger.error(f"QNAME:: ---- > {value}, {value.__class__.__name__}")

            # CRITICAL DECISION: What to do after logging?
            # Option 1 (Recommended): Re-raise the exception.
            # This allows Qt to perform its default C++ handling for the Python exception
            # (which might include printing a message to stderr).
            # It's the most "transparent" action after logging.
            # If there's any Python code higher up *calling* the event loop dispatch
            # that has a try-except, it could also catch it.
            raise

            # Option 2: Manually call your global excepthook and then suppress/exit.
            # This is a more forceful intervention if you want your hook to dictate behavior.
            # global an_exception_handler # your sys.excepthook function
            # an_exception_handler(type(e), e, e.__traceback__)
            # return False # Or True, depending on what notify should return on error.
            # If an_exception_handler exits, this won't matter.

            # If you don't re-raise and don't exit, the exception is "eaten" here,
            # which might lead to unexpected application behavior.


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

        # We're setting up the controller with it's view and node registry
        self._node_registry: dict[str, type[EntityNode]] = node_registry or {}
        self._controller = WorkspaceController(
            node_type_registry=self._node_registry,
        )

        # Initialize public API components
        self.main_window = MainWindow(self._controller.view)
        self.command_registry: CommandRegistry = default_command_registry
        self.key_mapping = KeyMapping()

        self._setup_command_system()

        logger.info("EdonApplication initialized.")

    def load_graph(self, entity_graph: EntityGraph) -> None:
        """
        Loads a new graph, replacing the current one.

        This method is the primary interface for loading saved files,
        importing graphs, or replacing the current workspace content.
        """
        logger.info(f"Application loading new graph with {len(entity_graph.nodes)} nodes")
        self._controller.load_graph(entity_graph)

    def clear_graph(self) -> None:
        """
        Clears the current graph and returns to empty workspace.
        """
        logger.info("Application clearing current graph")
        self.load_graph(EntityGraph())

    @property
    def entity_graph(self) -> EntityGraph:
        """Access to the current entity graph for serialization or inspection."""
        return self._controller.graph

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
        self._controller.node_registry.clear()
        self._controller.node_registry.update(value)
        logger.info(f"Node registry updated in controller with {len(value)} node types")

    def _setup_logging(self, log_level: str) -> None:
        setup_logging(log_level=log_level)

        # Install Qt message handler
        qInstallMessageHandler(_qt_message_handler)

        logger.debug("Logging system initialized")

    def _create_qt_application(self) -> QApplication:
        return EdonLoggingApplication(sys.argv)

    def _setup_command_system(self) -> None:
        """Initializes the application's command system.

        This method configures the infrastructure for handling user commands.
        It populates the `CommandRegistry` with all available command definitions,
        establishes default `KeyMapping` based on these commands, and sets up
        the `KeyProcessor` to interpret input from the `GraphicsView` and
        dispatch corresponding actions.
        """
        logger.debug("Setting up command system... CommandRegistry, KeyMapping and KeyProcessor")

        # Create key mapping from command defaults
        self.key_mapping = KeyMapping.from_command_defaults(
            self.command_registry.get_all_commands()
        )

        # Create key processor for handling input events
        self._key_processor: KeyProcessor = KeyProcessor(self.command_registry, self.key_mapping)
        self._controller.view.key_processor = self._key_processor

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
