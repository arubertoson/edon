src/edon_ui/__init__.py
---
# src/edon_ui/__init__.py
# This file makes Python treat the directory as a package.

# We will expose key classes here later, e.g.:
# from .main_window import MainWindow
# from .graphics_view import GraphicsView
# from .graphics_scene import GraphicsScene

# __all__ = ['MainWindow', 'GraphicsView', 'GraphicsScene'] 

---
src/edon_ui/app.py
---
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


---
src/edon_ui/base.py
---
# Create a new file like base_graphics_item.py or add to a common utils module
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import QPainter
from PySide6.QtCore import QRectF
from loguru import logger
import typing


class BaseEdonGraphicsObject(QGraphicsObject):
    def __init_subclass__(cls, **kwargs):
        """
        This hook is called when a class inherits from BaseEdonGraphicsObject.
        It checks if essential Qt graphics methods are directly overridden in the subclass.
        """
        super().__init_subclass__(**kwargs)

        # Check if 'paint' is directly implemented in the subclass's __dict__
        # and not just inherited from this base class or QGraphicsObject itself.
        if "paint" not in cls.__dict__ or cls.paint == BaseEdonGraphicsObject.paint:
            logger.warning(
                f"Class '{cls.__module__}.{cls.__name__}' inherits from BaseEdonGraphicsObject "
                f"but does not appear to directly override the 'paint' method. "
                f"If this is not an abstract class, it will raise an error at runtime."
            )

        if (
            "boundingRect" not in cls.__dict__
            or cls.boundingRect == BaseEdonGraphicsObject.boundingRect
        ):
            logger.warning(
                f"Class '{cls.__module__}.{cls.__name__}' inherits from BaseEdonGraphicsObject "
                f"but does not appear to directly override the 'boundingRect' method. "
                f"If this is not an abstract class, it will raise an error at runtime."
            )

    def boundingRect(self) -> QRectF:
        """
        This method MUST be overridden by all concrete (non-abstract) subclasses.
        """
        error_message = (
            f"CRITICAL ERROR: boundingRect() was called on an instance of "
            f"'{self.__class__.__module__}.{self.__class__.__name__}', but this class "
            f"has not properly overridden it. This method is essential for item layout and interaction."
        )
        # Log it first so it appears before the exception potentially gets re-wrapped by Qt
        logger.critical(error_message)
        raise NotImplementedError(error_message)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: typing.Optional[QWidget] = None,
    ) -> None:
        """
        This method MUST be overridden by all concrete (non-abstract) subclasses.
        """
        error_message = (
            f"CRITICAL ERROR: paint() was called on an instance of "
            f"'{self.__class__.__module__}.{self.__class__.__name__}', but this class "
            f"has not properly overridden it. This method is essential for drawing the item."
        )
        logger.critical(error_message)
        raise NotImplementedError(error_message)


---
src/edon_ui/context_menu.py
---
from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from edon_ui.views.scene import GraphicsScene
from edon_ui.widgets.node_spawner import NodeSpawningPanel

if TYPE_CHECKING:
    from PySide6.QtWidgets import QMainWindow, QWidget


class AppContextMenu(QMenu):
    def __init__(
        self,
        main_window: QMainWindow,
        position: QPoint,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.menu_position = position
        self.main_window = main_window

        from edon_ui.views.viewer import GraphicsView

        self.view = cast(GraphicsView, parent)

        self._add_file_actions()
        self.addSeparator()
        self._add_node_actions()

    def _add_file_actions(self):
        quit_action = QAction("Close", self)
        quit_action.triggered.connect(self.main_window.close)
        self.addAction(quit_action)

    def _add_node_actions(self):
        add_node_action = QAction("Add New Node", self)
        if self.menu_position is None or self.view is None:
            add_node_action.setEnabled(False)
        else:
            add_node_action.triggered.connect(self._request_node_spawner)
        self.addAction(add_node_action)

    def _request_node_spawner(self) -> None:
        """
        Handles the request to show the NodeSpawningPanel.
        """
        if not self.view or not self.menu_position:
            return

        # self.menu_position is the global click position.
        # NodeSpawningPanel's spawn_position needs to be in scene coordinates.
        # First, map the global menu position to view coordinates.
        spawn_position_view: QPoint = self.view.mapFromGlobal(self.menu_position)
        # Then, map the view coordinates to scene coordinates.
        spawn_position_scene: QPointF = self.view.mapToScene(spawn_position_view)
        panel_display_position_global: QPointF = QPointF(self.menu_position)

        # Parent the panel to the view for proper lifecycle management
        node_spawner = NodeSpawningPanel(
            controller=self.view._controller,
            spawn_position=spawn_position_scene,
            parent=self.view,
        )
        node_spawner.show_panel(panel_display_position_global)

    # Removed _request_add_new_node and _quit_application as they are now handled by emitting signals
    # and the connections will be made by the creator of this menu.

    # Example of how you might add other sections:
    # def _add_edit_actions(self):
    #     undo_action = QAction("Undo (Placeholder)", self)
    #     # undo_action.triggered.connect(self.parent_widget.some_undo_slot)
    #     self.addAction(undo_action)

    # def _add_node_actions(self):
    #     add_node_action = QAction("Add Node (Placeholder)", self)
    #     # add_node_action.triggered.connect(self.parent_widget.canvas.some_add_node_slot)
    #     self.addAction(add_node_action)


---
src/edon_ui/icon_engine.py
---
import sys

import qtawesome as qta
from loguru import logger
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget


def _get_qta_char_code(font_prefix):
    """
    Retrieves the integer Unicode character code for a qtawesome icon
    using the simpler qta.charmap().
    """
    try:
        char_map = qta.charmap(font_prefix)
        if char_map:
            logger.info(f"Char map for {font_prefix}: {char_map}")
            return char_map
        else:
            logger.warning(f"Warning: Char code not found for {font_prefix} using qta.charmap.")
    except Exception as e:
        logger.error(f"Error getting char code for {font_prefix} via qta.charmap: {e}")
        return None


class FontIconEngine(QIconEngine):
    """
    Custom QIconEngine that renders an icon from a qtawesome font character.
    """

    def __init__(self, full_icon_name: str, base_color: QColor = QColor("black")):
        super().__init__()
        self.icon_name = full_icon_name
        self.char_code = _get_qta_char_code(self.icon_name)
        self.prefix, self.char_key = self.icon_name.split(".")

        self.base_color = QColor(base_color)

    def paint(self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State):
        """
        Paints the icon character within the given rectangle.
        """
        if self.char_code is None:
            painter.save()
            painter.setPen(Qt.GlobalColor.red)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "?")
            painter.restore()

            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if hasattr(self, "size"):
            point_size = self.size.height()
            logger.error(f"Icon size: {self.size}")
        else:
            # Determine font point size based on the target rectangle's height
            # Adjust the factor (e.g., 0.75) to get the desired relative icon size
            point_size = int(rect.height() * 0.8)
            if point_size < 6:  # Ensure a minimum sensible font size
                point_size = 6

        rect.setLeft(rect.left() - point_size - 4)

        try:
            # Get the QFont for the font family (prefix) and calculated size
            icon_qfont = qta.font(self.prefix, point_size)
        except Exception as e:
            logger.error(
                f"Error getting qta.font for prefix '{self.prefix}': {e}. Using fallback."
            )
            icon_qfont = QFont()  # Default system font
            icon_qfont.setPointSize(point_size)

        painter.setFont(icon_qfont)

        # Determine color based on icon mode
        current_color = QColor(self.base_color)  # Start with the base color

        if mode == QIcon.Mode.Disabled:
            # For disabled state, typically use a desaturated or semi-transparent color
            # Using QColor's HSL values to desaturate and lighten
            h, s, l, a = current_color.getHsl()  # type: ignore
            current_color.setHsl(h, int(s * 0.3), min(255, l + 60), int(a * 0.6))
        elif mode == QIcon.Mode.Selected or mode == QIcon.Mode.Active:
            # For selected/active, make it slightly brighter or use a theme color
            # Here, we'll just make it a bit brighter if it's not too light already
            h, s, l, a = current_color.getHsl()  # type: ignore
            if l < 230:  # Avoid making very light colors pure white
                current_color.setHsl(h, s, min(255, l + 25), a)
            # Alternatively, you could use QApplication.palette().highlight().color()
            # current_color = QApplication.palette().color(QPalette.ColorRole.Highlight)

        painter.setPen(current_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.char_code)

        painter.restore()

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        """
        Returns a QPixmap rendering of the icon.
        This is essential for QIcon to work correctly in many contexts.
        """
        pm = QPixmap(size)
        pm.fill(Qt.GlobalColor.transparent)  # Transparent background for the pixmap

        painter = QPainter(pm)
        # The rect for painting on the pixmap is its full bounds
        self.paint(painter, QRect(QPoint(0, 0), size), mode, state)
        painter.end()  # Crucial to end painter when drawing on QPixmap directly

        return pm

    def clone(self) -> QIconEngine:
        """
        Returns a new instance of this icon engine. Required by QIconEngine.
        """
        return FontIconEngine(self.full_icon_name, self.base_color)

    def virtual_hook(self, id, data):
        """
        Handles virtual hooks if any.
        """
        return super().virtual_hook(id, data)


class FontIcon(QIcon):
    """
    Custom QIcon that uses FontIconEngine to render icons from qtawesome fonts.
    """

    def __init__(self, full_icon_name: str, color: QColor = QColor("black"), parent=None):
        # Create an instance of our custom engine
        self.engine = FontIconEngine(full_icon_name, color)
        # Initialize QIcon with the custom engine
        super().__init__(self.engine)

    def font(self, size: QSize = QSize(24, 24)):
        return qta.font(self.engine.prefix, size)

    def set_size(self, size: QSize):
        self.engine.size = size

    def char(self):
        return self.engine.char_code


# --- Example Usage ---
class TestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test FontIcon")
        layout = QVBoxLayout(self)

        # Create icons using the custom QtaFontIcon class
        icon_expand = FontIcon("fa5s.expand", QColor("dodgerblue"))
        icon_expand.set_size(QSize(32, 32))
        icon_user = FontIcon("fa5s.user-circle", QColor("green"))
        icon_cog_disabled = FontIcon("fa5s.cog", QColor("darkgray"))  # Base color for normal state
        icon_unknown = FontIcon("foo.bar")  # Test fallback for unknown icon

        # Create buttons and set icons
        button1 = QPushButton("Expand")
        button1.setIcon(icon_expand)
        button1.setIconSize(QSize(24, 24))  # QIcon will use engine to paint at this size
        layout.addWidget(button1)

        button2 = QPushButton("User")
        button2.setIcon(icon_user)
        button2.setIconSize(QSize(32, 32))
        layout.addWidget(button2)

        button3 = QPushButton("Settings (Disabled)")
        button3.setIcon(icon_cog_disabled)
        button3.setIconSize(QSize(48, 48))
        button3.setEnabled(False)  # This will trigger QIcon.Mode.Disabled
        layout.addWidget(button3)

        button4 = QPushButton("Unknown Icon")
        button4.setIcon(icon_unknown)
        button4.setIconSize(QSize(32, 32))
        layout.addWidget(button4)

        button5 = QPushButton("Selected State (Style Dependent)")
        # For selected state to show visually, the widget style must support it,
        # or you might need to handle it more explicitly if not a checkable button.
        button5.setCheckable(True)
        button5.setChecked(True)  # This can trigger QIcon.Mode.Selected or QIcon.Mode.On
        button5.setIcon(FontIcon("fa5s.check-square", QColor("purple")))
        button5.setIconSize(QSize(24, 24))
        layout.addWidget(button5)

        self.setLayout(layout)
        self.resize(300, 300)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # It's good practice to initialize qtawesome early,
    # though importing often does enough for basic use.
    # qta.init_resource() # If you're using its resource system

    test_widget = TestWidget()
    test_widget.show()
    sys.exit(app.exec())


---
src/edon_ui/project-guidelines.md
---
# Edon Python Code Style & Quality Guide

## 1. Language & Libraries

- Use **Python 3.13** features.
- Use **PySide6** for Qt.
- Always use **absolute imports**.

## 2. Type Hints

- All functions, methods, and class attributes **must** have type hints.
- Use **built-in generics** for concrete collections (e.g., `list[str]`, `dict[str, int]`).
- Use **`collections.abc`** for abstract types (e.g., `Iterable`, `Mapping`, `Callable`).
- Use **`X | Y`** for unions (e.g., `str | None`).
- Use `type` for type aliases (Python 3.12+), and `NewType` for distinct types.
- Use string literals for forward references.
- Use `from typing import TYPE_CHECKING` for type-only imports.
- Use `Protocol` for structural typing.

## 3. Docstrings & Comments

- Every public module, class, function, and method must have a **Google-style docstring**.
- Docstrings should summarize purpose, why it exists, don't list arguments, return values, and exceptions.
- Use **inline comments** to explain *why* (not *what*) for non-obvious logic.
- Keep comments accurate and up-to-date.

## 4. Naming & Structure

- Follow **Google Python Style Guide** naming conventions.
- Organize code to "read like a book": logical flow, clear blocks, and top-down structure.
- sort methods in a class by their purpose, not by their name.
- Use descriptive names for all identifiers.

## 5. Architecture

- **Core logic** (`src/edon/`) is UI-agnostic.
- **UI logic** and Qt dependencies go in `src/edon_ui/`.
- Use `GraphController` to mediate between model and view.

## 6. Dependencies & Logging

- Manage dependencies with `pyproject.toml` and `uv`.
- Use `loguru` for logging; avoid logging sensitive data.

## 7. Testing

- Place all tests in a `tests/` directory.
- Write unit tests for core logic and UI tests as needed.

---

This guide summarizes the most important rules for writing Python code in the Edon project. For details, see the full project and Python style guides.


---
src/edon_ui/theme.py
---
from PySide6.QtGui import QColor, QFont

# --- Primary Palette ---
COLOR_BACKGROUND_DARK = QColor("#2D2D2D")  # Dark grey, good for view/scene backgrounds
COLOR_BACKGROUND_MEDIUM = QColor("#6d6d6d")  # Dark slate gray, from image node background
COLOR_BACKGROUND_LIGHT = QColor("#b0b0b0")  # Lighter slate gray, from image input field background

COLOR_SURFACE = QColor("#4A4A4A")  # For surfaces on top of backgrounds (unused for now)

COLOR_TEXT_LIGHT = QColor("#D1D1D1")  # Light text for dark backgrounds (title, labels from image)
COLOR_TEXT_MEDIUM = QColor("#BBBBBB")  # Medium emphasis text (unused for now)
COLOR_TEXT_DARK = QColor("#202020")  # Dark text for light backgrounds (if you had them)
COLOR_TEXT_INPUT = QColor("#E0E0E0")  # Text inside input fields from image

# --- Accent Colors ---
ACCENT_PRIMARY = QColor("#FF6B6B")  # Red/coral for ports from image
ACCENT_SECONDARY = QColor("#7A81DD")  # A muted blue/purple, could be for selection or highlights
ACCENT_SUCCESS = QColor("#2ECC71")  # Green
ACCENT_WARNING = QColor("#F39C12")  # Orange
ACCENT_ERROR = QColor("#E74C3C")  # Red

# --- Node Specific (derived from image and palette) ---
NODE_BACKGROUND = QColor("#4A4A4A")
SUBGRAPH_NODE_BACKGROUND = QColor("#3E505B") # Distinct background for SubGraphNode instances
NODE_BORDER_DEFAULT = NODE_BACKGROUND.lighter(110)  # Subtle darker border
NODE_BORDER_SELECTED = QColor("#5F9FDF")  # A distinct blue for selection
NODE_BORDER_RADIUS = 4.0
NODE_BORDER_WIDTH_DEFAULT = 1.5
NODE_BORDER_WIDTH_SELECTED = 2.0

NODE_HORIZONTAL_PADDING = 10.0  # Padding inside the node, before socket row content starts
NODE_MIN_WIDTH = 125.0  # Minimum overall width for a node
NODE_MIN_HEIGHT = 60.0  # Minimum overall height for a node

NODE_TITLE_BACKGROUND = COLOR_BACKGROUND_DARK.darker(200)
NODE_TITLE_TEXT = COLOR_TEXT_LIGHT
NODE_TITLE_HEIGHT = 25.0  # Adjusted to look like image

NODE_CONTENT_BACKGROUND = COLOR_BACKGROUND_LIGHT.lighter(110)  # Background for input fields

NODE_LABEL_TEXT = COLOR_TEXT_LIGHT  # For labels like "A", "B", "Use Cache"

NODE_PORT_COLOR = ACCENT_PRIMARY
NODE_PORT_RADIUS = 7.0

# --- Fonts (matching Segoe UI look if available, otherwise common sans-serif) ---
FONT_FAMILY_UI = "Segoe UI"
FONT_NODE_TITLE = QFont(FONT_FAMILY_UI, 8, QFont.Weight.DemiBold)
FONT_NODE_LABEL = QFont(FONT_FAMILY_UI, 9)
FONT_NODE_INPUT = QFont(FONT_FAMILY_UI, 9)
FONT_NODE_FOOTER = QFont(FONT_FAMILY_UI, 9)


# --- Grid Colors ---
GRID_COLOR_LIGHT = QColor(55, 55, 55)  # Dots in the image background
GRID_COLOR_DARK = QColor(45, 45, 45)  # Not visible in image, but good for pattern

# --- Checkbox (can be styled further in QSS) ---
CHECKBOX_INDICATOR_CHECKED_BG = QColor("#4A90E2")  # Blue from typical checkbox
CHECKBOX_TEXT = NODE_LABEL_TEXT

# --- SpinBox/Input Fields (can be styled further in QSS) ---
INPUT_BACKGROUND = COLOR_BACKGROUND_LIGHT
INPUT_TEXT_COLOR = COLOR_TEXT_INPUT
INPUT_BORDER_COLOR = COLOR_BACKGROUND_MEDIUM.darker(120)

# --- Scene Specific Backgrounds ---
SCENE_BACKGROUND = QColor(30, 30, 30)  # Very dark gray for the furthest background
SCENE_ACTIVE_AREA_BACKGROUND = QColor(40, 40, 40)  # Background for the area where nodes primarily reside
SCENE_ACTIVE_AREA_BORDER = QColor(1, 1, 1)  # Border for the active area

# Socket Colors
SOCKET_BORDER_COLOR = QColor("#FF000000")  # Black
SOCKET_FILL_COLOR_DEFAULT = QColor("#FFAAAAAA")  # Light Gray

# Colors per socket type (using string keys)
SOCKET_FILL_COLORS = {
    "default": QColor("#FFAAAAAA"),  # Light Gray
    "number": QColor("#FF007ACC"),  # Blue
    "integer": QColor("#FF0055FF"),  # Bright Blue
    "float": QColor("#FF00BFFF"),  # Sky Blue
    "string": QColor("#FFFFA500"),  # Orange
    "boolean": QColor("#FFD60000"),  # Red
    "vector": QColor("#FF00C853"),  # Green
    "color": QColor("#FFFF4081"),  # Pink
    "matrix": QColor("#FF8D6E63"),  # Brown
    "image": QColor("#FF7C4DFF"),  # Purple
    "audio": QColor("#FF00B8D4"),  # Cyan
    "object": QColor("#FFB0BEC5"),  # Gray Blue
    "event": QColor("#FFFFFFFF"),  # White
    "enum": QColor("#FF9E9D24"),  # Olive
    "array": QColor("#FF6D4C41"),  # Deep Brown
    "resource": QColor("#FF8BC34A"),  # Light Green
    "time": QColor("#FFFFEB3B"),  # Yellow
    "angle": QColor("#FFFF7043"),  # Deep Orange
    "curve": QColor("#FFAB47BC"),  # Violet
    "path": QColor("#FF607D8B"),  # Blue Gray
    "data": QColor("#FF263238"),  # Dark Gray
    "custom": QColor("#FF00E676"),  # Neon Green
}

# Socket Properties
SOCKET_RADIUS = 6.0  # pixels
SOCKET_ROW_HEIGHT = 20.0  # Total vertical space for a socket row (for circle + label/widget)
SOCKET_PADDING = 5.0  # Padding around sockets for layout (e.g., above first socket row)
SOCKET_SPACING = 10.0  # Vertical spacing between socket visual elements (DEPRECATED if using ROW_HEIGHT consistently)
# We'll keep it for now but SOCKET_ROW_HEIGHT will be the primary driver for layout

# New theme constants
SOCKET_HOVER_FILL_COLOR = QColor("#FF0000")  # Example: Bright red for hover
EDGE_Z_VALUE = -1  # For finalized connections (currently drawn below nodes)
EDGE_Z_VALUE_DRAGGING = 100  # For connections being actively dragged
EDGE_COLOR_DEFAULT = QColor("#F0F0F0")  # Example: Light gray/white
EDGE_THICKNESS = 2.0
EDGE_COLOR_SELECTED = QColor("#FF0000")  # Example: Bright red for selected

EDGE_THICKNESS_DRAGGING = EDGE_THICKNESS
EDGE_COLOR_DRAGGING = EDGE_COLOR_DEFAULT

INPUT_BORDER_RADIUS = 4.0
INPUT_BACKGROUND_COLOR = QColor("#FF000000")  # Black
INPUT_TEXT_COLOR = QColor("#FFFFFFFF")  # White

# Add these lines (if not already present)
SOCKET_HORIZONTAL_PADDING = 4.0
SOCKET_VERTICAL_ITEM_PADDING = 2.0
SOCKET_VERTICAL_CONTENT_MARGIN = 4.0
SOCKET_CIRCLE_SPACING = 8.0
SOCKET_ITEM_FIXED_WIDTH = 70.0
SOCKET_ITEM_VERTICAL_MARGIN = 4.0
NODE_MIN_CONTENT_HEIGHT = 20.0

# For QLineEdit based input widgets in sockets
INPUT_WIDGET_BACKGROUND_COLOR = COLOR_BACKGROUND_MEDIUM  # A medium-dark gray
INPUT_WIDGET_TEXT_COLOR = QColor("#E0E0E0")  # Light gray for text
INPUT_WIDGET_BORDER_COLOR = QColor("#606060")  # Border for the input widget
INPUT_WIDGET_BORDER_RADIUS = 2  # Integer for rounded corners
INPUT_WIDGET_PADDING = 2  # Internal padding for QLineEdit

# Widths for the SocketWidgetAdaptor (total width including its margins)
SOCKET_INTEGER_WIDGET_ADAPTOR_WIDTH = 70.0
SOCKET_FLOAT_WIDGET_ADAPTOR_WIDTH = 70.0
SOCKET_STRING_WIDGET_ADAPTOR_WIDTH = 100.0  # Strings often need more space

# Horizontal margin for the SocketWidgetAdaptor itself
# This is the space the adaptor adds *around* the QLineEdit
# SOCKET_WIDGET_ADAPTOR_HORIZONTAL_MARGIN = getattr(
#     theme, "SOCKET_HORIZONTAL_PADDING", 2.0
# )  # Default to existing socket padding

# For SocketLabel text
SOCKET_LABEL_TEXT_COLOR = QColor("#B0B0B0")  # A slightly dimmer gray for socket labels
FONT_SOCKET_LABEL_DEFAULT_SIZE = 9  # Default font size for socket labels (adjust as needed)

# Default Colors for Icons
ICON_COLOR = "#C0C0C0"  # Light gray for icons
ICON_COLOR_ACTIVE = "#FFFFFF"  # White for active/hovered icons

# Default Colors for Text Inputs
INPUT_TEXT_DISABLED_COLOR = "#808080"  # Medium gray for disabled input text

# --- Global Application Stylesheet ---
# This is where we'll define QSS rules for the entire application.
# We'll use f-strings to embed theme constants directly into the stylesheet.

APPLICATION_STYLESHEET = f"""
/* === QLineEdit === */
QLineEdit {{
    background-color: {INPUT_WIDGET_BACKGROUND_COLOR.name()};
    color: {INPUT_WIDGET_TEXT_COLOR.name()};
    border: 1px solid {INPUT_WIDGET_BORDER_COLOR.name()};
    border-radius: {INPUT_WIDGET_BORDER_RADIUS}px;
    padding: {INPUT_WIDGET_PADDING}px;
    selection-background-color: {ACCENT_SECONDARY.name()};
    selection-color: {COLOR_TEXT_LIGHT.name()}; /* For selected text color */
}}

QLineEdit:focus {{
    border-color: {NODE_BORDER_SELECTED.name()}; /* Highlight border on focus */
}}

/* === QPushButton (Placeholder - customize as needed) === */
QPushButton {{
    background-color: {ACCENT_PRIMARY.name()};
    color: {COLOR_TEXT_LIGHT.name()};
    border-radius: {INPUT_BORDER_RADIUS}px;
    padding: 5px 10px;
    border: 1px solid {ACCENT_PRIMARY.darker(120).name()};
}}

QPushButton:hover {{
    background-color: {ACCENT_PRIMARY.lighter(120).name()};
}}

QPushButton:pressed {{
    background-color: {ACCENT_PRIMARY.darker(130).name()};
}}

/* === QCheckBox (Placeholder - customize as needed) === */
QCheckBox {{
    spacing: 5px; /* Space between indicator and text */
    color: {CHECKBOX_TEXT.name()};
}}

QCheckBox::indicator {{
    width: 13px;
    height: 13px;
    border-radius: 3px;
    border: 1px solid {INPUT_BORDER_COLOR.name()};
    background-color: {INPUT_BACKGROUND.name()};
}}

QCheckBox::indicator:checked {{
    background-color: {CHECKBOX_INDICATOR_CHECKED_BG.name()};
    border: 1px solid {CHECKBOX_INDICATOR_CHECKED_BG.darker(120).name()};
    image: url(none); /* Remove default checkmark if you want to use a custom one or none */
}}

QCheckBox::indicator:unchecked:hover {{
    border-color: {NODE_BORDER_SELECTED.name()};
}}

QCheckBox::indicator:checked:hover {{
    background-color: {CHECKBOX_INDICATOR_CHECKED_BG.lighter(120).name()};
    border-color: {CHECKBOX_INDICATOR_CHECKED_BG.darker(130).name()};
}}

/* Add more global styles here for other widgets or custom items by class name */

"""


---
src/edon_ui/commands/__init__.py
---
"""Command System for Edon UI.

This package implements a comprehensive command and hotkey management system.

Exports:
    - Core components:
        - `Command`: Dataclass representing a command.
        - `CommandRegistry`: Manages all defined commands.
        - `EditorContext`: Type alias for the context passed to command actions.
        - `ContextProvider`: Protocol for objects providing `EditorContext`.
    - Hotkey management:
        - `KeyMapping`: Manages mappings between hotkey sequences and command IDs.
    - Event processing:
        - `KeyProcessor`: Processes input events to trigger commands.
    - Built-in command definitions:
        - `ALL_COMMAND_DEFINITIONS`: A list of pre-defined `Command` objects.
    - Default registry instance:
        - `default_command_registry`: A pre-populated CommandRegistry instance.
"""

from .core import Command, ContextProvider, EditorContext, CommandRegistry
from .key_mapping import KeyMapping
from .key_processor import KeyProcessor
from .builtins import ALL_COMMAND_DEFINITIONS


def _create_and_populate_registry() -> CommandRegistry:
    """Creates and populates a CommandRegistry with all built-in commands."""
    registry = CommandRegistry()
    for cmd_def in ALL_COMMAND_DEFINITIONS:
        registry.register(cmd_def)
    return registry


default_command_registry: CommandRegistry = _create_and_populate_registry()

__all__ = [
    "Command",
    "CommandRegistry",
    "EditorContext",
    "ContextProvider",
    "KeyMapping",
    "KeyProcessor",
    "default_command_registry",
]


---
src/edon_ui/commands/builtins.py
---
"""Built-in command definitions for the application.

This file is responsible for defining the `ALL_COMMAND_DEFINITIONS` list,
which aggregates all command objects used by the application.
It imports action functions from the `actions` sub-package.
"""

from edon_ui.commands.actions.basic_actions import (
    close_action,
    delete_selection_action,
    help_action,
    window_toggle_maximize_action,
    action_show_node_spawner,
    action_enter_subgraph,
    action_exit_subgraph,
)
from edon_ui.commands.core import Command


def _parse_hotkey_sequence(hotkey_str: str | None) -> list[str] | None:
    """Parses a comma-separated hotkey string into a list of sequences."""
    if not hotkey_str:
        return None
    return hotkey_str.split(",")


ALL_COMMAND_DEFINITIONS: list[Command] = [
    Command(
        id="app.close",
        label="Close",
        category="Application",
        description="Close the application.",
        action=close_action,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+X"),
    ),
    Command(
        id="help.show",
        label="Help",
        category="Help",
        description="Show help dialog.",
        action=help_action,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+H"),
    ),
    Command(
        id="window.toggle_maximize",
        label="Toggle Maximize/Fullscreen",
        category="Window",
        description="Toggle window maximize/fullscreen state.",
        action=window_toggle_maximize_action,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+K,F"),
    ),
    Command(
        id="edit.delete_selection",
        label="Delete Selection",
        category="Edit",
        description="Delete selected items (nodes and edges).",
        action=delete_selection_action,
        default_hotkey_sequence=_parse_hotkey_sequence("D"),
    ),
    Command(
        id="graph.show_node_spawner",
        label="Add Node...",
        category="Graph",
        description="Opens a panel to search and add new nodes to the graph.",
        action=action_show_node_spawner,
        default_hotkey_sequence=_parse_hotkey_sequence("Shift+A"),
    ),
    Command(
        id="graph.enter_subgraph",
        label="Enter Subgraph",
        category="Graph Navigation",
        description="Enter the selected subgraph node to view/edit its internal graph.",
        action=action_enter_subgraph,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+E"),
    ),
    Command(
        id="graph.exit_subgraph",
        label="Exit Subgraph",
        category="Graph Navigation",
        description="Exit the current subgraph and return to its parent graph.",
        action=action_exit_subgraph,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+U"),  # "U" for "Up"
    ),
]


---
src/edon_ui/commands/core.py
---
"""Core data structures and protocols for the command system.

Defines:
- `EditorContext`: A type alias for the context object passed to commands.
- `ContextProvider`: A protocol for objects that can provide an `EditorContext`.
- `Command`: A dataclass representing an executable action with metadata.
- `CommandRegistry`: A class to manage a collection of `Command` objects.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from loguru import logger

from edon_ui.views.viewer import EditorContext

if TYPE_CHECKING:
    from PySide6.QtGui import QInputEvent


@runtime_checkable
class ContextProvider(Protocol):
    """A protocol for objects that can provide an EditorContext.

    This interface ensures that any object responsible for generating
    the context for command execution adheres to a common contract.
    """

    def provide_context(self, event: "QInputEvent | None" = None) -> EditorContext:
        """Provides the current editor context.

        The context might be influenced by the current state of the UI,
        the active document, or the event that triggered the command.

        Args:
            event: An optional QKeyEvent that might influence context creation.
                   For example, mouse position for context menus.

        Returns:
            The relevant EditorContext for a command action.
        """
        ...


@dataclass
class Command:
    """Represents a unique, executable command within the application.

    A command encapsulates an action, its metadata (like a user-facing label
    and category), and an optional default hotkey sequence.

    Attributes:
        id: A unique string identifier for the command (e.g., "file.save").
        label: A user-friendly name for the command (e.g., "Save File").
        category: A string used to group related commands (e.g., "File", "Edit").
        action: The callable to execute when the command is triggered.
            It takes an `EditorContext` object and should return `True` if the
            action was successful or handled, `False` otherwise.
        default_hotkey_sequence: An optional list of strings representing the
            suggested default hotkey sequence (e.g., `["Ctrl+S"]` or `["Ctrl+K", "S"]`).
        description: An optional, more detailed description of the command.
    """

    id: str
    label: str
    category: str
    action: Callable[[EditorContext], bool]
    default_hotkey_sequence: list[str] | None = None
    description: str | None = None


class CommandRegistry:
    """Manages the collection of all available commands.

    This registry provides a central place to store and retrieve `Command` objects.
    It ensures that command IDs are unique and allows for easy lookup of commands
    by ID or category.
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """Registers a command with the registry.

        If a command with the same ID already exists, it will be overwritten.
        Consider logging a warning in such cases.

        Args:
            command: The `Command` object to register.
        """
        if command.id in self._commands:
            logger.warning(f"Command '{command.id}' is being overwritten in CommandRegistry.")
        self._commands[command.id] = command

    def get_command(self, command_id: str) -> Command | None:
        """Retrieves a command by its unique ID.

        Args:
            command_id: The ID of the command to retrieve.

        Returns:
            The `Command` object if found, otherwise `None`.
        """
        return self._commands.get(command_id)

    def get_all_commands(self) -> list[Command]:
        """Retrieves all registered commands.

        Returns:
            A list of all `Command` objects in the registry.
        """
        return list(self._commands.values())

    def get_commands_by_category(self) -> dict[str, list[Command]]:
        """Groups all registered commands by their category.

        Returns:
            A dictionary where keys are category names and values are lists
            of `Command` objects belonging to that category.
        """
        categories: dict[str, list[Command]] = {}
        for command_instance in self._commands.values():
            categories.setdefault(command_instance.category, []).append(command_instance)
        return categories


---
src/edon_ui/commands/key_mapping.py
---
"""Manages the mapping between hotkey sequences and command identifiers.

This module defines the `HotkeyMapping` class, which is responsible for
storing and resolving hotkey bindings. It allows for setting default
bindings based on command definitions and can be extended to support
loading and saving user-customized hotkey configurations.
"""

from typing import TYPE_CHECKING, Self
from loguru import logger

if TYPE_CHECKING:
    from edon_ui.commands.core import Command


class KeyMapping:
    """Manages the current mapping between hotkey sequences and command IDs.

    This class stores user-configurable hotkey bindings. It can be initialized
    with default hotkeys derived from command definitions and provides methods
    to look up command IDs by key sequence and vice-versa.
    """

    def __init__(self) -> None:
        self._bindings: dict[tuple[str, ...], str] = {}  # sequence_tuple -> command_id

    @classmethod
    def from_command_defaults(cls, commands: list["Command"]) -> Self:
        """Creates a new KeyMapping instance populated with command defaults.

        Args:
            commands: A list of `Command` objects to derive default hotkeys from.

        Returns:
            A new KeyMapping instance with default bindings loaded.
        """
        instance = cls()
        for cmd in commands:
            if cmd.default_hotkey_sequence:
                sequence_tuple = tuple(cmd.default_hotkey_sequence or [])
                instance.set_binding(sequence_tuple, cmd.id)
        return instance

    def set_binding(self, sequence: tuple[str, ...], command_id: str) -> None:
        """Sets or overwrites a hotkey binding for a command ID.

        Associates a key sequence with a command ID. Overwrites existing bindings
        for the sequence or the command ID to maintain a one-to-one relationship
        between a sequence and its command, and a command to its primary sequence.

        Args:
            sequence: A tuple of strings representing the key sequence.
            command_id: The unique identifier of the command to bind.
        """
        if sequence in self._bindings:
            existing_cmd_id = self._bindings[sequence]
            if existing_cmd_id != command_id:
                logger.warning(
                    f"KeyMapping: Sequence {sequence} reassigned from '{existing_cmd_id}' to '{command_id}'."
                )
            del self._bindings[sequence]

        current_sequence_for_command = self.get_sequence_for_command_id(command_id)
        if current_sequence_for_command and current_sequence_for_command != sequence:
            logger.warning(
                f"KeyMapping: Command '{command_id}' remapped from {current_sequence_for_command} to {sequence}."
            )
            if current_sequence_for_command in self._bindings:
                del self._bindings[current_sequence_for_command]

        self._bindings[sequence] = command_id
        logger.debug(f"KeyMapping: Bound sequence {sequence} to command '{command_id}'.")

    def get_command_id_for_sequence(self, sequence: tuple[str, ...]) -> str | None:
        """Retrieves the command ID associated with a given hotkey sequence.

        Args:
            sequence: A tuple of strings representing the key sequence.

        Returns:
            The command ID if the sequence is bound, otherwise `None`.
        """
        return self._bindings.get(sequence)

    def get_sequence_for_command_id(self, command_id: str) -> tuple[str, ...] | None:
        """Retrieves the hotkey sequence associated with a given command ID.

        Args:
            command_id: The unique identifier of the command.

        Returns:
            The hotkey sequence if bound, otherwise `None`.
        """
        for seq, cmd_id in self._bindings.items():
            if cmd_id == command_id:
                return seq
        return None

    def get_all_bindings(self) -> dict[tuple[str, ...], str]:
        """Retrieves all current hotkey bindings.

        Returns:
            A copy of all sequence-to-command_id mappings.
        """
        return self._bindings.copy()

    def is_prefix_of_any_binding(self, sequence_tuple: tuple[str, ...]) -> bool:
        """Checks if the given sequence is a prefix of any longer bound sequence.

        Args:
            sequence_tuple: The sequence to check.

        Returns:
            True if `sequence_tuple` is a prefix of at least one longer binding,
            False otherwise.
        """
        if not sequence_tuple:  # An empty sequence cannot be a prefix
            return False

        for bound_sequence in self._bindings.keys():
            if len(bound_sequence) > len(sequence_tuple) and bound_sequence[: len(sequence_tuple)] == sequence_tuple:
                return True
        return False

    # TODO(dev): Add methods to load/save from/to JSON/config file
    # e.g., def load_from_config(self, config_path: str) -> None:
    # e.g., def save_to_config(self, config_path: str) -> None:


---
src/edon_ui/commands/key_processor.py
---
"""Processes raw input events to trigger commands based on hotkey mappings.

This module defines the `KeyProcessor` class, which listens to input events
(keyboard and mouse), manages partial key/action sequences, and, upon matching
a complete hotkey sequence, retrieves and executes the corresponding command.
"""

# TODO: I kind of want to be able to set "tool context", that will swap the key mapping.

from loguru import logger
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Qt, QEvent
from PySide6.QtGui import QKeyEvent, QMouseEvent, QInputEvent, QKeySequence

if TYPE_CHECKING:
    from .core import CommandRegistry, ContextProvider
    from .key_mapping import KeyMapping

STANDALONE_MODIFIERS = ("Ctrl", "Shift", "Alt", "Meta")
IGNORED_EVENT_TYPES = (
    QEvent.Type.MouseMove,
    QEvent.Type.HoverMove,
    QEvent.Type.Paint,
    QEvent.Type.Resize,
    QEvent.Type.LayoutRequest,
    QEvent.Type.Enter,
    QEvent.Type.Leave,
    QEvent.Type.FocusIn,
    QEvent.Type.FocusOut,
    QEvent.Type.WindowActivate,
    QEvent.Type.WindowDeactivate,
    QEvent.Type.UpdateRequest,
    QEvent.Type.Polish,
    QEvent.Type.PolishRequest,
    QEvent.Type.MetaCall,
    QEvent.Type.Timer,
    QEvent.Type.ChildAdded,
    QEvent.Type.ChildRemoved,
    QEvent.Type.ChildPolished,
    QEvent.Type.GrabMouse,
    QEvent.Type.UngrabMouse,
    QEvent.Type.GrabKeyboard,
    QEvent.Type.UngrabKeyboard,
    # Add other event types to ignore quickly if they become noisy or are irrelevant.
)


def qkeyevent_to_string(event: QKeyEvent) -> str | None:
    """Converts a QKeyEvent to a canonical string representation."""
    if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
        return None

    key_str = QKeySequence(event.keyCombination()).toString(
        QKeySequence.SequenceFormat.PortableText
    )
    return key_str if key_str else None


def qmouseevent_to_string(event: QMouseEvent) -> str | None:
    """Converts a QMouseEvent to a canonical string representation.

    Handles MouseButtonPress events.
    Format: [Modifiers+]MouseButtonAction (e.g., "Ctrl+LMBClick", "RMBClick")
    """
    modifiers_str = ""
    qt_mods = event.modifiers()
    if qt_mods & Qt.KeyboardModifier.ControlModifier:
        modifiers_str += "Ctrl+"
    if qt_mods & Qt.KeyboardModifier.MetaModifier:
        modifiers_str += "Meta+"
    if qt_mods & Qt.KeyboardModifier.AltModifier:
        modifiers_str += "Alt+"
    if qt_mods & Qt.KeyboardModifier.ShiftModifier:
        modifiers_str += "Shift+"

    button_action_str: str | None = None
    if event.button() == Qt.MouseButton.LeftButton:
        button_action_str = "LMB"
    elif event.button() == Qt.MouseButton.RightButton:
        button_action_str = "RMB"
    elif event.button() == Qt.MouseButton.MiddleButton:
        button_action_str = "MMB"
    # TODO: Potentially handle Qt.MouseButton.BackButton, Qt.MouseButton.ForwardButton if needed

    if not button_action_str:
        return None  # Unhandled mouse button for sequences

    if event.type() == QMouseEvent.Type.MouseButtonPress:
        button_action_str += "Click"
    elif event.type() == QMouseEvent.Type.MouseButtonRelease:
        button_action_str += "Release"

    return modifiers_str + button_action_str


class KeyProcessor(QObject):
    """Processes Qt input events (keyboard/mouse) for command execution,
    intended to be used as an event filter.
    """

    def __init__(
        self,
        command_registry: "CommandRegistry",
        hotkey_mapping: "KeyMapping",
        sequence_timeout_ms: int = 1500,
    ) -> None:
        super().__init__()
        self.command_registry = command_registry
        self.hotkey_mapping = hotkey_mapping
        self._current_typed_sequence: list[str] = []

        self._sequence_timer = QTimer(self)
        self._sequence_timer.setSingleShot(True)
        self._sequence_timer.timeout.connect(self._reset_typed_sequence)
        self._sequence_timeout_ms: int = sequence_timeout_ms

    def set_sequence_timeout(self, timeout_ms: int) -> None:
        """Sets the timeout for multi-key sequences."""
        if timeout_ms > 0:
            self._sequence_timeout_ms = timeout_ms
        else:
            logger.warning(
                f"Attempted to set invalid sequence timeout: {timeout_ms}ms. Using current or default."
            )

    def _process_event_for_command_sequence(
        self, event: QInputEvent, context_provider: "ContextProvider"
    ) -> bool:
        """Core logic for processing an event to find and execute a command sequence."""
        # Can you help me break this function down, we are trying to ensure that sequences like "Ctr+K", "F" is stored, but it seems it doesn't work properly AI?
        action_str, _, should_continue = self._determine_action_string_and_details(event)

        if not should_continue or action_str is None:
            return False

        # XXX: we need a state object to for the even tracking, this is quite
        # silly how it's handled.
        if self._current_typed_sequence and "KeyRelease" in _:
            return False

        self._current_typed_sequence.append(action_str)
        self._sequence_timer.start(self._sequence_timeout_ms)
        current_sequence_tuple = tuple(self._current_typed_sequence)

        logger.debug(f"KeyProcessor: Current sequence: {self._current_typed_sequence}")

        command_id = self.hotkey_mapping.get_command_id_for_sequence(current_sequence_tuple)
        if command_id:
            # XXX: Future enhancement: Commands should be able to specify if they
            # trigger on KeyPress, KeyRelease, or both. For now, all hotkey-triggered
            # commands execute on KeyPress only to prevent double execution.
            if event.type() == QEvent.Type.KeyPress:
                return self._handle_found_command(
                    command_id, event, context_provider, current_sequence_tuple
                )
            else:
                # Sequence matched on KeyRelease (or other non-KeyPress event),
                # but command execution is currently tied to KeyPress.
                # Reset sequence and consume event as it's part of a recognized hotkey.
                logger.trace(
                    f"KeyProcessor: Sequence {current_sequence_tuple} matched command '{command_id}' "
                    f"on event type {event.type()}. Resetting sequence, not re-executing command."
                )
                self._reset_typed_sequence()
                return True  # Event handled as part of a recognized sequence

        if self.hotkey_mapping.is_prefix_of_any_binding(current_sequence_tuple):
            return True

        logger.debug(
            f"KeyProcessor: Sequence {current_sequence_tuple} not a full command or prefix. Resetting sequence."
        )
        self._reset_typed_sequence()
        return False  # Not a command, not a prefix

    def _determine_action_string_and_details(
        self, event: QInputEvent
    ) -> tuple[str | None, str, bool]:
        """
        Determines the action string and event details from an input event.
        """
        action_str: str | None = None
        specific_event_details = ""

        if isinstance(event, QKeyEvent):
            qt_event_type = event.type()
            event_type_name = (
                "KeyPress" if qt_event_type == QKeyEvent.Type.KeyPress else "KeyRelease"
            )
            specific_event_details = f"type={event_type_name}, key={event.key()}, mods={event.modifiers()}, text='{event.text()}'"
            action_str = qkeyevent_to_string(event)
        elif isinstance(event, QMouseEvent):
            qt_event_type = event.type()
            event_type_name = (
                "MouseButtonPress"
                if qt_event_type == QMouseEvent.Type.MouseButtonPress
                else "MouseButtonRelease"
            )
            specific_event_details = f"type={event_type_name}, button={event.button()}, pos={event.position()}, mods={event.modifiers()}"
            action_str = qmouseevent_to_string(event)
        else:
            logger.warning(
                f"KeyProcessor._determine_action_string_and_details: Received unexpected event type: {type(event).__name__}"
            )
            return None, specific_event_details, False

        logger.trace(
            f"KeyProcessor._determine_action_string_and_details received: {specific_event_details}"
        )

        if not action_str:
            logger.trace(
                f"KeyProcessor: Event ({specific_event_details}) did not convert to action string. Current sequence: {self._current_typed_sequence}"
            )
            return None, specific_event_details, False  # Not a processable action

        # Handle standalone modifier strings
        is_standalone_modifier_str = action_str in STANDALONE_MODIFIERS
        if (
            is_standalone_modifier_str
            and not self._current_typed_sequence
            and isinstance(event, QKeyEvent)
        ):
            logger.trace(f"Ignoring standalone modifier string: {action_str}")
            return action_str, specific_event_details, False

        logger.trace(
            f"KeyProcessor._determine_action_string_and_details: Returning action_str: {action_str}, specific_event_details: {specific_event_details}, should_continue: True"
        )
        return action_str, specific_event_details, True

    def _handle_found_command(
        self,
        command_id: str,
        event: QInputEvent,
        context_provider: "ContextProvider",
        current_sequence_tuple: tuple[str, ...],
    ) -> bool:
        """Handles the execution of a command once its ID is found."""
        command = self.command_registry.get_command(command_id)
        if command:
            editor_context = context_provider.provide_context(event)
            context_event_type = (
                type(editor_context.event).__name__ if editor_context.event else "None"
            )
            logger.info(
                f"KeyProcessor: Executing command '{command.id}' for sequence: {current_sequence_tuple}. "
                f"Context event: {context_event_type}, Selected items: {len(editor_context.selected_items)}"
            )
            command.action(editor_context)
            self._reset_typed_sequence()
            return True  # Event handled
        else:
            logger.error(
                f"Command ID '{command_id}' found in hotkey map but not in registry. Sequence: {current_sequence_tuple}"
            )
            self._reset_typed_sequence()
            return False  # Command not found, sequence was valid but failed

    def _reset_typed_sequence_and_log_issue(
        self, event: QInputEvent | None, issue_message: str
    ) -> None:
        """Resets sequence and logs an issue, optionally with event details."""
        log_message = issue_message
        if event:
            if isinstance(event, QKeyEvent):
                log_message += f" (QKeyEvent: key={event.key()}, modifiers={event.modifiers()}, text='{event.text()}')"
            elif isinstance(event, QMouseEvent):
                log_message += f" (QMouseEvent: type={event.type()}, button={event.button()}, pos={event.position()})"
            else:
                log_message += f" (Event type: {type(event).__name__})"
        logger.warning(log_message)
        self._reset_typed_sequence()

    def _reset_typed_sequence(self) -> None:
        """Resets the currently typed key sequence and stops the timer."""
        if self._current_typed_sequence:
            logger.debug(f"KeyProcessor: Resetting sequence: {self._current_typed_sequence}")
            self._current_typed_sequence.clear()
        if self._sequence_timer.isActive():
            self._sequence_timer.stop()


---
src/edon_ui/commands/layout_algorithms.py
---
"""Provides algorithms for graph layout and topology analysis on UI items.

This module contains functions for determining connected subgraphs within selections,
constructing directed graph representations of UI components, and performing
topological sorting for layout ranking.
"""

from collections import deque
from loguru import logger

from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem

# XXX: Type Aliases for clarity if complex UI types are involved
# Example: NodeItemType = "NodeItem" # Replace with actual import if available

# XXX: Spacing constants for hierarchical layout (can be adjusted or moved if needed)
H_SPACING_HIERARCHICAL = 100.0  # Horizontal space between ranks
V_SPACING_HIERARCHICAL_WITHIN_RANK = 20.0  # Vertical space between nodes in the same rank
RANK_START_X = 0.0  # Initial X for the first rank
RANK_START_Y = 0.0  # Initial Y for the first node in any rank


def determine_node_selection_topology(
    selected_nodes: list[NodeItem], all_edges_in_scene: list[EdgeItem]
) -> list[list[NodeItem]]:
    """
    Determines the connected subgraphs within a list of selected UI nodes.

    This is useful for applying actions (like layout) independently to
    disconnected groups of selected nodes.

    Args:
        selected_nodes: A list of NodeItem instances that are currently selected.
        all_edges_in_scene: A list of all EdgeItem instances in the scene.

    Returns:
        A list of lists, where each inner list contains NodeItems forming a
        connected subgraph within the original selection.
    """
    if not selected_nodes:
        return []

    # Assuming NodeItem has a 'node_entity_id' string attribute
    adj: dict[str, list[str]] = {node.entity_id: [] for node in selected_nodes}
    selected_node_ids_set = {node.entity_id for node in selected_nodes}
    node_map_by_id: dict[str, NodeItem] = {node.entity_id: node for node in selected_nodes}

    for edge in all_edges_in_scene:
        # Assuming EdgeItem has 'source_socket_item.parent_node_entity_id' and
        # 'target_socket_item.parent_node_entity_id'
        source_id = edge.source_socket_item.parent_node_entity_id  # type: ignore
        target_id = edge.target_socket_item.parent_node_entity_id  # type: ignore

        # Consider only edges between nodes in the current selection
        if source_id in selected_node_ids_set and target_id in selected_node_ids_set:
            adj[source_id].append(target_id)
            adj[target_id].append(source_id)

    visited_ids: set[str] = set()
    subgraphs: list[list[NodeItem]] = []

    for node in selected_nodes:
        if node.entity_id not in visited_ids:
            current_subgraph_nodes: list[NodeItem] = []
            q = deque()  # Use collections.deque for efficient queue operations in BFS

            q.append(node)
            visited_ids.add(node.entity_id)

            while q:
                curr_node = q.popleft()
                current_subgraph_nodes.append(curr_node)

                for neighbor_id in adj[curr_node.node_entity_id]:
                    if neighbor_id not in visited_ids:
                        visited_ids.add(neighbor_id)
                        q.append(node_map_by_id[neighbor_id])

            if current_subgraph_nodes:
                subgraphs.append(current_subgraph_nodes)

    logger.debug(f"Determined selection topology: {len(subgraphs)} subgraph(s).")
    for i, sg in enumerate(subgraphs):
        # Assuming NodeItem has a 'title' attribute or fallback to 'node_entity_id'
        titles = [getattr(n, "title", n.entity_id) for n in sg]
        logger.debug(f"  Subgraph {i + 1}: {titles}")

    return subgraphs


def get_directed_graph_of_component(
    component_nodes: list[NodeItem], all_edges_in_scene: list[EdgeItem]
) -> dict[str, list[str]]:
    """
    Constructs a directed graph (adjacency list) for connections
    strictly within the given component of UI nodes.

    This is useful for preparing a component for operations like hierarchical layout.

    Args:
        component_nodes: A list of NodeItems forming a connected component.
        all_edges_in_scene: All EdgeItems in the scene.

    Returns:
        A dictionary where keys are node_entity_ids from the component,
        and values are lists of node_entity_ids of their direct children
        also within the component.
    """
    if not component_nodes:
        return {}

    directed_adj: dict[str, list[str]] = {node.entity_id: [] for node in component_nodes}
    component_node_ids_set = {node.entity_id for node in component_nodes}

    for edge in all_edges_in_scene:
        if not edge.source_socket_item or not edge.target_socket_item:
            logger.trace("get_directed_graph_of_component: Edge missing source/target socket item. Skipping.")
            continue

        source_node_id = edge.source_socket_item.parent_node_entity_id  # type: ignore
        target_node_id = edge.target_socket_item.parent_node_entity_id  # type: ignore

        if source_node_id in component_node_ids_set and target_node_id in component_node_ids_set:
            if target_node_id not in directed_adj[source_node_id]:
                directed_adj[source_node_id].append(target_node_id)

    component_titles = [getattr(n, "title", n.entity_id) for n in component_nodes]
    logger.debug(f"Directed graph for component {component_titles}: {directed_adj}")
    return directed_adj


def topological_sort_ui_component(
    directed_adj: dict[str, list[str]],
    nodes_in_component_map: dict[str, NodeItem],
) -> list[list[NodeItem]]:
    """
    Performs a topological sort on a directed graph component of UI nodes.

    The result is a list of ranks (levels), where each rank is a list of nodes.
    This is suitable for hierarchical layout algorithms.

    Args:
        directed_adj: An adjacency list for the component (node_id -> list_of_child_ids).
        nodes_in_component_map: A map from node_id to NodeItem for nodes in this component.

    Returns:
        A list of lists of NodeItems, where each inner list is a rank/level
        in the topological sort. Returns an empty list if a cycle is detected
        or the graph is empty, indicating layout cannot proceed this way.
    """
    if not directed_adj or not nodes_in_component_map:
        return []

    in_degree: dict[str, int] = {node_id: 0 for node_id in directed_adj}
    for node_id in directed_adj:
        for child_id in directed_adj[node_id]:
            if child_id in in_degree:
                in_degree[child_id] += 1
            else:
                logger.warning(
                    f"TopologicalSort: Node '{child_id}' (child of '{node_id}') not in component map. In-degree might be skewed for external nodes."
                )

    queue = deque()
    for node_id in directed_adj:
        if in_degree[node_id] == 0:
            queue.append(node_id)

    ranked_nodes: list[list[NodeItem]] = []
    processed_nodes_count = 0

    while queue:
        current_rank_node_ids = list(queue)
        queue.clear()

        current_rank_node_items: list[NodeItem] = []
        if not current_rank_node_ids:
            break

        for node_id in current_rank_node_ids:
            if node_id in nodes_in_component_map:
                current_rank_node_items.append(nodes_in_component_map[node_id])
                processed_nodes_count += 1
            else:
                logger.error(f"TopologicalSort: Node ID '{node_id}' from queue not found in component map.")
                continue

            for child_id in directed_adj.get(node_id, []):
                if child_id in in_degree:
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        queue.append(child_id)

        if current_rank_node_items:
            ranked_nodes.append(current_rank_node_items)

    if processed_nodes_count != len(nodes_in_component_map):
        problematic_nodes = [
            getattr(nodes_in_component_map[nid], "title", nid)
            for nid, deg in in_degree.items()
            if deg > 0 and nid in nodes_in_component_map
        ]
        logger.warning(
            f"TopologicalSort: Cycle detected in UI component or graph was disconnected. "
            f"Processed {processed_nodes_count}/{len(nodes_in_component_map)} nodes. "
            f"Nodes possibly in cycle: {problematic_nodes}"
        )
        return []

    logger.debug(f"Topological sort of UI component resulted in {len(ranked_nodes)} ranks.")
    return ranked_nodes


# Constants that were in builtins.py, related to arrangement actions that might use these algos.
# Consider if these should live here, or be passed into specific layout functions that use them,
# or live closer to the actions that call these layout functions. For now, co-locating here.
V_SPACING_ARRANGE = 10.0  # General vertical spacing, might be for a different algo
H_SPACING_ARRANGE = 50.0  # General horizontal spacing, might be for a different algo


---
src/edon_ui/commands/actions/__init__.py
---
# This file makes 'actions' a Python package


---
src/edon_ui/commands/actions/basic_actions.py
---
"""Basic, non-graph-algorithm command actions."""

from loguru import logger
from PySide6.QtCore import QPointF
from PySide6.QtGui import QCursor, QMouseEvent

from edon.graph import EntitySubGraphNode
from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem

# XXX: Editor Context should probably be a protocol.
from edon_ui.views.viewer import EditorContext
from edon_ui.widgets.node_spawner import NodeSpawningPanel


def close_action(context: EditorContext) -> bool:
    """Handles the command to close the main application window.

    Args:
        context: The current editor context, expected to have a `window` attribute
                 referencing the main application window.

    Returns:
        True if the close operation was attempted, False if the window context was missing.
    """
    if not hasattr(context, "window") or context.window is None:
        logger.warning("Close action: No window found in context.")
        return False
    logger.info("Executing close_action.")
    context.window.close()
    return True


def help_action(context: EditorContext) -> bool:
    """Placeholder action for showing a help dialog or help information.

    Currently, this action logs a message and prints to the console.
    It should be implemented to display actual help content.

    Args:
        context: The current editor context (unused in placeholder).

    Returns:
        True, indicating the action was handled (as a placeholder).
    """
    logger.info("Executing help_action (placeholder).")
    print("Help dialog would open here. (Placeholder Implementation)")
    return True


def window_toggle_maximize_action(context: EditorContext) -> bool:
    """Toggles the main application window between fullscreen/maximized and normal states.

    Args:
        context: The current editor context, expected to have a `window` attribute
                 referencing the main application window.

    Returns:
        True if the toggle operation was attempted, False if the window context was missing.
    """
    if not hasattr(context, "window") or context.window is None:
        logger.warning("Toggle maximize action: No window found in context.")
        return False

    current_state = context.window.isFullScreen()
    logger.info(f"Executing window_toggle_maximize_action. Current fullscreen: {current_state}")
    if current_state:
        context.window.showNormal()
    else:
        context.window.showFullScreen()
    return True


def delete_selection_action(context: EditorContext) -> bool:
    """Deletes currently selected nodes and edges from the graph scene.

    Retrieves selected NodeItem and EdgeItem instances from the context
    and requests their deletion via the context's manager.
    """
    node_items = [item for item in context.selected_items if isinstance(item, NodeItem)]
    edge_items = [item for item in context.selected_items if isinstance(item, EdgeItem)]

    if not node_items and not edge_items:
        logger.info("Delete selection action: Nothing selected to delete.")
        return False

    logger.info(
        f"Executing delete_selection_action: Deleting {len(node_items)} nodes and {len(edge_items)} edges."
    )

    if node_items:
        node_ids = [node.entity_id for node in node_items]
        try:
            context.controller.handle_ui_node_deletion_request(node_ids)
        except Exception as e:
            logger.error(f"Error during node deletion request: {e}")
            return False

    if edge_items:
        try:
            context.controller.handle_ui_edge_deletion_request(edge_items)
        except Exception as e:
            logger.error(f"Error during edge deletion request: {e}")
            return False

    return True


def action_show_node_spawner(context: EditorContext) -> bool:
    """
    Action to show the NodeSpawningPanel.
    The panel is positioned based on mouse event or current cursor position.
    The node spawn position is derived from this.
    """
    logger.debug("Executing action: Show Node Spawner")
    graph_controller = context.controller
    view = context.view

    # Determine global position for the panel itself
    global_pos_for_panel: QPointF
    if context.event and isinstance(context.event, QMouseEvent):
        global_pos_for_panel = context.event.globalPosition()
        logger.trace(f"Node spawner panel position from MouseEvent: {global_pos_for_panel}")
    else:
        # Fallback for hotkey invocation or non-mouse event: use current mouse cursor position
        cursor_pos = QCursor.pos()
        global_pos_for_panel = QPointF(cursor_pos)
        logger.trace(f"Node spawner panel position from QCursor: {global_pos_for_panel}")

    # Determine scene position for the node to be spawned
    # QGraphicsView.mapFromGlobal() expects QPoint, mapToScene() expects QPoint or QPolygon etc.
    view_pos = view.mapFromGlobal(global_pos_for_panel.toPoint())
    scene_pos_for_node = view.mapToScene(view_pos)
    logger.trace(f"Node spawn position in scene coordinates: {scene_pos_for_node}")

    # Ensure the panel is parented to the view or main window to manage its lifecycle and positioning
    # Using view as parent makes sense for a view-specific popup.
    # The panel is WA_DeleteOnClose, so it will clean itself up.
    panel = NodeSpawningPanel(graph_controller, scene_pos_for_node, parent=view)
    panel.show_panel(global_pos_for_panel)
    return True


def action_enter_subgraph(context: EditorContext) -> bool:
    """
    Action to enter the selected SubGraphNode.
    """
    logger.debug("Executing action: Enter Subgraph")
    if not hasattr(context, "controller") or context.controller is None:
        logger.warning("Enter Subgraph action: No controller found in context.")
        return False

    controller = context.controller
    selected_items = context.selected_items

    if len(selected_items) != 1:
        logger.trace(
            f"Expected 1 selected item for subgraph entry, found {len(selected_items)}. No action."
        )
        return False

    item = selected_items[0]
    if not isinstance(item, NodeItem):
        logger.trace(f"Selected item is not a NodeItem. Type: {type(item)}. No action.")
        return False

    entity_id = item.entity_id
    entity_node = context.controller.graph.get_node(entity_id)
    assert entity_node is not None, (
        f"CRITICAL: EntityNode with ID {entity_id} not found in graph despite UI item existing."
    )

    if not isinstance(entity_node, EntitySubGraphNode):
        logger.trace(
            f"Selected NodeItem's entity is not a SubGraphNode. "
            f"Entity ID: {entity_node.id}, Type: {type(entity_node)}. No action."
        )
        return False

    controller.enter_subgraph(item)

    return True


def action_exit_subgraph(context: EditorContext) -> bool:
    """
    Action to exit the current subgraph and return to the parent graph.
    """
    logger.debug("Executing action: Exit Subgraph")
    if not hasattr(context, "controller") or context.controller is None:
        logger.warning("Exit Subgraph action: No controller found in context.")
        return False

    controller = context.controller
    if not controller.context_stack.is_at_root():
        logger.info(f"Exiting subgraph. Current depth: {controller.context_stack.depth}")
        # Assuming exit_subgraph() will be implemented on WorkspaceController
        # based on memory.md.
        # This method is expected to handle popping from the graph_context_stack
        # and updating the view.
        if hasattr(controller, "exit_subgraph"):
            controller.exit_subgraph()
            return True
        else:
            logger.error("WorkspaceController does not have an exit_subgraph method.")
            return False
    else:
        logger.info("Exit Subgraph action: Already at root graph. No action taken.")
        return False


---
src/edon_ui/widgets/__init__.py
---
"""Initializes the socket_components sub-package.

This package provides various UI components used in the rendering and interaction
of node sockets, including graphical items, adaptors for Qt widgets, specialized
editor widgets, and factories to create these components.
"""

from edon_ui.widgets.gfx import SocketLabel, fit_font_to_height
from edon_ui.widgets.adaptors import SocketTextAdaptor, SocketWidgetAdaptor
from edon_ui.widgets.editors import FocusSelectLineEdit, ExpandLineEdit
from edon_ui.widgets.factories import (
    SOCKET_WIDGET_COMPONENT_FACTORIES,
    SocketWidgetComponentFactory,
    create_integer_socket_component,
    create_float_socket_component,
    create_string_socket_component,
    create_large_string_socket_component,
)

__all__ = [
    "SocketLabel",
    "fit_font_to_height",
    "SocketTextAdaptor",
    "SocketWidgetAdaptor",
    "FocusSelectLineEdit",
    "ExpandLineEdit",
    "SOCKET_WIDGET_COMPONENT_FACTORIES",
    "SocketWidgetComponentFactory",
    "create_integer_socket_component",
    "create_float_socket_component",
    "create_string_socket_component",
    "create_large_string_socket_component",
]


---
src/edon_ui/widgets/adaptors.py
---
"""Adaptor classes to make Qt items conform to SocketComponent interface.

This module provides adaptor classes that wrap Qt graphics items to make them conform
to the SocketComponent protocol. These adaptors handle the layout and positioning
requirements of socket components within a node's socket row, while also enabling the use
of standard QWidgets through proxy wrapping for better integration with the QGraphicsView
event system.

These adaptors ensure consistent behavior and layout for different types of socket
components while maintaining the flexibility of the underlying Qt graphics system.
"""

from loguru import logger
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsProxyWidget,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from edon_ui import theme
from edon_ui.widgets.gfx import SocketLabel

from edon_ui.base import BaseEdonGraphicsObject


class SocketTextAdaptor(BaseEdonGraphicsObject):
    """Adapts a SocketLabel to be used as a SocketComponent with margins."""

    def __init__(
        self,
        text_item: SocketLabel,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsObject | None = None,
    ):
        super().__init__(parent)
        self._text_item = text_item
        self._horizontal_margin = horizontal_margin

        if self._text_item.parentItem() != self:
            self._text_item.setParentItem(self)
        self._text_item.setPos(self._horizontal_margin, 0)

    def get_required_component_width(self) -> float:
        return self._text_item.boundingRect().width() + (self._horizontal_margin * 2)

    def get_required_component_height(self) -> float:
        return self._text_item.boundingRect().height()

    def boundingRect(self) -> QRectF:
        width = self.get_required_component_width()
        height = self.get_required_component_height()
        return QRectF(0, 0, width, height)

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        self._text_item.set_text_alignment(alignment)


class SocketWidgetAdaptor(BaseEdonGraphicsObject):
    """Adapts a QWidget to be used as a SocketComponent via QGraphicsProxyWidget."""

    def __init__(
        self,
        widget: QWidget,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(None)
        self._widget = widget
        self._horizontal_margin = horizontal_margin

        self.proxy = QGraphicsProxyWidget(self)
        self.proxy.setWidget(widget)
        self.proxy.setPos(horizontal_margin, 0)
        self.proxy.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        widget.proxy = self.proxy
        widget.setParent(parent)

    def get_required_component_width(self) -> float:
        width = self._widget.width() or self._widget.sizeHint().width()
        return width + (self._horizontal_margin * 2)

    def get_required_component_height(self) -> float:
        return self._widget.height() or self._widget.sizeHint().height()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.get_required_component_width(), self.get_required_component_height())


---
src/edon_ui/widgets/editors.py
---
"""Specialized QWidget subclasses for editing socket values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, TypeAlias, runtime_checkable

from loguru import logger
from PySide6.QtCore import QRect, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QCloseEvent,
    QColor,
    QFocusEvent,
    QFontMetrics,
    QHoverEvent,
    QIcon,
    QKeyEvent,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPalette,
    QPen,
    QResizeEvent,
    QShowEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsRectItem,
    QGraphicsScene,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyleOptionFrame,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from edon_ui import theme
from edon_ui.icon_engine import FontIcon

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsProxyWidget


@runtime_checkable
class ValueWidget(Protocol):
    def get_value(self) -> Any: ...
    def set_value(self, value: Any) -> None: ...


ValueWidgetType: TypeAlias = ValueWidget | QWidget


class ProxyAttributeMixin:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._proxy: QGraphicsProxyWidget | None = None

    @property
    def proxy(self) -> QGraphicsProxyWidget:
        assert self._proxy is not None, "CORRUPTION: `QGraphicsProxyWidget` should always be set"
        return self._proxy

    @proxy.setter
    def proxy(self, proxy: QGraphicsProxyWidget) -> None:
        self._proxy = proxy


class CustomDialogWidget(QWidget):
    """A frameless, always-on-top, movable dialog-like widget with a title bar and close button."""

    accepted = Signal()
    rejected = Signal()

    TITLE_BAR_HEIGHT = 24  # Define a constant for title bar height

    def __init__(
        self,
        parent: QWidget,
        scene: QGraphicsScene | None,
        title: str = "Dialog",
        content: ValueWidgetType | None = None,
    ):
        super().__init__(parent)
        self.scene = scene
        self._overlay_item: QGraphicsRectItem | None = None

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # Stylesheet might need adjustment if title_bar height is fixed programmatically
        self.setStyleSheet("""
            CustomDialogWidget {
                background: #232323;
                border-radius: 10px;
                border: 1px solid #444;
            }
            QFrame#titleBar {
                background: #232323;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                /* Height is now set programmatically */
            }
            QLabel#titleLabel {
                color: #e0e0e0;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#closeButton {
                background: transparent;
                color: #c0c0c0;
                border: none;
                font-size: 12px;
                font-weight: bold;
                border-radius: 6px; /* From user's previous changes */
                 /* Fixed size for buttons makes positioning easier */
                min-width: 12px; max-width: 12px;
                min-height: 12px; max-height: 12px;
            }
            QPushButton#closeButton:hover {
                background: #555;
                color: #fff;
            }
            QFrame#contentFrame {
                background: #232323;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        # --- Title Bar (Manual Layout) ---
        self.title_bar = QFrame(self)  # Store as instance member
        self.title_bar.setObjectName("titleBar")
        self.title_bar.setFixedHeight(self.TITLE_BAR_HEIGHT)

        self.title_label = QLabel(title, self.title_bar)  # Parented to title_bar
        self.title_label.setObjectName("titleLabel")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Crucial for centering text

        self.close_button = QPushButton("✕", self.title_bar)  # Parented to title_bar
        self.close_button.setObjectName("closeButton")
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(self._on_reject)

        # --- Content Area (Layout Managed) ---
        self.content_frame = QFrame(self)  # Store as instance member
        self.content_frame.setObjectName("contentFrame")

        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        if content:
            content_layout.addWidget(content)
        else:
            placeholder = QLabel("No content provided.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: #888;")
            content_layout.addWidget(placeholder)

        self.accept_button = QPushButton("Save", self)
        self.accept_button.setObjectName("acceptButton")
        self.accept_button.setToolTip("Save")
        self.accept_button.clicked.connect(self._on_accept)

        # --- Main Layout for CustomDialogWidget ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(0)

        main_layout.addWidget(self.title_bar)
        main_layout.addWidget(self.content_frame, 1)
        main_layout.addWidget(self.accept_button)  # Accept button row at the bottom

    def _position_title_bar_elements(self):
        tb_width = self.title_bar.width()
        tb_height = self.title_bar.height()

        self.close_button.move(tb_width - self.close_button.width(), 0)
        self.title_label.move(
            int((tb_width / 2) - (self.title_label.width() / 2)),
            int((tb_height / 2) - (self.title_label.height() / 2)),
        )

    def _dynamic_resize(self) -> None:
        parent_widget = self.parentWidget()
        if parent_widget:
            set_dynamic_width_and_height(
                self, parent_widget.rect(), width_ratio=0.7, height_ratio=0.8
            )
        else:
            desktop = QApplication.primaryScreen().geometry()
            set_dynamic_width_and_height(self, desktop, width_ratio=0.7, height_ratio=0.8)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._dynamic_resize()
        super().resizeEvent(event)

    def accept(self) -> None:
        if self.content:
            self.content.accept()
        super().accept()

    def reject(self) -> None:
        if self.content:
            self.content.reject()
        super().reject()

    def _on_accept(self) -> None:
        self.accepted.emit()
        self.close()

    def _on_reject(self) -> None:
        self.rejected.emit()
        self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.rejected.emit()
            event.accept()
        elif (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.accepted.emit()
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event: QShowEvent) -> None:
        # Initial positioning after widgets are shown and have sizes.
        QTimer.singleShot(0, self._position_title_bar_elements)

        # Overlay and scene interaction logic (ensure scene is not None)
        if self.scene:
            self._overlay_item = QGraphicsRectItem(self.scene.sceneRect())
            self._overlay_item.setBrush(QColor(0, 0, 0, 128))
            self._overlay_item.setZValue(9999)
            self.scene.addItem(self._overlay_item)

            view = self.scene.views()[0] if self.scene.views() else None
            if view:
                view.setInteractive(False)
                setattr(view, "_interaction_enabled", False)
        else:
            logger.warning("CustomDialogWidget.show(): Scene not available for overlay.")

        self._dynamic_resize()
        super().showEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.scene and self._overlay_item:
            self.scene.removeItem(self._overlay_item)
            self._overlay_item = None

            view = self.scene.views()[0] if self.scene.views() else None
            if view:
                view.setInteractive(True)
                setattr(view, "_interaction_enabled", True)

        super().closeEvent(event)

    # _drag_active = False  # Class attribute for drag state
    # _drag_pos = QPoint()  # Class attribute for drag position

    # def mousePressEvent(self, event: QMouseEvent) -> None:
    #     # Check if the press is on the title bar area (first child, or check y-coordinate)
    #     if event.button() == Qt.MouseButton.LeftButton and event.position().y() < self.TITLE_BAR_HEIGHT:
    #         CustomDialogWidget._drag_active = True
    #         CustomDialogWidget._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    #         event.accept()
    #     else:
    #         # If not dragging, pass event to super or content
    #         super().mousePressEvent(event)

    # def mouseMoveEvent(self, event: QMouseEvent) -> None:
    #     if CustomDialogWidget._drag_active and (event.buttons() & Qt.MouseButton.LeftButton):
    #         self.move(event.globalPosition().toPoint() - CustomDialogWidget._drag_pos)
    #         event.accept()
    #     else:
    #         super().mouseMoveEvent(event)

    # def mouseReleaseEvent(self, event: QMouseEvent) -> None:
    #     CustomDialogWidget._drag_active = False
    #     super().mouseReleaseEvent(event)


class FocusSelectLineEdit(ProxyAttributeMixin, QLineEdit):
    """A QLineEdit subclass designed for use within a QGraphicsScene via SocketWidgetAdaptor.

    It selects all text on focusInEvent. On Return, Enter, or Escape key release,
    it explicitly clears the focus from the hosting QGraphicsProxyWidget.
    The `SocketWidgetAdaptor` is responsible for setting the `proxy` attribute on this widget.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._elide_text = True
        self._focus_in = False
        self._ellipsis_place = Qt.TextElideMode.ElideRight

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Escape):
            if self.proxy:
                # The logger message was slightly off, self.proxy is the proxy itself
                logger.debug(f"FocusSelectLineEdit: Clearing focus on its proxy {self.proxy}")
                self.proxy.clearFocus()  # This should trigger our focusOutEvent
            else:
                # This case should ideally not happen if adapted correctly
                logger.warning(
                    f"FocusSelectLineEdit ({self.objectName()}): Proxy not set. Calling self.clearFocus() as fallback."
                )
                self.clearFocus()

            event.accept()
            return
        super().keyReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Include a validation icon to the left of the line edit and elide text
        if requested.
        """
        if self._elide_text and not self._focus_in:
            painter = QPainter(self)
            option = QStyleOptionFrame()
            self.initStyleOption(option)

            self.style().drawPrimitive(
                QStyle.PrimitiveElement.PE_PanelLineEdit, option, painter, self
            )

            text_rect = self.style().subElementRect(
                QStyle.SubElement.SE_LineEditContents, option, self
            )
            text_rect.adjust(4, 0, -4, 0)  # Adjust for padding/icon space

            fm = QFontMetrics(self.font())
            elided_text_str = fm.elidedText(self.text(), self._ellipsis_place, text_rect.width())

            if hasattr(theme, "INPUT_TEXT_COLOR"):
                painter.setPen(QColor(theme.INPUT_TEXT_COLOR))
            else:
                painter.setPen(self.palette().color(QPalette.ColorRole.Text))

            current_alignment = self.alignment()
            painter.drawText(text_rect, int(current_alignment), elided_text_str)
            return

        super().paintEvent(event)

    def focusInEvent(self, event: QFocusEvent) -> None:
        self._focus_in = True
        QTimer.singleShot(0, self.selectAll)
        super().focusInEvent(event)

    def focusOutEvent(self, event: QFocusEvent) -> None:
        self._focus_in = False
        super().focusOutEvent(event)


class ValueTextEdit(QTextEdit):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.title = "Edit Text"

        # Apply theme-consistent styling
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.INPUT_WIDGET_BACKGROUND_COLOR.name()};
                color: {theme.INPUT_WIDGET_TEXT_COLOR.name()};
                border: 1px solid {theme.INPUT_WIDGET_BORDER_COLOR.name()};
                border-radius: {theme.INPUT_WIDGET_BORDER_RADIUS}px;
                padding: {theme.INPUT_WIDGET_PADDING}px;
                selection-background-color: {theme.ACCENT_SECONDARY.name()};
                selection-color: {theme.COLOR_TEXT_LIGHT.name()};
            }}
            QTextEdit:focus {{
                border-color: {theme.NODE_BORDER_SELECTED.name()};
            }}
        """)

    def get_value(self) -> Any:
        return self.toPlainText()

    def set_value(self, value: Any) -> None:
        self.setPlainText(value)


# XXX: Don't know how to handle this, but it's not really needed for now.
class HighlightEventMixin:
    def event(self, event: QHoverEvent) -> bool:
        """Handle hover events to update visual state."""
        if event.type() in (QHoverEvent.Type.HoverEnter, QHoverEvent.Type.HoverLeave):
            if hasattr(self, "proxy"):
                self.proxy.update()
                return True
        return super().event(event)

    def paint_highlight(self, painter: QPainter, rect: QRect) -> None:
        # Create a semi-transparent highlight with rounded corners
        highlight_path = QPainterPath()
        radius = (
            theme.INPUT_WIDGET_BORDER_RADIUS if hasattr(theme, "INPUT_WIDGET_BORDER_RADIUS") else 4
        )

        r = QRect(rect.x() - 2, rect.y() - 2, rect.width() + 4, rect.height() + 4)
        highlight_path.addRoundedRect(r, radius, radius)

        highlight_color = QColor(theme.INPUT_WIDGET_BACKGROUND_COLOR).lighter(80)
        highlight_color.setAlpha(40)  # Subtle transparency

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillPath(highlight_path, highlight_color)
        # Draw border
        border_color = QColor(theme.ACCENT_SECONDARY)
        border_color.setAlpha(120)  # Slightly transparent for subtlety
        pen = QPen(border_color)
        pen.setWidthF(1.2)  # Thin border, adjust as needed
        painter.setPen(pen)
        painter.drawPath(highlight_path)
        painter.restore()


class ExpandLineEdit(ProxyAttributeMixin, QLineEdit):
    """A QLineEdit that displays an icon and opens a larger editor on click."""

    def __init__(
        self,
        widget_factory: type[ValueWidgetType],
        icon_name: str = "fa5s.expand",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        self.setObjectName("ExpandLineEdit")
        self.resize(128, 24)
        self.setStyleSheet("""
            QLineEdit#ExpandLineEdit {
                border: none;
                padding-left: 4px;
                padding-right: 4px;
                padding-top: 0px;
                padding-bottom: 0px;
                margin-left: 4px;
            }
        """)
        self.setReadOnly(True)

        self.widget_factory = widget_factory
        self.value: Any = None
        self._ellipsis_place = Qt.TextElideMode.ElideRight
        self.icon = FontIcon(icon_name, QColor(theme.ICON_COLOR))

    def _open_text_dialog(self) -> None:
        # Get the top-level window (the main window)
        window = self.window()  # self.window() is the top-level window containing this widget
        if not window:
            logger.error("ExpandLineEdit: Could not determine parent window.")
            return

        # Try to get the scene from the window, or from this widget's direct parent if part of a GFX view
        scene = getattr(window, "scene", None)
        if (
            not scene
            and isinstance(self.parentWidget(), QWidget)
            and hasattr(self.parentWidget(), "scene")
        ):
            scene = self.parentWidget().scene()

        if not scene:
            # If scene is still not found, it's a problem for the current overlay logic.
            # Log a warning. The dialog might still show, but overlay will be missing.
            logger.warning(
                "ExpandLineEdit: Could not determine QGraphicsScene for CustomDialogWidget's overlay."
            )
            # scene will be None, CustomDialogWidget's show() method should handle this.

        logger.debug(
            f"ExpandLineEdit: Opening text dialog. Parent window: {window}, Scene: {scene}"
        )

        widget = self.widget_factory()
        widget.set_value(self.value)

        dialog = CustomDialogWidget(
            parent=window,
            scene=scene,  # scene can be None
            title=widget.title,
            content=widget,
        )

        def _clear_focus():
            logger.trace(f"ExpandLineEdit: Clearing focus on its proxy {self.proxy}")
            self.clearFocus()
            self.proxy.clearFocus()

        def _update_value():
            self.value = widget.get_value()
            logger.trace(f"ExpandLineEdit: Clearing focus on its proxy {self.proxy}")
            _clear_focus()

        dialog.accepted.connect(_update_value)
        dialog.rejected.connect(_clear_focus)
        dialog.show()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Opens a dialog for editing text when the line edit is clicked."""
        # Allow QLineEdit to first process the mouse press (e.g., for focus)

        if event.button() == Qt.MouseButton.LeftButton:
            # Check if the click was on the icon area, or allow anywhere for now
            # For simplicity, any left click will open the dialog for now.
            # More precise hit testing on the icon can be added if needed.
            if self.rect().contains(event.pos()):  # Ensure click is within the widget
                QTimer.singleShot(0, self._open_text_dialog)

                event.accept()
                return
        # If not handled (e.g. right click), ensure superclass can still process if it wants
        # (though super() was already called, this is more for structure if we didn't call it above)
        # No, super() was already called, so this is not needed: super().mousePressEvent(event)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = self.geometry()
        option = QStyleOptionFrame()
        self.initStyleOption(option)

        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_PanelLineEdit, option, painter)

        icon_rect = QRect((rect.width() / 2) - 2, rect.y(), rect.width(), rect.height())
        text_rect = self.style().subElementRect(
            QStyle.SubElement.SE_LineEditContents, option, self
        )

        if self.value:
            icon_width = self.height() // 1.3
            text_rect.adjust(0, 0, -int(icon_width), 0)

            fm = QFontMetrics(self.font())
            elided_text_str = fm.elidedText(
                self.value.replace("\n", " "), self._ellipsis_place, text_rect.width()
            )

            start_color = QColor(theme.INPUT_TEXT_DISABLED_COLOR)
            end_color = QColor(theme.INPUT_TEXT_DISABLED_COLOR).lighter(130)

            gradient = QLinearGradient(
                text_rect.left(), text_rect.center().y(), text_rect.right(), text_rect.center().y()
            )

            gradient.setColorAt(1, start_color)
            gradient.setColorAt(0, end_color)

            painter.setPen(QPen(QBrush(gradient), 0))
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                elided_text_str,
            )

        if self.icon:
            self.icon.paint(painter, icon_rect, mode=QIcon.Mode.Normal, state=QIcon.State.On)


def set_dynamic_width_and_height(
    widget, screen_geometry: QRect, width_ratio: float = 0.5, height_ratio: float = 0.5
):
    """
    The screen and height will be updated to match the screen geometry.
    """
    screen_width = int(screen_geometry.width() * width_ratio)
    screen_height = int(screen_geometry.height() * height_ratio)
    widget.resize(screen_width, screen_height)

    # Make the dialog window appear in the center of the screen
    x = int(screen_geometry.center().x() - widget.width() / 2)
    y = int(screen_geometry.center().y() - widget.height() / 2)
    widget.move(x, y)


---
src/edon_ui/widgets/factories.py
---
"""Factory functions for creating socket editor components."""

from typing import Protocol, Any

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator, QIntValidator

from edon.socket import SocketType
from edon_ui.widgets.adaptors import SocketWidgetAdaptor
from edon_ui.widgets.editors import ExpandLineEdit, FocusSelectLineEdit, ValueTextEdit


class SocketWidgetComponentFactoryProtocol(Protocol):
    def __call__(
        self,
        initial_value: Any,
        node_id: str,
        socket_name: str,
    ) -> SocketWidgetAdaptor: ...


type SocketWidgetComponentFactory = SocketWidgetComponentFactoryProtocol


def create_integer_socket_component(
    initial_value: int,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
    """
    Creates a QLineEdit configured for integer input and wraps it in a SocketWidgetAdaptor.
    """
    logger.debug(
        f"Creating integer socket component for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)  # Parent will be set by SocketWidgetAdaptor via proxy
    line_edit.setObjectName(f"le_int_{node_id}_{socket_name}")
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    line_edit.setValidator(QIntValidator(-2147483648, 2147483647, line_edit))
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value))

    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


def create_float_socket_component(
    initial_value: float,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
    """
    Creates a QLineEdit configured for float input and wraps it in a SocketWidgetAdaptor.
    """
    logger.debug(
        f"Creating float socket component for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)
    line_edit.setObjectName(f"le_float_{node_id}_{socket_name}")
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
    validator = QDoubleValidator(line_edit)
    validator.setNotation(QDoubleValidator.Notation.StandardNotation)
    line_edit.setValidator(validator)
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value))

    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


def create_string_socket_component(
    initial_value: str,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
    logger.debug(
        f"Creating string socket component (QLineEdit) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)
    line_edit.setObjectName(f"le_str_{node_id}_{socket_name}")
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(str(initial_value if initial_value is not None else ""))

    # FontMetrics calculation for logging purposes, can be removed if not essential here
    fm = line_edit.fontMetrics()
    text_width_pixels = fm.horizontalAdvance(line_edit.text())
    logger.debug(
        f"  String QLineEdit '{line_edit.objectName()}': text='{line_edit.text()}', calculated fontMetrics text_width_pixels={text_width_pixels}"
    )

    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


def create_large_string_socket_component(
    initial_value: str,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
    logger.debug(
        f"Creating large string socket component (IconPopupLineEdit) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = ExpandLineEdit(parent=None, widget_factory=ValueTextEdit)
    line_edit.setObjectName(f"text_edit_{node_id}_{socket_name}")
    line_edit.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    line_edit.setText(initial_value)

    # XXX: Popup logic needs it own way of ending on top.
    # We have weird parenting logic here. Ensure that this is not the end result required.
    # adaptor = SocketWidgetAdaptor(widget=line_edit, parent=controller.graphics_scene.views()[0])
    adaptor = SocketWidgetAdaptor(widget=line_edit)
    return adaptor


# XXX: This is just shit
def create_any(
    initial_value: str,
    node_id: str,
    socket_name: str,
) -> SocketWidgetAdaptor:
    logger.debug(
        f"Creating large string socket component (IconPopupLineEdit) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    line_edit = FocusSelectLineEdit(None)

    adaptor = SocketWidgetAdaptor(line_edit)
    return adaptor


# Registry for socket widget component factories
SOCKET_WIDGET_COMPONENT_FACTORIES: dict[SocketType, SocketWidgetComponentFactory] = {
    SocketType.ANY: create_any,
    SocketType.INTEGER: create_integer_socket_component,
    SocketType.FLOAT: create_float_socket_component,
    SocketType.STRING: create_string_socket_component,
    SocketType.LARGE_STRING: create_large_string_socket_component,
}


---
src/edon_ui/widgets/gfx.py
---
"""Graphical primitives for socket UI rendering."""

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QFont,
    QFontMetricsF,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsTextItem,
)

from edon_ui import theme


def fit_font_to_height(font: QFont, target_height: float, min_size: int = 1, max_size: int = 30) -> QFont:
    """Finds the largest font size that fits within target_height."""
    test_font = QFont(font)
    for size in range(max_size, min_size - 1, -1):
        test_font.setPointSize(size)
        metrics = QFontMetricsF(test_font)
        if metrics.height() <= target_height:
            return test_font
    test_font.setPointSize(min_size)
    return test_font


def _font_height_diff(font: QFont, target_height: float) -> float:
    metrics = QFontMetricsF(font)
    return target_height - metrics.height()


class SocketLabel(QGraphicsTextItem):
    def __init__(self, text: str, target_layout_height: float, parent: QGraphicsItem | None = None):
        super().__init__(text, parent)
        logger.trace(f"SocketLabel created with text: '{text}'")

        font = self.font()
        font.setPointSize(getattr(theme, "FONT_SOCKET_LABEL_DEFAULT_SIZE", 10))

        diff = _font_height_diff(font, target_layout_height)
        if diff < 0:
            font = fit_font_to_height(font, target_layout_height)
            diff = _font_height_diff(font, target_layout_height)

        self.setFont(font)
        self.document().setDocumentMargin(diff / 2 if diff > 0 else 0)
        self.setDefaultTextColor(getattr(theme, "SOCKET_LABEL_TEXT_COLOR", theme.INPUT_TEXT_COLOR))

    def get_required_component_width(self) -> float:
        """Returns the width as determined by setTextWidth or natural text width."""
        return self.boundingRect().width()

    def get_required_component_height(self) -> float:
        """Returns the actual bounding height of the text item, including document margins."""
        return self.boundingRect().height()

    def set_text_alignment(self, alignment: Qt.AlignmentFlag):
        doc = self.document()
        option = doc.defaultTextOption()
        option.setAlignment(alignment)
        doc.setDefaultTextOption(option)


---
src/edon_ui/widgets/node_spawner.py
---
"""
Node Spawning Panel widget for Edon UI.

This widget provides a searchable list of available node types
that can be instantiated onto the graph canvas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QLineEdit, QListWidget, QVBoxLayout, QWidget
from thefuzz import fuzz

if TYPE_CHECKING:
    from edon_ui.graph.controller import WorkspaceController


class NodeSpawningPanel(QWidget):
    """
    A panel that allows users to search for and select nodes to spawn onto the canvas.
    """

    def __init__(
        self,
        controller: WorkspaceController,
        spawn_position: QPointF,
        parent: QWidget | None = None,
    ):
        """
        Initialize the NodeSpawningPanel.

        Args:
            graph_controller: The main graph controller instance.
            spawn_position: The scene position where the new node should be spawned.
            parent: The parent widget.
        """
        super().__init__(parent)

        self.controller = controller
        self.spawn_position = spawn_position

        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        # A basic size, can be refined later
        self.setMinimumSize(300, 400)

        # --- UI Elements ---
        self.search_bar = QLineEdit(self)
        self.search_bar.setPlaceholderText("Search nodes...")

        self.node_list_widget = QListWidget(self)
        self.node_list_widget.setAlternatingRowColors(True)

        self._all_node_type_names: list[str] = []

        # --- Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.search_bar)
        main_layout.addWidget(self.node_list_widget)
        self.setLayout(main_layout)

        # --- Connections and Initial State ---
        self._load_all_node_types()
        self._filter_node_list()  # Initial population and selection

        self.search_bar.textChanged.connect(self._filter_node_list)
        self.node_list_widget.itemClicked.connect(self._spawn_selected_node)

    def _load_all_node_types(self) -> None:
        """
        Loads all available node type names from the graph_controller's node_registry.
        """
        self._all_node_type_names = []
        if self.controller and self.controller.node_registry:
            self._all_node_type_names = sorted(list(self.controller.node_registry.keys()))

    def _filter_node_list(self) -> None:
        """
        Filters the node_list_widget based on the search_bar's text
        using fuzzy matching and selects the first item.
        """
        search_text = self.search_bar.text().lower()
        self.node_list_widget.clear()

        FUZZY_MATCH_THRESHOLD = 60  # Minimum score to be considered a match

        if not search_text:
            # If search text is empty, show all nodes
            for name in self._all_node_type_names:
                self.node_list_widget.addItem(name)
        else:
            scored_names: list[tuple[str, int]] = []
            for name in self._all_node_type_names:
                # Using partial_ratio for better matching of substrings or partial names
                score = fuzz.partial_ratio(search_text, name.lower())
                if score >= FUZZY_MATCH_THRESHOLD:
                    scored_names.append((name, score))

            # Sort by score in descending order
            scored_names.sort(key=lambda x: x[1], reverse=True)

            for name, _ in scored_names:
                self.node_list_widget.addItem(name)

        if self.node_list_widget.count() > 0:
            self.node_list_widget.setCurrentRow(0)

    def _spawn_selected_node(self) -> None:
        """
        Spawns the currently selected node in the list and closes the panel.
        """
        current_item = self.node_list_widget.currentItem()
        if not current_item:
            if self.node_list_widget.count() > 0:
                current_item = self.node_list_widget.item(0)
            else:
                return

        if not current_item:
            return

        node_type_hint = current_item.text()

        # Spawn the node. The controller will place its top-left at self.spawn_position initially.
        # self.spawn_position is the mouse click, intended as the center.
        node_item = self.controller.handle_ui_node_creation_request(
            node_type_hint=node_type_hint, scene_pos=self.spawn_position
        )

        # Now that we have the actual NodeItem, get its dimensions
        rect = node_item.boundingRect()
        offset = QPointF(rect.width() / 2.0, rect.height() / 2.4)

        # Calculate the correct top-left position for the node
        # so its center aligns with self.spawn_position.
        final_node_pos = self.spawn_position - offset
        node_item.setPos(final_node_pos)

        logger.info(
            f"Spawning node of type '{node_type_hint}'. Target center: {self.spawn_position}. Final top-left: {final_node_pos}"
        )
        self.close()

    def show_panel(self, position: QPointF) -> None:
        """
        Shows the panel at the given global position.
        The input position should be global screen coordinates.
        The panel will be centered horizontally on this position,
        and its vertical position adjusted so the search bar is centered on this position.
        """
        # Ensure the panel has its layout calculated to get correct dimensions
        self.adjustSize()  # Process layout and get initial size

        panel_width = self.width()
        search_bar_height = self.search_bar.height()

        # Calculate top-left position for the panel
        new_x = position.x() - panel_width / 2
        new_y = position.y() - search_bar_height / 2

        self.move(QPointF(new_x, new_y).toPoint())
        self.show()
        self.activateWindow()
        self.search_bar.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        list_widget = self.node_list_widget
        current_row = list_widget.currentRow()
        count = list_widget.count()

        if key == Qt.Key.Key_Escape:
            self.close()
            event.accept()
        elif key == Qt.Key.Key_Down:
            if count > 0:
                next_row = (current_row + 1) % count
                list_widget.setCurrentRow(next_row)
            event.accept()
        elif key == Qt.Key.Key_Up:
            if count > 0:
                prev_row = (current_row - 1 + count) % count
                list_widget.setCurrentRow(prev_row)
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if list_widget.currentItem():
                self._spawn_selected_node()
            event.accept()
        else:
            # Allow search bar to process other key presses
            # self.search_bar.keyPressEvent(event) # This can cause double processing
            super().keyPressEvent(event)


---
src/edon_ui/graph/__init__.py
---
"""Graphics System for Edon UI.

This package implements a comprehensive graphics system.
"""

from edon_ui.graph.controller import WorkspaceController

__all__ = [
    "WorkspaceController",
]


---
src/edon_ui/graph/context.py
---
"""
Manages the context stack for navigating through nested graphs in the UI.

This module provides classes to track the current graph, scene, and registry
when entering and exiting subgraphs, ensuring the UI state remains synchronized
with the logical graph hierarchy.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from edon.graph import EntityGraph, EntitySubGraphNode
    from edon_ui.graph.registry import WorkspaceUIDataRegistry
    from edon_ui.views.scene import GraphicsScene


class ContextState:
    """
    A simple data class to hold the state for a single navigation level.
    """

    def __init__(
        self,
        graph: EntityGraph,
        scene: GraphicsScene,
        registry: WorkspaceUIDataRegistry,
        origin_subgraph_node: EntitySubGraphNode | None = None,
    ):
        self.graph = graph
        self.scene = scene
        self.registry = registry
        # The SubGraphNode instance that was entered to reach this level.
        # None for the root graph.
        self.origin_subgraph_node = origin_subgraph_node


class WorkspaceContextStack:
    """
    Manages the state of navigation through a hierarchy of graphs (e.g., entering subgraphs).

    It maintains stacks for the logical EntityGraph, the corresponding UI GraphicsScene,
    and the GraphUIDataRegistry for that scene.
    """

    def __init__(self) -> None:
        self._stacks: list[ContextState] = []

    def initialize(self, context_state: ContextState) -> None:
        """
        Initializes the navigation state with the root graph.
        """
        # During a initialize we have to reset the whole stack, the assumption
        # is that you only do init from the root graph.
        self._stacks = [context_state]

    @property
    def current(self) -> ContextState:
        """
        Gets the state of the current (topmost) navigation level.
        Returns None if the stack is empty (e.g., before initialization).
        """
        stack = self._stacks[-1]
        assert stack is not None, (
            f"CORRUPTION: {self.__class__.__name__} level should never be None"
        )

        return stack

    @property
    def parent(self) -> ContextState | None:
        if self.is_at_root():
            return None

        return self._stacks[-2]

    @property
    def depth(self) -> int:
        return len(self._stacks)

    def push(self, ContextState) -> None:
        """
        Pushes a new navigation level (e.g., after entering a subgraph).
        """
        self._stacks.append(ContextState)

    def pop(self) -> ContextState | None:
        """
        Pops the current navigation level, returning to the previous one.
        Returns the state of the level that was popped, or None if at root or uninitialized.
        """
        assert self._stacks, "CORRUPTION: Cannot pop from an empty navigation stack"
        if self.is_at_root():
            return None

        return self._stacks.pop()

    def context_state_for_scene(self, scene_instance: GraphicsScene) -> ContextState:
        """
        Retrieves the ContextState associated with a specific GraphicsScene instance.
        """
        context_state: ContextState | None = None
        for ctx in self._stacks:
            if ctx.scene is scene_instance:
                context_state = ctx

        assert context_state is not None, (
            "CORRUPTION: Scene {scene_instance} is not part of any stack."
        )
        return context_state

    def is_at_root(self) -> bool:
        """Checks if the current navigation level is the root."""
        return len(self._stacks) == 1


---
src/edon_ui/graph/controller.py
---
"""
Manages the synchronization and interaction between the logical entity graph
and its visual representation in the UI.

This controller acts as the central point for handling user input related
to graph manipulation (node creation, deletion, linking) and reflecting
changes from the entity graph model onto the graphics scene. It also
manages the context when navigating into and out of subgraphs.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import TYPE_CHECKING, Type, cast

from loguru import logger
from PySide6.QtCore import QPointF, Slot

from edon.graph import EntityGraph, EntitySubGraphNode
from edon.node import EntityNode
from edon.types import EdgeKey, SocketAddress, SocketRole
from edon_ui import theme
from edon_ui.graph.context import ContextState, WorkspaceContextStack
from edon_ui.graph.registry import WorkspaceUIDataRegistry
from edon_ui.items.edge import EdgeItem
from edon_ui.items.factory import create_node_item
from edon_ui.items.node import NodeItem
from edon_ui.views.scene import EdgeDragContext, GraphicsScene
from edon_ui.views.viewer import GraphicsView

if TYPE_CHECKING:
    pass

type NodeRegistryMap = MutableMapping[str, Type[EntityNode]]


class WorkspaceController:
    """
    Controls the synchronization between the entity graph (edon.graph.EntityGraph)
    and the UI representation (edon_ui.graphics_scene.GraphicsScene).

    It acts as the intermediary, translating UI actions into model operations
    and reflecting model changes in the UI. It can be initialized with an
    optional `node_type_registry` to map node type string identifiers to their
    respective `EntityNode` classes, facilitating node creation from type hints.
    """

    def __init__(
        self,
        node_type_registry: Mapping[str, Type[EntityNode]] | None = None,
    ):
        """
        Initialize controller, creating its own GraphicsView and initial root graph context.
        The GraphContextStack is initialized with this root context.
        Graph content can be loaded subsequently via load_graph().
        """
        self._view = GraphicsView(self)

        self.context_stack = WorkspaceContextStack()
        self.node_registry: NodeRegistryMap = dict(node_type_registry or {})

        init_scene = self._create_wired_scene()
        self._view.setScene(init_scene)
        assert self.view.scene() is init_scene, (
            "CORRUPTION: GraphicsView's scene does not match the initial_scene created by WorkspaceController."
        )

        self.context_stack.initialize(
            ContextState(
                graph=EntityGraph(),
                scene=init_scene,
                registry=WorkspaceUIDataRegistry(),
            )
        )

    def _create_wired_scene(self) -> GraphicsScene:
        scene = GraphicsScene()
        scene.edge_drag_initiation_request.connect(self.handle_ui_init_edge_drag_action)
        scene.edge_link_request.connect(self.handle_ui_edge_link_request)
        scene.node_redraw_ui_request.connect(self.handle_ui_node_redraw_request)

        return scene

    @property
    def view(self) -> GraphicsView:
        return self._view

    @property
    def scene(self) -> GraphicsScene:
        return self.context_stack.current.scene

    @property
    def graph(self) -> EntityGraph:
        return self.context_stack.current.graph

    @property
    def registry(self) -> WorkspaceUIDataRegistry:
        return self.context_stack.current.registry

    def _clear_all_ui(self) -> None:
        """
        Removes all UI elements and clears the registry.

        This method ensures a clean slate by removing all visual elements
        and resetting the UI data registry. Order matters: edges must be
        removed before nodes due to dependencies.
        """
        # XXX: We should look into scene reset that is prettier than this.
        # I don't think we have to go through everything and delete it.
        # But if we do we should delegate it to scene either way.
        edge_items_to_remove = list(self.registry.edges)
        for edge_item in edge_items_to_remove:
            self.scene.remove_edge(edge_item)

        node_items_to_remove = list(self.registry.nodes)
        for node_item in node_items_to_remove:
            self.scene.remove_node(node_item)

        # Reset the registry to clean state
        self.context_stack.current.registry = WorkspaceUIDataRegistry()

        logger.debug(
            f"Cleared {len(edge_items_to_remove)} edges and {len(node_items_to_remove)} nodes"
        )

    def load_graph(self, entity_graph: EntityGraph) -> None:
        """
        Replaces the current graph and rebuilds the entire UI representation.

        This method provides a clean slate approach: it clears all existing UI elements,
        creates a fresh empty entity graph, and populates both the graph and UI
        from the given graph data.
        """
        logger.info(f"Loading new graph with {len(entity_graph.nodes)} nodes")

        assert self.context_stack.is_at_root(), (
            "load_graph can only be called when at the root navigation level."
        )

        state = ContextState(
            graph=EntityGraph(),
            scene=self._create_wired_scene(),
            registry=WorkspaceUIDataRegistry(),
        )
        self.context_stack.initialize(state)

        # Create Scene state from the given entity_graph
        self._populate_scene_from_graph_data(entity_graph)

        self.view.setScene(state.scene)
        self.view.set_interactive_scene(bool(state.registry.nodes))

        logger.info("Graph loading completed successfully for the current context")

    def _register_node_internal(
        self, entity_node: EntityNode, scene_position: QPointF
    ) -> NodeItem:
        """
        Creates a NodeItem for an EntityNode that is ALREADY in self.graph.

        This method only handles UI registration and assumes the entity_node
        is already properly added to the entity graph. It never modifies
        the entity graph itself, maintaining clear separation of concerns.
        """
        logger.debug(f"Registering UI for existing node '{entity_node.id}' at {scene_position}")

        node_item = create_node_item(
            entity_node,
        )

        # XXX: we do this if we are populating a scene from existing graph
        if entity_node.id not in self.graph.nodes:
            self.graph.add_node(entity_node)

        self.registry.register_node_with_sockets(node_item)

        # Finally update graphics layers, scene/view behavior, if this is the first node added this will
        # enable interactivity etc.
        self.scene.add_node(node_item)

        if not self.view.is_interactive:
            self.view.set_interactive_scene(True)

        return node_item

    def _register_edge_internal(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Creates an EdgeItem for the given EdgeKey, adds it to the scene,
        and updates internal controller maps.
        Assumes the link exists in self.graph and source/target node UIs are registered.
        """
        logger.debug(f"GraphController: Registering UI for edge {edge_key}")

        source_socket_addr = edge_key.source
        target_socket_addr = edge_key.target

        edge_item = EdgeItem(
            self.registry.socket_item_for_address(source_socket_addr),
            self.registry.socket_item_for_address(target_socket_addr),
        )

        self.scene.add_edge(edge_item)
        self.registry.register_edge_item(edge_key, edge_item)

        return edge_item

    def _populate_scene_from_graph_data(self, source_graph: EntityGraph | None = None) -> None:
        """
        Populates the GraphicsScene with NodeItems and EdgeItems based on the
        given source graph (or current EntityGraph if None).
        """
        graph_to_read = source_graph if source_graph is not None else self.graph

        logger.debug(
            f"GraphController: Populating UI scene from {'external' if source_graph else 'current'} entity graph data."
        )

        # XXX: Temporary solution, we will track layout info in the serialization.
        default_x, default_y = 50.0, 50.0
        spacing_x = getattr(theme, "NODE_MIN_WIDTH", 150.0) + 50.0
        spacing_y = getattr(theme, "NODE_MIN_HEIGHT", 100.0) + 50.0
        nodes_per_row = 5

        # Add all nodes using existing request method
        for i, (_, entity_node) in enumerate(graph_to_read.nodes.items()):
            pos_x = default_x + (i % nodes_per_row) * spacing_x
            pos_y = default_y + (i // nodes_per_row) * spacing_y

            # We are working with existing entity_nodes, request_add_node will create the
            # entity node, we simply want to register it.
            self._register_node_internal(entity_node, scene_position=QPointF(pos_x, pos_y))

        # Add all edges using existing request method
        for edge_key in graph_to_read.edges:
            self._register_edge_internal(edge_key)

    def enter_subgraph(self, subgraph_node_item: NodeItem) -> None:
        """
        Switches the controller's context to the internal graph of the given SubGraphNodeItem.
        """
        logger.trace(f"Entering subgraph from depth {self.context_stack.depth}")

        # The graph and UI registry should be in sync; if node_item exists, entity_node must exist.
        entity_id = subgraph_node_item.entity_id
        entity_node = self.graph.get_node(entity_id)

        assert entity_node is not None, (
            f"CRITICAL: EntityNode with ID {entity_id} not found in graph despite UI item existing."
        )
        assert isinstance(entity_node, EntitySubGraphNode), (
            f"CORRUPTION: Node {entity_node.id} provided to enter_subgraph "
            f"is not a SubGraphNode. Actual type: {type(entity_node)}."
        )

        subgraph_entity = cast(EntitySubGraphNode, entity_node)
        context_state = ContextState(
            graph=subgraph_entity.internal_graph,
            scene=self._create_wired_scene(),
            registry=WorkspaceUIDataRegistry(),
            origin_subgraph_node=subgraph_entity,
        )
        self.context_stack.push(context_state)

        self._populate_scene_from_graph_data(source_graph=context_state.graph)

        # It's always important to update the interaction on the scene.
        self.view.setScene(self.scene)
        self.view.set_interactive_scene(bool(self.context_stack.current.registry.nodes))

        logger.debug(
            f"Successfully entered subgraph: {subgraph_entity.id}. Current depth: {self.context_stack.depth}"
        )

    def exit_subgraph(self) -> None:
        """
        Exits the current subgraph view and returns to the parent graph view.
        """
        logger.trace(f"Leaving subgraph from depth {self.context_stack.depth}")

        assert not self.context_stack.is_at_root(), (
            "Cannot exit subgraph: Already at the root graph."
        )

        self.context_stack.pop()
        logger.info(
            f"Exited subgraph. Current depth: {self.context_stack.depth}. "
            f"Now viewing graph: {self.context_stack.current.graph if self.context_stack.current.graph else 'Root'}"
        )

        # Update the view to display the parent scene
        self.view.setScene(self.scene)
        self.view.set_interactive_scene(bool(self.context_stack.current.graph.nodes))

    @Slot(str, QPointF)
    def handle_ui_node_creation_request(self, node_type_hint: str, scene_pos: QPointF) -> NodeItem:
        """
        Slot to handle the new_node_requested_at_scene_pos signal from the UI (e.g., GraphicsView).
        It determines the entity node class to create based on the hint and then
        calls the main request_add_node method.
        """
        logger.debug(
            f"GraphController: Received handle_ui_node_creation_request for type '{node_type_hint}' at {scene_pos}"
        )

        node_class_to_create = self.node_registry.get(node_type_hint)
        assert node_class_to_create is not None, (
            f"CORRUPTION: Node type hint '{node_type_hint}' not found in registry. Cannot create node."
        )

        return self.request_add_node(
            node_entity_class=node_class_to_create,
            mouse_position=scene_pos,
        )

    @Slot(SocketAddress, SocketAddress)
    def handle_ui_edge_link_request(
        self, source_socket_addr: SocketAddress, target_socket_addr: SocketAddress
    ) -> None:
        """
        Handles a UI request to link two sockets identified by their SocketAddress.

        Attempts to add the new edge if it doesn't already exist.
        """
        logger.debug(
            f"GraphController: Received handle_ui_edge_link_attempt from "
            f"source {source_socket_addr} to target {target_socket_addr}"
        )

        edge_key = EdgeKey(source_socket_addr, target_socket_addr)

        # If the target socket already has an edge, we remove it, input nodes can only have one edge
        # and we decided on behavior that the new edge will replace the old one.
        # This uses the updated find_edge_items_at_socket which calls the registry.
        edge_items = self.registry.edge_items_for_socket(target_socket_addr)
        if edge_items:
            logger.debug(
                f"Target socket {target_socket_addr.node_id}::{target_socket_addr.name} already has a link, removing existing."
            )
            self.handle_ui_edge_deletion_request(list(edge_items))

        # If we are in a subgraph we need to check whether we have to update the SubGraphNode in the parent with
        # new context.
        if not self.context_stack.is_at_root():
            # Import here to avoid circular dependencies at module level if SubgraphPromoterNode
            # itself might eventually use controller functionalities, or keep at top if safe.
            from edon.nodes.utility import SubgraphPromoterNode

            source_node_entity = self.graph.get_node(source_socket_addr.node_id)
            target_node_entity = self.graph.get_node(target_socket_addr.node_id)

            is_source_node_promoter = isinstance(source_node_entity, SubgraphPromoterNode)
            is_target_node_promoter = isinstance(target_node_entity, SubgraphPromoterNode)
            if any([is_source_node_promoter, is_target_node_promoter]):
                if is_source_node_promoter:
                    internal_socket_addr = target_socket_addr
                else:
                    internal_socket_addr = source_socket_addr

                logger.debug(
                    f"Dispatching to request_expose_subgraph_socket: "
                    f"internal: {internal_socket_addr}"
                )
                self.request_expose_socket_from_subgraph(internal_socket_addr=internal_socket_addr)

        self.request_add_edge(edge_key)

    def handle_ui_node_deletion_request(self, entity_node_ids: Sequence[str]) -> None:
        """Processes a UI request to delete one or more specified nodes."""
        logger.debug(
            f"GraphController: Received handle_ui_node_deletion_request for IDs: {entity_node_ids}"
        )

        for node_id in entity_node_ids:
            self.request_remove_node(node_id)

    def handle_ui_edge_deletion_request(self, edge_items: Sequence[EdgeItem]) -> None:
        """Processes a UI request to delete one or more specified edges."""
        logger.debug(
            f"GraphController: Received handle_ui_edge_deletion_request for {len(edge_items)} edge(s)."
        )

        for edge_item in edge_items:
            self.request_remove_edge(edge_item.edge_key)

    def request_add_node(
        self,
        node_entity_class: type[EntityNode],
        mouse_position: QPointF,
        **node_specific_kwargs,
    ) -> NodeItem:
        """
        Creates a new entity node or uses an existing one, adding it to both
        the entity graph and UI.

        This is the primary method for adding nodes during user interaction
        or when populating from existing graph data.
        """
        logger.debug(f"Creating new node of type '{node_entity_class}' at {mouse_position}")

        new_entity_node = node_entity_class(**node_specific_kwargs)
        node_item = self._register_node_internal(new_entity_node, mouse_position)

        return node_item

    def request_add_edge(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Link sockets in the entity graph and then register the UI edge representation.
        """
        logger.debug(f"GraphController: Requesting to create edge: {edge_key}")

        link_success, reason = self.graph.link_sockets(edge_key)
        assert link_success, (
            f"CORRUPTION: EntityGraph.link_sockets failed for {edge_key} with reason {reason}"
        )

        return self._register_edge_internal(edge_key)

    def request_remove_node(self, entity_node_id: str) -> None:
        """
        Handles a request to remove a node and its linked edges from both the
        entity graph and the UI scene.
        """
        logger.debug(f"GraphController: Requesting to remove node with ID: {entity_node_id}")

        # Unregister from UI registry; this will assert if node_id is not found.
        # It returns the node_item, and lists of socket_items and edge_items that were part of this node.
        node_item_to_remove, _removed_socket_items, removed_edge_items = (
            self.registry.unregister_node(entity_node_id)
        )

        # XXX: should  `remove_node` handle removing edges as well or is that part of business logic?
        # currently the data layer and the entity graph is handling the edge cleanup when we remove a
        # node.
        # Remove associated edges from the entity graph and the scene
        for edge_item in removed_edge_items:
            # Entity graph unlinking is based on the edge_key from the UI edge_item
            # This might attempt to unlink sockets that are already unlinked if
            # entity_graph.remove_node below also handles unlinking.
            # However, entity_graph.unlink_sockets should be idempotent or handle this.
            self.graph.unlink_sockets(edge_item.edge_key)
            self.scene.remove_edge(edge_item)

        self.graph.remove_node(entity_node_id)
        self.scene.remove_node(node_item_to_remove)

        # Finally update view behavior, if this is the first node added this will
        # enable interactivity etc.
        self.view.set_interactive_scene(bool(self.registry.nodes))

    def request_remove_edge(self, edge_key: EdgeKey) -> None:
        """
        Handles a request to remove a single edge (entity and UI).
        """
        logger.debug(f"GraphController: Requesting to remove edge: {edge_key}")

        # XXX: This should be handled by assertions in the `entity_graph`, not by upstream checks.
        # Unlink sockets in the entity graph first. Refactor necessary.
        self.graph.unlink_sockets(edge_key)

        edge_item = self.registry.unregister_edge(edge_key)
        self.scene.remove_edge(edge_item)

        logger.debug(f"UI EdgeItem for {edge_key} removed from graphics scene and UI registry.")

    def request_expose_socket_from_subgraph(self, internal_socket_addr: SocketAddress) -> None:
        """
        Handles a request to expose an internal socket of a subgraph as a proxy
        socket on the parent SubGraphNode.

        This is typically triggered by dragging an edge from an internal node's socket
        to a special socket on a SubgraphPromoterNode within the subgraph's view.
        """
        current_stack_state = self.context_stack.current
        assert current_stack_state.origin_subgraph_node is not None, (
            "CORRUPTION: Attempting to expose subgraph socket when not editing within a subgraph context."
        )

        subgraph_node_entity = current_stack_state.origin_subgraph_node
        subgraph_node_entity.add_proxy_socket(internal_socket_addr.name, internal_socket_addr)

        parent_stack_state = self.context_stack.parent
        assert parent_stack_state is not None, (
            "CORRUPTION: Attempting to expose subgraph socket when not editing within a subgraph context."
        )

        from edon_ui.items.factory import create_socket_item

        socket_entity = subgraph_node_entity.sockets[internal_socket_addr.name]
        # We need to get the display state from the socket item that we are exposing, so the behavior
        # is maintained.
        internal_socket_item = self.registry.socket_item_for_address(internal_socket_addr)
        new_socket_item = create_socket_item(
            socket_entity, internal_socket_item.components.display_state
        )

        parent_stack_state.registry.register_socket_item_for_node(new_socket_item)

        subgraph_item = parent_stack_state.registry.node_item_for_id(subgraph_node_entity.id)
        subgraph_item.add_socket_item(new_socket_item)

    @Slot(str, GraphicsScene)
    def handle_ui_node_redraw_request(self, node_id: str, scene: GraphicsScene) -> None:
        state = self.context_stack.context_state_for_scene(scene)
        node_item = state.registry.node_item_for_id(node_id)

        for socket_item in node_item.source_sockets + node_item.target_sockets:
            edges = state.registry.edge_items_for_socket(socket_item.address)
            # Drawing should really happen at the scene level but creating a function to
            # pipe the edge items to the scene just "because" is unnecessary.
            for edge in edges:
                edge.update_path()

    @Slot(SocketAddress, QPointF, GraphicsScene)
    def handle_ui_init_edge_drag_action(
        self, clicked_socket_addr: SocketAddress, pos: QPointF, scene: GraphicsScene
    ) -> None:
        """
        Analyzes a clicked socket and prepares the data needed for the edge drag action.
        """
        socket_item = self.registry.socket_item_for_address(clicked_socket_addr)

        # Check if we need to lift an existing edge
        # This uses the updated find_edge_items_at_socket which calls the registry.
        linked_edges = list(self.registry.edge_items_for_socket(clicked_socket_addr))

        if socket_item.role == SocketRole.TARGET and linked_edges:
            # Lift existing edge - the actual source becomes the original source
            assert len(linked_edges) == 1, (
                f"CORRUPTION: Target socket {clicked_socket_addr} should have exactly one edge, "
                f"found {len(linked_edges)}: {linked_edges}."
            )

            lifted_edge = linked_edges[0]
            actual_source_socket_item = lifted_edge.source_socket_item
            actual_source_addr = actual_source_socket_item.address

            # We need to clean up the edge that we lifted, it will be replaced
            # by a temporary edge and managed as a new object.
            self.handle_ui_edge_deletion_request(linked_edges)

            is_lifted = True
            logger.debug(
                f"Lifting edge from {clicked_socket_addr}, original source: {actual_source_addr}"
            )
        else:
            actual_source_addr = clicked_socket_addr
            actual_source_socket_item = socket_item
            is_lifted = False
            logger.debug(f"Preparing new edge drag from {clicked_socket_addr}")

        valid_targets, invalid_targets = self.partition_socket_drop_targets(actual_source_addr)

        # Feed the necessary context to the scene for it to start the edge drag action
        scene.edge_drag_create_action(
            EdgeDragContext(
                source_socket_addr=actual_source_addr,
                source_socket_item=actual_source_socket_item,
                is_lifted_edge=is_lifted,
                valid_targets={
                    addr: self.registry.socket_item_for_address(addr) for addr in valid_targets
                },
                invalid_targets={
                    addr: self.registry.socket_item_for_address(addr) for addr in invalid_targets
                },
            ),
            pos,
        )

    def partition_socket_drop_targets(
        self, drag_origin_socket_addr: SocketAddress
    ) -> tuple[set[SocketAddress], set[SocketAddress]]:
        """
        Determines valid drop target sockets for an edge drag operation.

        This method delegates to EntityGraph.get_connection_targets() to maintain
        proper separation of concerns between UI coordination and business logic.
        """
        valid_targets, invalid_targets = self.graph.partition_valid_link_targets(
            drag_origin_socket_addr
        )

        logger.debug(
            f"Found {len(valid_targets)} valid drop targets for {drag_origin_socket_addr} via EntityGraph: {valid_targets}"
        )
        return valid_targets, invalid_targets

    def find_edge_items_at_socket(self, socket_addr: SocketAddress) -> set[EdgeItem]:
        """Retrieves all UI EdgeItems connected to the given socket address from the UI registry.

        Assertions in `GraphUIDataRegistry` handle cases where the socket address is not found.
        """
        return self.registry.edge_items_for_socket(socket_addr)


---
src/edon_ui/graph/layout.py
---


---
src/edon_ui/graph/registry.py
---
"""
Centralized registry for UI item mappings with assertion-based validation.

Maintains synchronized mappings between logical graph entities and their UI
representations. Enforces data integrity through aggressive validation that
crashes the application immediately upon detecting any inconsistency.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import ValuesView
from typing import TYPE_CHECKING

from loguru import logger

from edon.types import EdgeKey, SocketAddress

if TYPE_CHECKING:
    from edon_ui.items.edge import EdgeItem
    from edon_ui.items.node import NodeItem
    from edon_ui.items.socket import SocketItem


class WorkspaceUIDataRegistry:
    """
    Centralized registry for UI item mappings with assertion-based validation.

    Maintains synchronized mappings between logical graph entities and their UI
    representations. Enforces data integrity through aggressive validation that
    crashes the application immediately upon detecting any inconsistency.
    """

    def __init__(self) -> None:
        self._node_items: dict[str, NodeItem] = {}
        self._edge_items: dict[EdgeKey, EdgeItem] = {}
        self._socket_items: dict[SocketAddress, SocketItem] = {}
        self._socket_to_edge_keys: dict[SocketAddress, set[EdgeKey]] = defaultdict(set)

        # Track registration sequence for debugging corrupted states
        self._registration_order: list[str] = []

    @property
    def nodes(self) -> ValuesView[NodeItem]:
        return self._node_items.values()

    @property
    def edges(self) -> ValuesView[EdgeItem]:
        return self._edge_items.values()

    @property
    def sockets(self) -> ValuesView[SocketItem]:
        return self._socket_items.values()

    def _assert_invariants(self) -> None:
        """Validates all internal consistency rules and crashes if any are violated."""

        # Socket associations must reference registered sockets
        for socket_addr in self._socket_to_edge_keys:
            assert socket_addr in self._socket_items, (
                f"CORRUPTION: Socket {socket_addr} has edge associations but no registered SocketItem"
            )

        # Edge associations must reference registered edges
        for socket_addr, edge_keys in self._socket_to_edge_keys.items():
            for edge_key in edge_keys:
                assert edge_key in self._edge_items, (
                    f"CORRUPTION: Socket {socket_addr} references non-existent edge {edge_key}"
                )

        # Edges must be bidirectionally associated with their endpoint sockets
        for edge_key, _ in self._edge_items.items():
            source_addr = edge_key.source
            target_addr = edge_key.target

            assert edge_key in self._socket_to_edge_keys[source_addr], (
                f"CORRUPTION: Edge {edge_key} not associated with its source socket {source_addr}"
            )
            assert edge_key in self._socket_to_edge_keys[target_addr], (
                f"CORRUPTION: Edge {edge_key} not associated with its target socket {target_addr}"
            )

        # Socket parent nodes must be registered
        for socket_addr, _ in self._socket_items.items():
            assert socket_addr.node_id in self._node_items, (
                f"CORRUPTION: Socket {socket_addr} belongs to unregistered node {socket_addr.node_id}"
            )

    def register_socket_item_for_node(self, socket_item: SocketItem) -> None:
        socket_addr = socket_item.address
        assert socket_addr not in self._socket_items, (
            f"CORRUPTION: Attempting to register already-registered SocketItem '{socket_addr}'."
        )
        assert socket_addr.node_id in self._node_items, (
            f"CORRUPTION: Attempting to register SocketItem '{socket_addr}' for a "
            f"non-existent parent node '{socket_addr.node_id}'."
        )

        self._socket_items[socket_addr] = socket_item
        self._assert_invariants()

    def unregister_socket_item(self, socket_addr: SocketAddress) -> None:
        assert socket_addr in self._socket_items, (
            "CORRUPTION: Attempting to unregister non-registered `SocketAddress` {socket_addr}"
        )

        # Assert that edges connected to this socket have already been dealt with.
        assert not self._socket_to_edge_keys.get(socket_addr), (
            f"CORRUPTION: Attempting to unregister socket '{socket_addr}' which still has "
            f"edge associations: {self._socket_to_edge_keys.get(socket_addr)}. "
            "Edges must be unregistered before their endpoint sockets."
        )

        del self._socket_items[socket_addr]
        del self._socket_to_edge_keys[socket_addr]
        self._assert_invariants()

    def register_node_with_sockets(self, node_item: NodeItem) -> None:
        """Atomically registers a node and all its socket items."""
        node_id = node_item.entity_id

        # Prevent double registration which indicates logic errors
        assert node_id not in self._node_items, (
            f"CORRUPTION: Attempting to register already-registered node {node_id}"
        )

        # Collect socket items and validate they're not already registered
        all_socket_items = node_item.source_sockets + node_item.target_sockets
        socket_addresses = [item.address for item in all_socket_items if item is not None]

        for socket_addr in socket_addresses:
            assert socket_addr not in self._socket_items, (
                f"CORRUPTION: Socket {socket_addr} already registered during node registration"
            )

        # All-or-nothing registration to prevent partial corruption
        try:
            self._node_items[node_id] = node_item
            for socket_item in all_socket_items:
                if socket_item is not None:
                    self._socket_items[socket_item.address] = socket_item

            self._registration_order.append(f"NODE:{node_id}")
            logger.debug(f"Registered node {node_id} with {len(socket_addresses)} sockets")

            # Validate consistency after every state mutation
            self._assert_invariants()

        except Exception as e:
            # Any failure during registration indicates corrupted state
            logger.critical(f"FATAL: Node registration failed for {node_id}, state corrupted: {e}")
            self._dump_debug_state()
            raise RuntimeError(f"Registry corruption during node registration: {e}") from e

    def register_edge_item(self, edge_key: EdgeKey, edge_item: EdgeItem) -> None:
        """Registers an edge item with full endpoint validation."""

        # Duplicate edge registration indicates controller logic errors
        assert edge_key not in self._edge_items, f"CORRUPTION: Edge {edge_key} already registered"

        # Endpoint sockets must exist before edge creation
        assert edge_key.source in self._socket_items, (
            f"CORRUPTION: Cannot register edge {edge_key} - source socket {edge_key.source} not registered"
        )
        assert edge_key.target in self._socket_items, (
            f"CORRUPTION: Cannot register edge {edge_key} - target socket {edge_key.target} not registered"
        )

        try:
            # Atomic registration of edge and bidirectional socket associations
            self._edge_items[edge_key] = edge_item
            self._socket_to_edge_keys[edge_key.source].add(edge_key)
            self._socket_to_edge_keys[edge_key.target].add(edge_key)

            self._registration_order.append(f"EDGE:{edge_key}")
            logger.debug(f"Registered edge {edge_key}")

            # Ensure consistency after state modification
            self._assert_invariants()

        except Exception as e:
            logger.critical(
                f"FATAL: Edge registration failed for {edge_key}, state corrupted: {e}"
            )
            self._dump_debug_state()
            raise RuntimeError(f"Registry corruption during edge registration: {e}") from e

    def unregister_node(self, node_id: str) -> tuple[NodeItem, list[SocketItem], list[EdgeItem]]:
        """Removes a node and cascades to all dependent sockets and edges."""

        # Node must exist for unregistration
        assert node_id in self._node_items, (
            f"CORRUPTION: Cannot unregister non-existent node {node_id}"
        )

        node_item = self._node_items[node_id]

        # Identify all dependent items that must be removed
        node_socket_addrs = [addr for addr in self._socket_items.keys() if addr.node_id == node_id]

        # Find edges connected to any socket of this node
        edges_to_remove: set["EdgeKey"] = set()
        for socket_addr in node_socket_addrs:
            edges_to_remove.update(self._socket_to_edge_keys[socket_addr])

        try:
            # Remove in dependency order: edges → sockets → node
            removed_edges_items = []
            for edge_key_to_remove in list(
                edges_to_remove
            ):  # Iterate over a copy as unregister_edge modifies the sets
                removed_edges_items.append(self.unregister_edge(edge_key_to_remove))

            removed_sockets = []
            for socket_addr in node_socket_addrs:
                removed_sockets.append(self._unregister_socket_internal(socket_addr))

            # Remove the node itself
            del self._node_items[node_id]
            self._registration_order.append(f"UNREGISTER_NODE:{node_id}")

            # logger.debug(
            #     f"Cascade unregistered node {node_id} ({len(removed_edges)} edges, {len(removed_sockets)} sockets)"
            # )

            # Validate consistency after cascade operation
            self._assert_invariants()

            return node_item, removed_sockets, removed_edges_items

        except Exception as e:
            logger.critical(f"FATAL: Cascade unregistration failed for node {node_id}: {e}")
            self._dump_debug_state()
            raise RuntimeError(f"Registry corruption during cascade unregistration: {e}") from e

    def unregister_edge(self, edge_key: EdgeKey) -> EdgeItem:
        """
        Removes a specific edge UI item and its associations from the registry.

        This method asserts that the edge exists before attempting removal. It cleans up
        the edge's references from its connected sockets and ensures registry invariants
        are maintained.
        """
        assert edge_key in self._edge_items, (
            f"CORRUPTION: Attempting to unregister non-existent edge {edge_key}"
        )

        edge_item = self._edge_items.pop(edge_key)

        # Clean up bidirectional socket associations
        source_addr = edge_key.source
        if source_addr in self._socket_to_edge_keys:
            self._socket_to_edge_keys[source_addr].discard(edge_key)
            if not self._socket_to_edge_keys[source_addr]:  # Remove empty set
                del self._socket_to_edge_keys[source_addr]

        target_addr = edge_key.target
        if target_addr in self._socket_to_edge_keys:
            self._socket_to_edge_keys[target_addr].discard(edge_key)
            if not self._socket_to_edge_keys[target_addr]:  # Remove empty set
                del self._socket_to_edge_keys[target_addr]

        self._registration_order.append(f"UNREGISTER_EDGE:{edge_key}")
        logger.debug(f"Unregistered edge {edge_key}")

        self._assert_invariants()
        return edge_item

    def _unregister_socket_internal(self, socket_addr: SocketAddress) -> "SocketItem":
        """Removes a socket and validates no edges are still associated."""
        assert socket_addr in self._socket_items, (
            f"CORRUPTION: Socket {socket_addr} not registered"
        )
        assert not self._socket_to_edge_keys[socket_addr], (
            f"CORRUPTION: Attempting to unregister socket {socket_addr} with remaining edge associations: {self._socket_to_edge_keys[socket_addr]}"
        )

        socket_item = self._socket_items[socket_addr]
        del self._socket_items[socket_addr]
        del self._socket_to_edge_keys[socket_addr]  # Remove the empty set entry

        return socket_item

    def node_item_for_id(self, node_id: str) -> NodeItem:
        """Retrieves the node item for the given ID."""
        assert node_id in self._node_items, (
            f"CORRUPTION: Requested non-existent node {node_id}. Available: {list(self._node_items.keys())}"
        )
        return self._node_items[node_id]

    def edge_items_for_socket(self, socket_addr: SocketAddress) -> set[EdgeItem]:
        """Retrieves all edge items connected to the specified socket."""
        assert socket_addr in self._socket_items, (
            f"CORRUPTION: Requested edges for non-existent socket {socket_addr}"
        )

        edge_keys = self._socket_to_edge_keys[socket_addr]
        edge_items = set()

        for edge_key in edge_keys:
            # Every socket association must reference a valid edge
            assert edge_key in self._edge_items, (
                f"CORRUPTION: Socket {socket_addr} references non-existent edge {edge_key}"
            )
            edge_items.add(self._edge_items[edge_key])

        return edge_items

    def socket_item_for_address(self, socket_addr: SocketAddress) -> SocketItem:
        """Retrieves the socket item for the given address."""
        assert socket_addr in self._socket_items, (
            f"CORRUPTION: Requested non-existent socket {socket_addr}. Available: {list(self._socket_items.keys())}"
        )
        return self._socket_items[socket_addr]

    def _dump_debug_state(self) -> None:
        """Outputs complete registry state for post-mortem analysis."""
        logger.critical("=== REGISTRY STATE DUMP ===")
        logger.critical(f"Nodes: {len(self._node_items)} registered")
        logger.critical(f"Edges: {len(self._edge_items)} registered")
        logger.critical(f"Sockets: {len(self._socket_items)} registered")
        logger.critical(
            f"Socket-Edge associations: {len(self._socket_to_edge_keys)} sockets with edges"
        )
        logger.critical(
            f"Registration order: {self._registration_order[-10:]}"
        )  # Recent operations only

        # Identify specific corruption patterns
        orphaned_sockets = [
            addr for addr in self._socket_to_edge_keys if addr not in self._socket_items
        ]
        if orphaned_sockets:
            logger.critical(f"ORPHANED SOCKET ASSOCIATIONS: {orphaned_sockets}")


---
src/edon_ui/views/__init__.py
---
"""Graphics System for Edon UI.

This package implements a comprehensive graphics system.
"""

from edon_ui.views.scene import GraphicsScene
from edon_ui.views.viewer import GraphicsView
from edon_ui.views.window import MainWindow

__all__ = [
    "GraphicsScene",
    "GraphicsView",
    "MainWindow",
]


---
src/edon_ui/views/scene.py
---
"""
Provides the custom QGraphicsScene implementation for the node editor.

This module defines the GraphicsScene class, which manages the visual workspace
for the node graph. It handles adding and removing visual items (nodes, edges),
drawing the background and grid, managing the active area, and processing
low-level UI events related to item interaction and dragging.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt, Signal, Slot
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QStyleOptionGraphicsItem,
    QWidget,
)

from edon.graph import SocketAddress
from edon.socket import SocketRole
from edon_ui import theme
from edon_ui.items.edge import DraggingEdgeItem, EdgeItem
from edon_ui.items.node import NodeItem
from edon_ui.items.socket import SocketItem, SocketLinkItem

if TYPE_CHECKING:
    from PySide6.QtCore import QObject

    from edon_ui.views.viewer import GraphicsView


@dataclass
class EdgeDragContext:
    """
    Encapsulates the data needed to initiate an edge drag operation.

    Contains the resolved source socket information after handling edge lifting
    logic, along with precomputed valid and invalid drop targets for efficient
    visual feedback during the drag operation.
    """

    source_socket_addr: SocketAddress
    source_socket_item: SocketItem
    is_lifted_edge: bool
    valid_targets: Mapping[SocketAddress, SocketItem]
    invalid_targets: Mapping[SocketAddress, SocketItem]


@dataclass
class DragContext:
    """
    Manages the state of an active edge drag operation within the graphics scene.

    Consolidates drag-related state that was previously scattered across multiple
    instance variables, providing a single point of truth for the current drag
    operation's visual and logical state.
    """

    temp_edge: DraggingEdgeItem
    source_socket_item: SocketItem
    valid_targets: Mapping[SocketAddress, SocketItem]
    invalid_targets: Mapping[SocketAddress, SocketItem]
    highlighted_socket: SocketItem | None = None

    def apply_target_socket_highlight(self, item: SocketItem | None) -> None:
        # Here we check whether we had a highlight, or if we are already highlighting
        # the target item. If not, we need to reset.
        if self.highlighted_socket and not self.highlighted_socket == item:
            self.highlighted_socket.set_drop_target_highlight(False)
            self.highlighted_socket = None

        # We check whether the target item is in the `DragContext` valid targets and highlight
        # the object if it is.
        if item and item.address in self.valid_targets:
            item.set_drop_target_highlight(True)
            self.highlighted_socket = item

    def apply_target_socket_visuals(self) -> None:
        """Applies visual feedback by marking invalid drop target sockets."""
        if not self.invalid_targets:
            return

        for socket_item in self.invalid_targets.values():
            if socket_item and socket_item.link_item:
                socket_item.link_item.set_not_valid_drop_target(True)

    def cleanup_visuals(self) -> None:
        """Resets all visual feedback states applied during the drag operation."""
        if self.highlighted_socket:
            self.highlighted_socket.set_drop_target_highlight(False)

        for socket_item in self.invalid_targets.values():
            if socket_item and socket_item.link_item:
                socket_item.link_item.set_not_valid_drop_target(False)


class EmptySceneTextItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        # Define text and styles for each line
        self.line1_text = "There's nothing here!"
        self.line1_font_family = "Arial"
        self.line1_font_size_px = 18
        self.line1_color = QColor("#b4b4b4")
        self.line1_italic = False

        self.line2_text = "(ctrl+space to start adding nodes)"
        self.line2_font_family = "Arial"
        self.line2_font_size_px = 14
        self.line2_color = QColor("#909090")
        self.line2_italic = True

        self.line_spacing_px = 4  # Additional spacing between lines in pixels

        # Prepare fonts (can also be done in paint, but here is fine too)
        self._font1 = QFont(self.line1_font_family)
        self._font1.setPixelSize(self.line1_font_size_px)  # Use pixelSize for consistency
        self._font1.setItalic(self.line1_italic)

        self._font2 = QFont(self.line2_font_family)
        self._font2.setPixelSize(self.line2_font_size_px)
        self._font2.setItalic(self.line2_italic)

        # Cache bounding rect calculation
        self._cached_bounding_rect = self._calculate_bounding_rect()

    def boundingRect(self) -> QRectF:
        return self._cached_bounding_rect

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        overall_br = self.boundingRect()  # This is already centered around (0,0)

        # --- Draw Line 1 ---
        painter.setFont(self._font1)
        painter.setPen(self.line1_color)

        # Calculate rect for line 1, centered horizontally within overall_br
        # and positioned at the top part of overall_br
        line1_metrics_rect = self._get_line_metrics(self.line1_text, self._font1)

        # Top-left y for line1 text block, relative to item's (0,0) origin
        y1_pos = overall_br.top()

        # Create a drawing rectangle for line1 that spans the full width of the item
        # Qt.AlignCenter will then center the text within this drawing_rect1.
        drawing_rect1 = QRectF(
            overall_br.left(), y1_pos, overall_br.width(), line1_metrics_rect.height()
        )
        painter.drawText(drawing_rect1, Qt.AlignmentFlag.AlignCenter, self.line1_text)

        # --- Draw Line 2 ---
        painter.setFont(self._font2)
        painter.setPen(self.line2_color)

        line2_metrics_rect = self._get_line_metrics(self.line2_text, self._font2)

        # Top-left y for line2 text block, relative to item's (0,0) origin
        # Positioned after line1 and spacing
        y2_pos = y1_pos + line1_metrics_rect.height() + self.line_spacing_px

        drawing_rect2 = QRectF(
            overall_br.left(), y2_pos, overall_br.width(), line2_metrics_rect.height()
        )
        painter.drawText(drawing_rect2, Qt.AlignmentFlag.AlignCenter, self.line2_text)

    def _get_line_metrics(self, text, font):
        fm = QFontMetricsF(font)
        # boundingRect(text) gives a tight rect around the text.
        # Alternatively, height() gives ascent+descent, width(text) gives advance width.
        return fm.boundingRect(text)  # QRectF

    def _calculate_bounding_rect(self) -> QRectF:
        rect1 = self._get_line_metrics(self.line1_text, self._font1)
        rect2 = self._get_line_metrics(self.line2_text, self._font2)

        max_width = max(rect1.width(), rect2.width())
        total_height = rect1.height() + self.line_spacing_px + rect2.height()

        # We want the item's origin (0,0) to be its visual center for easy scene placement
        return QRectF(-max_width / 2, -total_height / 2, max_width, total_height)


class GraphicsScene(QGraphicsScene):
    """A custom QGraphicsScene subclass designed for a node-based editor interface.

    This scene manages the visual workspace where nodes can be placed and manipulated.
    It provides:
        - Empty state handling with helper text
        - A defined active area with visual boundaries
        - Dynamic scene resizing based on node positions
        - Node and Edge Tracking
        - Visual grid lines for alignment
        - Custom background and styling

    The scene automatically adjusts its boundaries as nodes are added, moved, or
    removed to maintain an appropriate workspace size. It also provides visual
    feedback when empty to guide users on how to begin using the editor.
    """

    # Node Signals
    node_redraw_ui_request = Signal(str, object)

    # Edge Signals
    edge_drag_initiation_request = Signal(SocketAddress, QPointF, object)
    edge_link_request = Signal(SocketAddress, SocketAddress, object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self._drag_context: DragContext | None = None

        self.active_area_size = 2000  # Initial size, can be smaller if preferred
        self.setSceneRect(
            -self.active_area_size / 2,
            -self.active_area_size / 2,
            self.active_area_size,
            self.active_area_size,
        )
        self.setBackgroundBrush(QBrush(theme.SCENE_BACKGROUND))

        # Active area - initialized without specific rect, will be set by _update_scene_appearance
        self.active_area = QGraphicsRectItem()
        self.active_area.setBrush(QBrush(theme.SCENE_ACTIVE_AREA_BACKGROUND))
        self.active_area.setPen(QPen(theme.SCENE_ACTIVE_AREA_BORDER, 1))
        self.active_area.setZValue(-100)  # Ensure it's behind all other items

        self.empty_scene_text = EmptySceneTextItem()
        self.empty_scene_text.setVisible(False)
        super().addItem(self.empty_scene_text)

        self.selectionChanged.connect(self._handle_selection_changed)

    @property
    def _view(self) -> GraphicsView:
        views = self.views()
        assert len(views) == 1, (
            "CORRUPTION: There should be exactly one view for each scene, instead got {len(views)}"
        )

        return cast(GraphicsView, views[0])

    def clear(self) -> None:
        super().clear()
        self.empty_scene_text = EmptySceneTextItem()
        self.empty_scene_text.setVisible(False)
        super().addItem(self.empty_scene_text)

    def add_node(self, node: NodeItem):
        # A node needs to be able to redraw itself when e.g. a socket is updated, or a widget
        # is hidden.
        # XXX: This might actually remove the need for hte _update_edges_for_node, as that
        # should be chained called either way.
        # what do we need to do:
        #   - When we add/remove sockets we need to removed edges if it has connection.
        #   - we then need to create/delete any widgets that has been changed on the item
        #   - then we need to update the position of any edges that are still connected.
        # node.node_redraw_signal.connect(self._update_redraw_node_item)
        super().addItem(node)

        node._on_socket_row_layout_changed()
        self._update_active_area_rect()

    def remove_node(self, node: NodeItem):
        super().removeItem(node)

    def add_edge(self, edge: EdgeItem):
        """Adds a visual EdgeItem to the scene.

        The logical linking and state updates on SocketItems are handled by the GraphController.
        """
        socket_item: SocketItem = edge.target_socket_item
        socket_item.transition_to(True)

        super().addItem(edge)

    def remove_edge(self, edge: EdgeItem):
        """Removes a visual EdgeItem from the scene.

        The logical unlinking and state updates on SocketItems are handled by the GraphController.
        """
        socket_item: SocketItem = edge.target_socket_item
        socket_item.transition_to(False)

        super().removeItem(edge)

    def is_dragging_edge(self) -> bool:
        return self._drag_context is not None

    def edge_drag_create_action(self, drag_context: EdgeDragContext, pos: QPointF):
        """
        Initiates an edge drag operation from the specified socket.

        Delegates the edge lifting and validation logic to the controller,
        then sets up the visual drag state based on the returned information.
        """
        temp_edge = DraggingEdgeItem(drag_context.source_socket_item, pos)
        super().addItem(temp_edge)

        # Create the drag context and update the visuals on potential target sockets.
        self._drag_context = DragContext(
            temp_edge,
            drag_context.source_socket_item,
            drag_context.valid_targets,
            drag_context.invalid_targets,
        )
        self._drag_context.apply_target_socket_visuals()

        logger.debug(
            f"Started {'lifted' if drag_context.is_lifted_edge else 'new'} edge drag from {drag_context.source_socket_addr}"
        )

    def edge_drag_action(self, current_scene_pos: QPointF):
        """Updates the temporary edge position and manages socket highlighting during drag."""
        if not self._drag_context:
            return

        # Update temp edge position
        self._drag_context.temp_edge.update_target_position(current_scene_pos)

        # Handle socket highlighting
        target_socket_item = self._get_socket_at_pos(current_scene_pos)
        self._drag_context.apply_target_socket_highlight(target_socket_item)

    def edge_drop_action(self, event_scene_pos: QPointF):
        """
        Completes the edge drag operation by attempting to create a connection.

        Handles role swapping for reverse connections and ensures all visual
        state is properly cleaned up regardless of connection success.
        """
        if not self._drag_context:
            return

        target_socket_item = self._get_socket_at_pos(event_scene_pos)
        if target_socket_item and target_socket_item.address in self._drag_context.valid_targets:
            source_addr = self._drag_context.source_socket_item.address
            target_addr = target_socket_item.address

            # Handle role swapping for reverse connections
            if self._drag_context.source_socket_item.role == SocketRole.TARGET:
                source_addr, target_addr = target_addr, source_addr

            self.edge_link_request.emit(source_addr, target_addr, self)

        # Cleanup everything
        super().removeItem(self._drag_context.temp_edge)
        self._drag_context.cleanup_visuals()
        self._drag_context = None

    def _handle_selection_changed(self):
        # XXX: We should keep an eye on this function as it could potentially be recursed and cause a crash/lock.
        # If that happens we need to look into temporarily disconnecting the signal and reconnecting it.
        current_selected_items = self.selectedItems()
        nodes_are_present_in_selection = any(
            isinstance(item, NodeItem) for item in current_selected_items
        )

        if nodes_are_present_in_selection:
            # If any node is selected, iterate through a copy of the selected items and deselect any EdgeItem.
            # We iterate a copy because setSelected(False) will modify the list returned by selectedItems() live.
            # This might not be necessary if we are careful with the logic of the edge item selection.
            for item in list(current_selected_items):
                if isinstance(item, EdgeItem):
                    item.setSelected(False)

    def _calculate_node_bounds(self, nodes: Iterable[NodeItem], padding: float) -> QRectF:
        """Calculate the bounding rectangle for a list of nodes with padding."""
        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")

        for node in nodes:
            pos = node.pos()
            rect = node.boundingRect()
            min_x = min(min_x, pos.x())
            min_y = min(min_y, pos.y())
            max_x = max(max_x, pos.x() + rect.width())
            max_y = max(max_y, pos.y() + rect.height())

        return QRectF(
            min_x - padding,
            min_y - padding,
            (max_x + padding) - (min_x - padding),
            (max_y + padding) - (min_y - padding),
        )

    def _expand_bounds_only(self, current_rect: QRectF, new_bounds: QRectF) -> QRectF:
        """Expand current bounds to include new bounds, but never shrink."""
        final_left = min(current_rect.left(), new_bounds.left())
        final_top = min(current_rect.top(), new_bounds.top())
        final_right = max(current_rect.right(), new_bounds.right())
        final_bottom = max(current_rect.bottom(), new_bounds.bottom())

        return QRectF(final_left, final_top, final_right - final_left, final_bottom - final_top)

    def _update_active_area_rect(self):
        """
        Updates the active area rectangle based on node positions.

        If nodes are selected by the user, it expands the current active area to
        include these selected nodes. If no nodes are selected, it recalculates
        the active area based on all nodes (e.g., for initial setup or after
        a full recalculation request).
        """
        node_items = [item for item in self.items() if isinstance(item, NodeItem)]
        assert node_items, (
            "CORRUPTION: Update active area should only happen if we have nodes in the scene."
        )

        padding = 0
        current_active_rect = self.active_area.rect()

        selected_nodes = [item for item in self.selectedItems() if isinstance(item, NodeItem)]
        nodes_to_consider = selected_nodes if selected_nodes else node_items

        bounds = self._calculate_node_bounds(nodes_to_consider, padding)

        if selected_nodes:
            final_bounds = self._expand_bounds_only(current_active_rect, bounds)
        else:
            # No selection: use bounds calculated from all nodes (initial or full recalc)
            final_bounds = bounds

        width = max(final_bounds.width(), 400.0)
        height = max(final_bounds.height(), 400.0)

        self.active_area.setRect(final_bounds.x(), final_bounds.y(), width, height)
        logger.trace(f"Active area updated to: {self.active_area.rect()}")

    def set_active(self, active: bool) -> None:
        """
        Updates the scene display based on whether nodes are present.
        """
        if active:
            self.empty_scene_text.setVisible(False)
            if not self.active_area.scene() == self:
                super().addItem(self.active_area)

            self._update_active_area_rect()
        else:
            if self.active_area.scene() == self:
                super().removeItem(self.active_area)
            self.empty_scene_text.setVisible(True)

    def _get_socket_at_pos(self, scene_pos: QPointF) -> SocketItem | None:
        items_at_pos = self.items(scene_pos)
        for item in items_at_pos:
            if isinstance(item, SocketLinkItem):
                return item._socket_item
        return None


---
src/edon_ui/views/viewer.py
---
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from loguru import logger
from PySide6.QtCore import QEvent, Qt, Slot
from PySide6.QtGui import QInputEvent, QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QApplication, QGraphicsProxyWidget, QGraphicsView, QMainWindow

from edon_ui.context_menu import AppContextMenu
from edon_ui.views.scene import GraphicsScene
from edon_ui.views.window import MainWindow

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsItem, QMainWindow, QGraphicsScene

    from edon.graph import EntityGraph
    from edon_ui.commands.key_processor import KeyProcessor
    from edon_ui.graph.controller import WorkspaceController


@dataclass
class EditorContext:
    view: GraphicsView
    scene: GraphicsScene
    window: QMainWindow
    controller: WorkspaceController
    selected_items: list[QGraphicsItem]
    event: QInputEvent | None = None
    params: dict[str, Any] = field(default_factory=dict)


class GraphicsView(QGraphicsView):
    RIGHT_CLICK_MOVE_THRESHOLD = 5

    def __init__(self, controller: WorkspaceController, parent=None):
        super().__init__(parent)
        self.key_processor: KeyProcessor | None = None
        self._controller = controller

        # Rendering and transformation
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        # Scrollbars and drag mode
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # Panning and right-click state
        self._pan_active = False
        self._last_pan_pos = None
        self._right_click_pos = None
        self._right_click_moved = False

        # Zoom and interaction
        self._zoom_factor = 1.1
        self._interaction_enabled = True

    @property
    def is_interactive(self) -> bool:
        return self._interaction_enabled

    def set_interactive_scene(self, active: bool) -> None:
        current_scene = cast(GraphicsScene, self.scene())

        self.setInteractive(active)
        self._interaction_enabled = active

        if active:
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.resetTransform()
            self.centerOn(current_scene.empty_scene_text)

        current_scene.set_active(active)

    def _request_scene_rect_adjustment(self):
        """Helper method to get visible scene rect and request adjustment from the scene.

        This method calculates what portion of the scene is currently visible in the viewport
        and then directly adjusts the scene's boundaries.
        """
        current_scene = self.scene()
        if not current_scene:
            return

        visible_rect_in_view_coords = self.viewport().rect()
        visible_polygon_in_scene_coords = self.mapToScene(visible_rect_in_view_coords)
        visible_rect_in_scene_coords = visible_polygon_in_scene_coords.boundingRect()

        current_s_rect = current_scene.sceneRect()

        # Define padding in scene units. This ensures the sceneRect grows a bit beyond
        # what's immediately visible, giving some buffer for panning.
        # This padding logic is now part of the view's responsibility.
        padding_w = visible_rect_in_scene_coords.width() * 0.5
        padding_h = visible_rect_in_scene_coords.height() * 0.5
        min_padding = 200.0
        padding_w = max(min_padding, padding_w)
        padding_h = max(min_padding, padding_h)
        padded_visible_rect = visible_rect_in_scene_coords.adjusted(
            -padding_w, -padding_h, padding_w, padding_h
        )

        # Unite the current sceneRect with the padded visible rect to ensure the scene boundaries
        # encompass both the existing scene area and the newly visible area.
        new_scene_rect = current_s_rect.united(padded_visible_rect)

        # Only update the sceneRect if it has actually changed to avoid unnecessary redraws.
        if new_scene_rect != current_s_rect:
            current_scene.setSceneRect(new_scene_rect)

    def provide_context(self, event: QInputEvent | None = None) -> EditorContext:
        scene = cast(GraphicsScene, self.scene())
        window = cast(QMainWindow, self.window())
        return EditorContext(
            view=self,
            scene=scene,
            window=window,
            controller=self._controller,
            selected_items=scene.selectedItems(),
            event=event,
            params={},
        )

    def wheelEvent(self, event: QWheelEvent):
        if not self.isInteractive() or not self._interaction_enabled:
            event.ignore()
            return
        zoom_in = event.angleDelta().y() > 0
        zoom_factor_val = self._zoom_factor if zoom_in else (1 / self._zoom_factor)
        self.scale(zoom_factor_val, zoom_factor_val)
        self._request_scene_rect_adjustment()

    def _route_key_event(self, event: QKeyEvent) -> None:
        # We have no use for the auto repeat keys and will be ignoring those events in the key
        # processor, how we use this is up for debate.
        if event.isAutoRepeat():
            return False

        event_type_str = "KeyPress" if event.type() == QEvent.Type.KeyPress else "KeyRelease"
        scene_focus_item = self.scene().focusItem() if self.scene() else None

        logger.trace(
            f"GV.{event_type_str}: key={event.key()}, text='{event.text()}'. SceneFocus: {scene_focus_item}"
        )

        # Event routing logic:
        # If the scene's focus item is a QGraphicsProxyWidget (such as a socket or embedded widget),
        # we delegate the key event directly to the base QGraphicsView implementation and return.
        # This ensures that any interactive proxy widget (e.g., custom sockets, embedded editors)
        # receives key events as expected, supporting their own input handling.
        #
        # For all other cases (i.e., when the focus is not on a proxy widget), we also delegate
        # the event to the base implementation, which will route it to the appropriate QGraphicsItem
        # or handle it at the view level. This fallback ensures standard Qt event propagation.
        #
        # In both cases, after delegating to the base implementation, we return to prevent further
        # processing.
        if isinstance(scene_focus_item, QGraphicsProxyWidget):
            logger.debug(
                f"GV.{event_type_str}: Scene-focused proxy widget ({scene_focus_item}) processing."
            )
            if event.type() == QEvent.Type.KeyPress:
                super().keyPressEvent(event)
            else:
                super().keyReleaseEvent(event)
            return
        else:
            logger.trace(
                f"GV.{event_type_str}: No focused proxy widget. General GView/GItem super().{event_type_str.lower()}."
            )
            if event.type() == QEvent.Type.KeyPress:
                super().keyPressEvent(event)
            else:
                super().keyReleaseEvent(event)

        if event.isAccepted():
            logger.trace(
                f"GV.{event_type_str}: Event accepted by GView/GItem/Proxy. Key: {event.key()}, text: '{event.text()}'"
            )
            return

        # If a key processor is set, attempt to handle the event as a command sequence.
        # The key processor is responsible for interpreting key events that are not handled
        # by proxy widgets or standard Qt item/view logic, enabling custom keyboard-driven
        # commands or shortcuts within the editor.
        if self.key_processor:
            logger.debug(
                f"GV.{event_type_str}: Attempting key_processor for key: {event.key()}, text: '{event.text()}'"
            )
            if self.key_processor._process_event_for_command_sequence(event, self):
                logger.debug(
                    f"GV.{event_type_str}: Event accepted by key_processor: {event.key()}, text: '{event.text()}'"
                )
                event.accept()
            else:
                logger.trace(
                    f"GV.{event_type_str}: Event not accepted by key_processor: {event.key()}, text: '{event.text()}'"
                )
        else:
            logger.trace(f"GV.{event_type_str}: No key_processor.")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        self._route_key_event(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        self._route_key_event(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        scene_item_under_mouse = self.itemAt(event.pos())
        logger.trace(
            f"GV.mousePress: btn={event.button()}, pos={event.pos()}. ItemUnderMouse: {scene_item_under_mouse}. "
            f"AppFocus: {QApplication.focusWidget()}, SceneFocus: {self.scene().focusItem() if self.scene() else None}"
        )

        # XXX: This should also be a command.
        main_window = cast(MainWindow, self.window())
        if (
            event.button() == Qt.MouseButton.LeftButton
            and main_window
            and hasattr(main_window, "is_position_on_resize_edge")
            and main_window.is_position_on_resize_edge(event.globalPosition())
        ):
            logger.trace("  Mouse press on window resize edge.")
            super().mousePressEvent(event)
            if event.isAccepted():
                return

        # XXX: This function should be a command, panning should not be limited to middle mouse button.
        # we also need to look into track pad support.
        if event.button() == Qt.MouseButton.MiddleButton:
            if not self.isInteractive() and not self._interaction_enabled:
                logger.trace("  Middle mouse: Interaction disabled, ignoring.")
                event.ignore()
                return
            logger.trace("  Middle mouse: Activating pan.")
            self._pan_active = True
            self._last_pan_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # XXX: Same as with panning, moving the window should possibly be a command.
        # as long as we provide the correct context this should work.
        elif event.button() == Qt.MouseButton.RightButton:
            logger.trace("Right mouse: Initiating context menu/move sequence.")
            self._right_click_pos = event.globalPosition().toPoint()
            self._right_click_moved = False
            event.accept()
            return

        if not self._interaction_enabled:
            logger.trace("  Interaction disabled, ignoring further mouse press processing.")
            event.ignore()
            return

        logger.trace("GV.mousePress: Passing to super() for item interaction / rubber band.")
        super().mousePressEvent(event)
        logger.trace(
            f"  GV.mousePress: After super(), event.accepted={event.isAccepted()}, AppFocus: {QApplication.focusWidget()}, SceneFocus: {self.scene().focusItem() if self.scene() else None}"
        )

        if not event.isAccepted():
            if self.key_processor and self.key_processor._process_event_for_command_sequence(
                event, self
            ):
                logger.debug("  GV.mousePress: Event accepted by key_processor.")
                event.accept()
            else:
                logger.trace("  GV.mousePress: Event not accepted by key_processor.")
        else:
            logger.trace("  GV.mousePress: Event already accepted before key_processor check.")

    def mouseReleaseEvent(self, event: QMouseEvent):
        logger.trace(f"GV.mouseRelease: btn={event.button()}, pos={event.pos()}")

        if event.button() == Qt.MouseButton.MiddleButton:
            if self._pan_active:
                logger.trace("  Middle mouse release: Deactivating pan.")
                self._pan_active = False
                self._last_pan_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                event.accept()
                return
        elif event.button() == Qt.MouseButton.RightButton:
            if self._right_click_pos and not self._right_click_moved:
                logger.debug("  Right mouse release (no drag): Showing context menu.")
                menu = AppContextMenu(
                    cast(QMainWindow, self.window()),
                    event.globalPos(),
                    self,
                )
                menu.exec(event.globalPos())
            else:
                logger.trace("  Right mouse release (dragged or no initial pos): Resetting state.")
            self._right_click_pos = None
            self._right_click_moved = False
            event.accept()
            return

        if not self._interaction_enabled:
            logger.trace("  Interaction disabled, ignoring further mouse release processing.")
            event.ignore()
            return

        logger.trace("  GV.mouseRelease: Passing to super() for item processing.")
        super().mouseReleaseEvent(event)
        logger.trace(f"  GV.mouseRelease: After super(), event.accepted={event.isAccepted()}")

        if not event.isAccepted():
            if self.key_processor and self.key_processor._process_event_for_command_sequence(
                event, self
            ):
                logger.debug("  GV.mouseRelease: Event accepted by key_processor.")
                event.accept()
            else:
                logger.trace("  GV.mouseRelease: Event not accepted by key_processor.")
        else:
            logger.trace("  GV.mouseRelease: Event already accepted before key_processor check.")

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._pan_active and self._last_pan_pos:
            current_pos = event.position().toPoint()
            delta = current_pos - self._last_pan_pos

            self._last_pan_pos = current_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            self._request_scene_rect_adjustment()
            event.accept()
            return

        if self._right_click_pos and event.buttons() & Qt.MouseButton.RightButton:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self._right_click_pos
            if (
                abs(delta.x()) > self.RIGHT_CLICK_MOVE_THRESHOLD
                or abs(delta.y()) > self.RIGHT_CLICK_MOVE_THRESHOLD
            ) and not self._right_click_moved:
                self._right_click_moved = True
                if self.window() and self.window().windowHandle():
                    self.window().windowHandle().startSystemMove()
            event.accept()
            return

        if not self._interaction_enabled:
            event.ignore()
            return

        super().mouseMoveEvent(event)


---
src/edon_ui/views/window.py
---
"""
Defines the main window for the Edon application.

This module contains the `MainWindow` class, which serves as the primary
top-level window, handling user interactions like resizing and providing
a container for the main graphics view.
"""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
from edon_ui.views.scene import GraphicsScene

if TYPE_CHECKING:
    from edon_ui.views.viewer import GraphicsView


# XXX: Look into resizing logic, this is a weak point that doesn't not work properly yet.
# XXX: We should also look up where the window is created when we are starting the application.
class MainWindow(QMainWindow):
    """
    Main application window for Edon.

    This window is frameless and handles custom resizing logic. It contains
    the main graphics view where nodes and edges are displayed.
    """

    MARGIN: int = 8

    def __init__(self, view: "GraphicsView") -> None:
        """
        Initializes the MainWindow.

        Args:
            view: The graphics view to display in this window.
        """
        super().__init__()
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(200, 200)
        self.resize(1000, 800)

        # Layout and canvas
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view: GraphicsView = view
        self.view.setParent(central_widget)
        self.scene = cast(GraphicsScene, view.scene())

        layout.addWidget(self.view)
        self.setCentralWidget(central_widget)

        # Window movement and resize state
        self._resizing: bool = False
        self._resize_edge = Qt.Edge

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse press events, primarily for initiating window resizing.

        If the left mouse button is pressed on a resize edge, system resizing
        is started.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._resize_edge = self._detect_edge(event.position().toPoint())
            if self._resize_edge != Qt.Edge:
                self._resizing = True
                self.windowHandle().startSystemResize(self._resize_edge)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Handles mouse release events, primarily for finalizing window resizing.

        If resizing was active, it's stopped on left mouse button release.

        Args:
            event: The mouse event.
        """
        if event.button() == Qt.MouseButton.LeftButton and self._resizing:
            self._resizing = False
            self._resize_edge = Qt.Edge
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _detect_edge(self, pos: QPoint) -> Qt.Edge:
        """
        Detects if a given point is on one of the window's resize edges.

        Args:
            pos: The point in local widget coordinates.

        Returns:
            A Qt.Edge enum indicating which edge(s) the point is on,
            or Qt.Edge() if none.
        """
        rect = self.rect()
        margin = self.MARGIN
        edges = Qt.Edge(0)

        if pos.x() <= rect.x() + margin:
            edges |= Qt.Edge.LeftEdge
        if pos.x() >= rect.x() + rect.width() - margin:
            edges |= Qt.Edge.RightEdge
        if pos.y() <= rect.y() + margin:
            edges |= Qt.Edge.TopEdge
        if pos.y() >= rect.y() + rect.height() - margin:
            edges |= Qt.Edge.BottomEdge

        return edges

    def is_position_on_resize_edge(self, global_pos: QPointF) -> bool:
        """
        Checks if a global position is on one of the window's resize edges.

        Args:
            global_pos: The position in global screen coordinates.

        Returns:
            True if the position is on a resize edge, False otherwise.
        """
        pos_in_local_coords: QPoint = self.mapFromGlobal(global_pos).toPoint()
        return self._detect_edge(pos_in_local_coords) != Qt.Edge

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """
        Overrides the context menu event to prevent default Qt context menus
        from interfering with custom application context menus.

        Args:
            event: The context menu event.
        """
        event.accept()


---
src/edon_ui/items/edge.py
---
"""Graphical representation of socket connections.

Provides classes and utility functions to compute and render visual edges that
connect socket items in the scene.
"""

from collections.abc import Callable

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QStyleOptionGraphicsItem, QWidget

from edon.types import EdgeKey
from edon.socket import SocketRole
from edon_ui import theme
from edon_ui.items.socket import SocketItem

PathCalculatorType = Callable[[QPointF, QPointF, bool, SocketRole], QPainterPath]


def straight_line_path_calculator(
    p1: QPointF, p2: QPointF, active: bool, starting_socket_role: SocketRole
) -> QPainterPath:
    """
    Calculates a straight-line QPainterPath between two points.

    Returns a direct line connecting the start and end positions.
    """
    path = QPainterPath()
    path.moveTo(p1)
    path.lineTo(p2)

    return path


def bezier_path_calculator(
    p1: QPointF, p2: QPointF, active: bool, starting_socket_role: SocketRole
) -> QPainterPath:
    """
    Calculates a cubic Bezier curve QPainterPath between two points.

    Returns a smooth curve computed using horizontal offsets from the endpoints.
    """
    path = QPainterPath()
    path.moveTo(p1)

    # Calculate horizontal offset between start and end
    dx = p2.x() - p1.x()
    # dy = p2.y() - p1.y() # Vertical distance, not directly used for this curve style

    # Configurable parameters (ideally from theme.py)
    horizontal_offset_factor = 0.6  # How far out control points extend, proportional to dx
    min_horizontal_offset = 30.0  # Minimum curve handle length in pixels
    max_horizontal_offset = 150.0  # Maximum curve handle length in pixels

    # Calculate absolute offset magnitude based on horizontal distance (dx)
    offset_magnitude_abs = abs(dx) * horizontal_offset_factor
    offset_magnitude_abs = max(min_horizontal_offset, offset_magnitude_abs)
    offset_magnitude_abs = min(max_horizontal_offset, offset_magnitude_abs)

    # Determine control point offset for the starting socket:
    # For TARGET role, control point extends to the left; otherwise, to the right.
    ctrl1_x_offset: float
    ctrl2_x_offset: float
    if starting_socket_role == SocketRole.TARGET:
        ctrl1_x_offset = -offset_magnitude_abs
    else:
        ctrl1_x_offset = offset_magnitude_abs

    # Determine control point offset for the target:
    # For an active (dragging) edge, the offset opposes the drag direction.
    # For a fixed target, the offset depends on the target socket's role.
    if active:
        if dx >= 0:
            ctrl2_x_offset = -offset_magnitude_abs
        else:
            ctrl2_x_offset = offset_magnitude_abs
    else:
        if starting_socket_role == SocketRole.TARGET:
            ctrl2_x_offset = offset_magnitude_abs
        else:
            ctrl2_x_offset = -offset_magnitude_abs

    ctrl1 = QPointF(p1.x() + ctrl1_x_offset, p1.y())
    ctrl2 = QPointF(p2.x() + ctrl2_x_offset, p2.y())

    path.cubicTo(ctrl1, ctrl2, p2)

    return path


class DraggingEdgeItem(QGraphicsPathItem):
    """
    Temporary visual edge used during socket connection dragging.

    Provides real-time feedback by updating its path as the mouse moves.
    """

    Type = QGraphicsItem.UserType + 2  # type: ignore[attr-defined]

    def __init__(
        self,
        source_socket_item: SocketItem,
        initial_mouse_scene_pos: QPointF,
        path_calculator: PathCalculatorType = straight_line_path_calculator,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(parent)

        self.source_socket_item: SocketItem = source_socket_item
        self._source_pos: QPointF = self.source_socket_item.link_item.scenePos()
        self._current_target_pos: QPointF = initial_mouse_scene_pos
        self._path_calculator: PathCalculatorType = path_calculator

        self.setZValue(theme.EDGE_Z_VALUE_DRAGGING)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

        self._pen: QPen = QPen(theme.EDGE_COLOR_DRAGGING, theme.EDGE_THICKNESS_DRAGGING)
        self._pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        self._update_internal_path()

    def _update_internal_path(self) -> None:
        self._source_pos = (
            self.source_socket_item.link_item.scenePos()
        )  # Use link_item for position
        # Access role directly from the SocketItem
        starting_role = self.source_socket_item.role
        path = self._path_calculator(
            self._source_pos, self._current_target_pos, True, starting_role
        )
        self.setPath(path)

    def update_target_position(self, new_mouse_scene_pos: QPointF) -> None:
        if self._current_target_pos != new_mouse_scene_pos:
            self.prepareGeometryChange()

            self._current_target_pos = new_mouse_scene_pos
            self._update_internal_path()

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(self._pen)
        painter.drawPath(self.path())

    def type(self) -> int:
        return self.__class__.Type


class EdgeItem(QGraphicsPathItem):
    """
    Visual edge connecting two socket items.

    Dynamically updates its path based on socket movements and renders with styling
    that reflects its interaction state.
    """

    Type = QGraphicsItem.UserType + 1  # type: ignore[attr-defined]

    def __init__(
        self,
        source_socket_item: SocketItem,
        target_socket_item: SocketItem,
        path_calculator: PathCalculatorType = straight_line_path_calculator,
        parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(parent)

        self.setZValue(theme.EDGE_Z_VALUE)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self._path_calculator = path_calculator

        self.source_socket_item: SocketItem = source_socket_item
        self.target_socket_item: SocketItem = target_socket_item

        # Positions are taken from the link_item of the SocketItem
        self._source_pos: QPointF = self.source_socket_item.link_item.scenePos()
        self._target_pos: QPointF = self.target_socket_item.link_item.scenePos()

        self._pen = QPen(theme.EDGE_COLOR_DEFAULT, theme.EDGE_THICKNESS)
        self._pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        self._pen_selected = QPen(theme.EDGE_COLOR_SELECTED, theme.EDGE_THICKNESS)
        self._pen_selected.setCapStyle(Qt.PenCapStyle.RoundCap)

        self._edge_key: EdgeKey | None = None

        self.update_path()

    @property
    def edge_key(self) -> EdgeKey:
        if not self._edge_key:
            # Access socket_address directly from SocketItem
            source_socket_addr = self.source_socket_item.address
            target_socket_addr = self.target_socket_item.address
            self._edge_key = EdgeKey(source_socket_addr, target_socket_addr)
        return self._edge_key

    def boundingRect(self) -> QRectF:
        """
        Returns the bounding rectangle of this edge.

        The rectangle includes padding around the path to make it easier to interact with,
        especially if the line is thin.
        """
        path_rect = self.path().boundingRect()
        padding = self._pen.widthF() * 4
        return path_rect.adjusted(-padding, -padding, padding, padding)

    def update_path(self) -> None:
        self.prepareGeometryChange()

        # Positions are taken from the link_item of the SocketItem
        self._source_pos = self.source_socket_item.link_item.scenePos()
        self._target_pos = self.target_socket_item.link_item.scenePos()

        # An EdgeItem is always static when it simply "exists", meaning, it's inactive and it starts
        # from it's source role. The role is taken directly from the source SocketItem.
        path = self._path_calculator(
            self._source_pos, self._target_pos, False, self.source_socket_item.role
        )
        self.setPath(path)

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        if self.isSelected():
            pen = self._pen_selected
        else:
            pen = self._pen

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.drawPath(self.path())

    def type(self) -> int:
        return self.__class__.Type


---
src/edon_ui/items/factory.py
---
"""
UI Factory functions for constructing NodeItem, SocketRowItem, and socket widgets from entity nodes and sockets.
This centralizes all UI construction logic for the node editor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from edon.graph import EntitySubGraphNode
from edon.types import SocketRole
from edon_ui import theme
from edon_ui.items.node import NodeItem, SubGraphNodeItem
from edon_ui.items.socket import SocketComponent, SocketComponents, SocketItem, SocketLinkItem
from edon_ui.widgets import (
    SOCKET_WIDGET_COMPONENT_FACTORIES,
    SocketLabel,
    SocketTextAdaptor,
    SocketWidgetAdaptor,
)

if TYPE_CHECKING:
    from edon.node import EntityNode
    from edon.socket import EntitySocket
    from edon.types import SocketDef, SocketDisplayState, SocketType


def create_socket_widget_component(
    entity_socket: EntitySocket,
    node_id: str,
    initial_value: Any | None = None,
) -> SocketWidgetAdaptor:
    """
    Constructs a socket widget component for a specified entity socket.

    This function utilizes the SOCKET_WIDGET_COMPONENT_FACTORIES to retrieve a factory function
    that generates a SocketWidgetAdaptor along with its associated QWidget.
    """
    logger.debug(f"Creating socket widget item for {entity_socket}")

    type_info = entity_socket.type_info
    socket_name = entity_socket.name

    factory_func = SOCKET_WIDGET_COMPONENT_FACTORIES.get(type_info)
    assert factory_func is not None, (
        f"CORRUPTION: `factory_func` needs to exists in {SOCKET_WIDGET_COMPONENT_FACTORIES}"
    )

    return factory_func(
        initial_value=initial_value,
        node_id=node_id,
        socket_name=socket_name,
    )


def create_socket_item(
    entity_socket: EntitySocket,
    display_state: SocketDisplayState,
) -> SocketItem:
    """Factory for creating a socket row with the correct composition."""
    logger.debug(f"Creating socket item for {entity_socket}::{display_state}")

    socket_type: SocketType = entity_socket.type_info
    initial_socket_value: Any = entity_socket.value

    socket_component = SocketLinkItem(None, visual_type_key=socket_type.description)
    label_component = SocketTextAdaptor(
        text_item=SocketLabel(
            text=socket_type.python_type.__name__,
            target_layout_height=theme.SOCKET_ROW_HEIGHT,
        )
    )
    widget_component = create_socket_widget_component(
        entity_socket, entity_socket.node.id, initial_value=entity_socket.value
    )

    assert socket_component and label_component and widget_component, (
        "CORRUPTION: All components needs to exists."
    )

    return SocketItem(
        role=entity_socket.role,
        entity_name=entity_socket.name,
        node_entity_id=entity_socket.node.id,
        components=SocketComponents(
            link=socket_component,
            label=label_component,
            widget=widget_component,
            display_state=display_state,
        ),
    )


def _get_socketdef(socket_defs: list[SocketDef], name: str) -> SocketDef | None:
    for sd in socket_defs:
        if sd.name == name:
            return sd
    return None


def create_node_item(
    entity_node: EntityNode,
) -> NodeItem:
    logger.debug(f"Creating {entity_node.node_type} node from factory.")

    target_sockets_ui: list[SocketItem] = []
    source_sockets_ui: list[SocketItem] = []
    actual_node_item_class: type[NodeItem]

    # XXX: This will most likely change when we start with serialization.
    if isinstance(entity_node, EntitySubGraphNode):
        actual_node_item_class = SubGraphNodeItem
        # For SubGraphNode, its sockets (proxies) are dynamically created.
        # We need to create SocketDef instances on-the-fly for the UI factory,
        # as SubGraphNode doesn't rely on class-level socket_definitions for its proxy sockets' UI.
        # The EntitySocket instances on SubGraphNode already have type_info and default_value.
        from edon.types import SocketDef, SocketDisplayState

        for entity_socket_instance in entity_node.target_sockets:
            # Create a SocketDef based on the EntitySocket's properties
            temp_socket_def = SocketDef(
                name=entity_socket_instance.name,
                socket_type=entity_socket_instance.type_info,  # entity_socket.type_info is SocketType
                default=entity_socket_instance.default_value,
                display_state=SocketDisplayState.ALL,  # Explicitly set, or rely on SocketDef default
            )
            row = create_socket_item(entity_socket_instance, temp_socket_def.display_state)
            target_sockets_ui.append(row)

        for entity_socket_instance in entity_node.source_sockets:
            temp_socket_def = SocketDef(
                name=entity_socket_instance.name,
                socket_type=entity_socket_instance.type_info,
                default=entity_socket_instance.default_value,
                display_state=SocketDisplayState.ALL,  # Explicitly set
            )
            row = create_socket_item(entity_socket_instance, temp_socket_def.display_state)
            source_sockets_ui.append(row)
    else:
        actual_node_item_class = NodeItem
        # Existing logic for regular EntityNodes that use class-level socket_definitions
        source_defs = type(entity_node).source_socket_definitions
        target_defs = type(entity_node).target_socket_definitions

        # The original assertion was: `assert source_defs and target_defs`
        # This can be problematic if a node legitimately has no inputs or no outputs.
        # For example, a constant node might only have source_sockets.
        # A print/display node might only have target_sockets.
        # We'll adjust the assertion to be more flexible, checking for None rather than emptiness,
        # as EntityNode.__post_init__ initializes these lists.
        assert source_defs is not None, (
            f"CORRUPTION: {type(entity_node).__name__}.source_socket_definitions is None. "
            "It should be an empty list if no source sockets are defined."
        )
        assert target_defs is not None, (
            f"CORRUPTION: {type(entity_node).__name__}.target_socket_definitions is None. "
            "It should be an empty list if no target sockets are defined."
        )

        for entity_socket in entity_node.target_sockets:
            socket_def = _get_socketdef(target_defs, entity_socket.name)
            assert socket_def is not None, (
                f"CORRUPTION: No `SocketDef` for target entity: {entity_socket}. Available Defs: {target_defs}"
            )
            row = create_socket_item(entity_socket, socket_def.display_state)
            target_sockets_ui.append(row)

        for entity_socket in entity_node.source_sockets:
            socket_def = _get_socketdef(source_defs, entity_socket.name)
            assert socket_def is not None, (
                f"CORRUPTION: No `SocketDef` for source entity: {entity_socket}. Available Defs: {source_defs}"
            )
            row = create_socket_item(entity_socket, socket_def.display_state)
            source_sockets_ui.append(row)

    # Instantiate the determined node item class
    ui_node = actual_node_item_class(
        title=entity_node.name,
        node_entity_id=entity_node.id,
        target_sockets=target_sockets_ui,
        source_sockets=source_sockets_ui,
    )
    return ui_node


---
src/edon_ui/items/node.py
---
"""Defines the NodeItem class, the visual representation of a node in the UI.

This module provides the QGraphicsObject subclass that handles rendering,
interaction, and layout for individual nodes within the graphics scene.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from loguru import logger
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsTextItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from edon.types import SocketRole
from edon_ui import theme

if TYPE_CHECKING:
    from edon_ui.views.scene import GraphicsScene
    from edon_ui.items.socket import SocketItem


class NodeItem(QGraphicsObject):
    """A visual node item in the editor, representing a logical node entity."""

    def __init__(
        self,
        title: str | None,
        node_entity_id: str,
        target_sockets: list[SocketItem] | None = None,
        source_sockets: list[SocketItem] | None = None,
        width: float = theme.NODE_MIN_WIDTH,
        height: float = theme.NODE_MIN_HEIGHT,
    ) -> None:
        super().__init__()

        self.title = title if title is not None else "Untitled"
        self.entity_id = node_entity_id
        self._min_width_param = width
        self._min_height_param = height

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCacheMode(QGraphicsItem.CacheMode.ItemCoordinateCache)

        self.title_text_item = QGraphicsTextItem(self.title, self)
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)

        self.target_sockets = target_sockets or []
        self.source_sockets = source_sockets or []
        for row in self.target_sockets + self.source_sockets:
            row.setParentItem(self)
            # XXX: I'm really unsure about this.
            # row.layout_dirty.connect(self._on_socket_row_layout_changed)

        self._width: float = 0
        self._height: float = 0

        # self._on_socket_row_layout_changed()

    @property
    def _scene(self) -> GraphicsScene:
        from edon_ui.views.scene import GraphicsScene

        scene = cast(GraphicsScene, self.scene())
        assert isinstance(scene, GraphicsScene), (
            "CORRUPTION: parent item of {self} is not of type `GraphicsScene`"
        )

        return scene

    def _calculate_dynamic_height(self) -> float:
        total_socket_rows_height = theme.NODE_TITLE_HEIGHT + theme.SOCKET_VERTICAL_CONTENT_MARGIN

        for idx, row in enumerate(self.target_sockets + self.source_sockets):
            total_socket_rows_height += row.boundingRect().height()
            if idx < len(self.target_sockets + self.source_sockets) - 1:
                total_socket_rows_height += theme.SOCKET_VERTICAL_ITEM_PADDING

        total_socket_rows_height += theme.SOCKET_VERTICAL_CONTENT_MARGIN
        content_area_height = max(total_socket_rows_height, theme.NODE_MIN_CONTENT_HEIGHT)

        return max(self._min_height_param, total_socket_rows_height, content_area_height)

    def _calculate_dynamic_width(self) -> float:
        max_row_w = 0
        all_rows = self.target_sockets + self.source_sockets
        if all_rows:
            max_row_w = max(row.boundingRect().width() for row in all_rows)

        # Remember to remove the padding
        min_content_width = theme.NODE_MIN_WIDTH - (theme.NODE_HORIZONTAL_PADDING * 2)
        calculated_total_width = max(max_row_w, min_content_width)

        return max(self._min_width_param, calculated_total_width)

    def _layout_socket_rows(self) -> None:
        """Layout input and output socket rows using their required width and height.

        This method positions each socket row within the node, stacking them vertically.
        Output rows are right-aligned, input rows are left-aligned.
        Padding is only added between rows, not after the last row.
        """
        current_row_top_y: float = theme.NODE_TITLE_HEIGHT + theme.SOCKET_VERTICAL_CONTENT_MARGIN

        # self._width should have been calculated by _calculate_dynamic_width() before this method is called.
        # This is the width available for the content of the socket rows, inside the node's own padding.
        content_area_width_for_rows = self._width

        # Source sockets
        for row_item in self.source_sockets:
            row_item.update_layout(content_area_width_for_rows)
            # Position the row considering the node's left padding
            row_item.setPos(0, current_row_top_y)
            current_row_top_y += (
                row_item.boundingRect().height() + theme.SOCKET_VERTICAL_ITEM_PADDING
            )

        # Target sockets
        for idx, row_item in enumerate(self.target_sockets):
            row_item.update_layout(content_area_width_for_rows)  # Pass the available width
            # Position the row considering the node's left padding
            row_item.setPos(0, current_row_top_y)
            current_row_top_y += row_item.boundingRect().height()
            if idx < len(self.target_sockets) - 1:
                current_row_top_y += theme.SOCKET_VERTICAL_ITEM_PADDING

    def _on_socket_row_layout_changed(self) -> None:
        """Handle a socket row's layout change by relayouting the entire node."""
        self.prepareGeometryChange()

        # Recalculate node's own width first based on potentially changed intrinsic needs of rows
        self._width = self._calculate_dynamic_width()

        # Then, layout socket rows, passing them the available content width
        self._layout_socket_rows()

        # Finally, calculate the node's height based on the new row layouts
        self._height = self._calculate_dynamic_height()

        logger.info(f"Node {self.entity_id} layout changed: {self._width}x{self._height}")

        self.update()

        self._scene.node_redraw_ui_request.emit(self.entity_id, self._scene)

        # self._scene.handle_ui_redraw_node_item(self)
        # self._scene._update_redraw_node_item(self)

    def add_socket_item(self, socket_item: SocketItem) -> None:
        assert socket_item not in self.target_sockets + self.source_sockets, (
            "CORRUPTION: Trying to add non-unique socket {SocketItem} to node {self}"
        )

        # We have to add the new socket as a child to the node item, this create the
        # internal Qt wiring and add it to the scene as well.
        socket_item.setParentItem(self)

        role = socket_item.role
        if role == SocketRole.SOURCE:
            self.source_sockets.append(socket_item)
        else:
            self.target_sockets.append(socket_item)

        self._on_socket_row_layout_changed()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """
        Handles item state changes, like position changes.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self._scene.node_redraw_ui_request.emit(self.entity_id, self._scene)
            self._scene._update_active_area_rect()

        return super().itemChange(change, value)

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Main node body
        node_rect = self.boundingRect()
        painter.setBrush(QBrush(theme.NODE_BACKGROUND))

        # Border
        border_width = theme.NODE_BORDER_WIDTH_DEFAULT
        if self.isSelected():
            pen = QPen(theme.NODE_BORDER_SELECTED, theme.NODE_BORDER_WIDTH_SELECTED)
            border_width = theme.NODE_BORDER_WIDTH_SELECTED  # For consistency if used elsewhere
        else:
            pen = QPen(theme.NODE_BORDER_DEFAULT, theme.NODE_BORDER_WIDTH_DEFAULT)
        painter.setPen(pen)
        painter.drawRoundedRect(node_rect, theme.NODE_BORDER_RADIUS, theme.NODE_BORDER_RADIUS)

        # Title Bar area
        # Create a path for the title bar with rounded top corners
        title_bar_rect = QRectF(0, 0, node_rect.width(), theme.NODE_TITLE_HEIGHT)
        # To ensure title bar fill respects the main border radius at top corners:
        # Create a path for the title bar background fill
        # Adjust for half border width to be inside the main border line
        # Corrected title bar drawing logic for perfect rounded tops inside border
        half_border = border_width / 2.0
        fill_title_rect = title_bar_rect.adjusted(
            half_border, half_border, -half_border, 0
        )  # Don't adjust bottom for fill

        title_fill_path = QPainterPath()
        title_fill_path.moveTo(
            fill_title_rect.left() + theme.NODE_BORDER_RADIUS - half_border, fill_title_rect.top()
        )
        title_fill_path.lineTo(
            fill_title_rect.right() - theme.NODE_BORDER_RADIUS + half_border, fill_title_rect.top()
        )
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.right() - 2 * theme.NODE_BORDER_RADIUS + half_border,
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS - half_border,  # arc width
                2 * theme.NODE_BORDER_RADIUS - half_border,  # arc height
            ),
            90,
            -90,
        )
        title_fill_path.lineTo(
            fill_title_rect.right(), fill_title_rect.bottom()
        )  # Straight down to bottom of title bar rect
        title_fill_path.lineTo(
            fill_title_rect.left(), fill_title_rect.bottom()
        )  # Straight across bottom
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.left(),
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS - half_border,
                2 * theme.NODE_BORDER_RADIUS - half_border,
            ),
            180,
            -90,
        )
        title_fill_path.closeSubpath()

        painter.setBrush(QBrush(theme.NODE_TITLE_BACKGROUND))
        painter.setPen(Qt.PenStyle.NoPen)  # No border for the fill path itself
        painter.drawPath(title_fill_path)

        # Position and draw title text (QGraphicsTextItem handles its own drawing)
        # Ensure title_text_item is correctly positioned.
        # The initial positioning in __init__ might not be perfect after font metrics.
        # For truly centered text in a custom-drawn rounded rect, manual calculation is best.
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)

        # Center the QGraphicsTextItem within the title bar rect
        title_text_rect = self.title_text_item.boundingRect()
        title_text_x = (self._width - title_text_rect.width()) / 2
        title_text_y = (theme.NODE_TITLE_HEIGHT - title_text_rect.height()) / 2
        self.title_text_item.setPos(title_text_x, title_text_y)


class SubGraphNodeItem(NodeItem):
    """A visual node item for SubGraphNodes, with distinct styling."""

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Main node body
        node_rect = self.boundingRect()
        # Use SUBGRAPH_NODE_BACKGROUND for the main body
        painter.setBrush(QBrush(theme.SUBGRAPH_NODE_BACKGROUND))  # Changed line

        # Border (same as NodeItem)
        border_width = theme.NODE_BORDER_WIDTH_DEFAULT
        if self.isSelected():
            pen = QPen(theme.NODE_BORDER_SELECTED, theme.NODE_BORDER_WIDTH_SELECTED)
            border_width = theme.NODE_BORDER_WIDTH_SELECTED
        else:
            pen = QPen(theme.NODE_BORDER_DEFAULT, theme.NODE_BORDER_WIDTH_DEFAULT)
        painter.setPen(pen)
        painter.drawRoundedRect(node_rect, theme.NODE_BORDER_RADIUS, theme.NODE_BORDER_RADIUS)

        # Title Bar area (copied from NodeItem.paint)
        # Create a path for the title bar with rounded top corners
        title_bar_rect = QRectF(0, 0, node_rect.width(), theme.NODE_TITLE_HEIGHT)
        # Adjust for half border width to be inside the main border line
        half_border = border_width / 2.0
        fill_title_rect = title_bar_rect.adjusted(
            half_border, half_border, -half_border, 0
        )  # Don't adjust bottom for fill

        title_fill_path = QPainterPath()
        title_fill_path.moveTo(
            fill_title_rect.left() + theme.NODE_BORDER_RADIUS - half_border, fill_title_rect.top()
        )
        title_fill_path.lineTo(
            fill_title_rect.right() - theme.NODE_BORDER_RADIUS + half_border, fill_title_rect.top()
        )
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.right() - 2 * theme.NODE_BORDER_RADIUS + half_border,
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS - half_border,  # arc width
                2 * theme.NODE_BORDER_RADIUS - half_border,  # arc height
            ),
            90,
            -90,
        )
        title_fill_path.lineTo(
            fill_title_rect.right(), fill_title_rect.bottom()
        )  # Straight down to bottom of title bar rect
        title_fill_path.lineTo(
            fill_title_rect.left(), fill_title_rect.bottom()
        )  # Straight across bottom
        title_fill_path.arcTo(
            QRectF(
                fill_title_rect.left(),
                fill_title_rect.top(),
                2 * theme.NODE_BORDER_RADIUS - half_border,
                2 * theme.NODE_BORDER_RADIUS - half_border,
            ),
            180,
            -90,
        )
        title_fill_path.closeSubpath()

        painter.setBrush(QBrush(theme.NODE_TITLE_BACKGROUND))  # Title background remains the same
        painter.setPen(Qt.PenStyle.NoPen)  # No border for the fill path itself
        painter.drawPath(title_fill_path)

        # Position and draw title text (same as NodeItem)
        self.title_text_item.setDefaultTextColor(theme.NODE_TITLE_TEXT)
        self.title_text_item.setFont(theme.FONT_NODE_TITLE)

        # Center the QGraphicsTextItem within the title bar rect
        title_text_rect = self.title_text_item.boundingRect()
        title_text_x = (self._width - title_text_rect.width()) / 2
        title_text_y = (theme.NODE_TITLE_HEIGHT - title_text_rect.height()) / 2
        self.title_text_item.setPos(title_text_x, title_text_y)


---
src/edon_ui/items/socket.py
---
"""Defines visual components related to node sockets in the UI.

This module includes classes for individual socket connection points (`SocketCircleItem`)
and rows that can contain a socket circle, label, and widget (`SocketRowItem`),
along with a protocol (`SocketComponent`) for items within a socket row.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

from loguru import logger
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsSceneMouseEvent,
)

from edon.types import SocketAddress, SocketDisplayState, SocketRole
from edon_ui import theme
from edon_ui.widgets.adaptors import SocketTextAdaptor, SocketWidgetAdaptor

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsSceneHoverEvent

    from edon_ui.items.node import NodeItem
    from edon_ui.views.scene import GraphicsScene


@runtime_checkable
class SocketComponent(Protocol):
    """
    Protocol defining the interface for a visual component within a SocketRowItem.

    Extends QGraphicsItem to inherit all the standard Qt graphics functionality,
    and adds the specific layout methods needed for socket components.
    """

    def get_required_component_width(self) -> float:
        """Returns the intrinsic width this component requires for layout."""
        ...

    def get_required_component_height(self) -> float:
        """Returns the intrinsic height this component requires for layout."""
        ...


@runtime_checkable
class SocketTextComponent(SocketComponent, Protocol):
    """
    Protocol defining the interface for a visual text component within a SocketItem.
    """

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        """Sets the alignment for the text component"""
        ...


@dataclass
class SocketComponents:
    """Pure data structure holding socket visual components."""

    link: SocketLinkItem
    label: SocketTextAdaptor
    widget: SocketWidgetAdaptor
    display_state: SocketDisplayState

    def __post_init__(self):
        self.transition_to(self.display_state)

    def height(self) -> float:
        return sum(
            [_.get_required_component_height() for _ in self.visible() if _ is not self.link]
        )

    def width(self) -> float:
        return max(
            [_.get_required_component_width() for _ in self.visible() if _ is not self.link]
        )

    def transition_to(self, state: SocketDisplayState) -> None:
        match state:
            case SocketDisplayState.ALL:
                self.link.show()
                self.label.show()
                self.widget.show()
            case SocketDisplayState.LINK_LABEL:
                self.link.show()
                self.label.show()
                self.widget.hide()
            case SocketDisplayState.LINK_WIDGET:
                self.link.show()
                self.label.hide()
                self.widget.show()
            case SocketDisplayState.LABEL:
                self.label.show()
                self.link.hide()
                self.widget.hide()
            case SocketDisplayState.WIDGET:
                self.link.hide()
                self.label.hide()
                self.widget.show()

    def __iter__(self) -> Iterator[SocketComponent]:
        return iter([self.link, self.label, self.widget])

    def visible(self) -> list[SocketWidgetAdaptor]:
        return [c for c in self if c.isVisible()]


def _layout_target_socket(
    components: SocketComponents, padding: float = theme.SOCKET_HORIZONTAL_PADDING
) -> None:
    """Layout components for TARGET role: [circle][padding][content]
    Content (label/widget) is stacked vertically and starts at x=0.
    Circle is positioned to the left of content, vertically centered with the primary content component.
    """
    current_y = 0.0

    label, label_visble = components.label, components.label.isVisible()
    widget, widget_visble = components.widget, components.widget.isVisible()
    link, link_visble = components.link, components.link.isVisible()

    assert label_visble or widget_visble, (
        "CORRUPTION: At least one of label and widget needs to be visible."
    )

    logger.error(f"VISIBLE: {label_visble}::{widget_visble}::{link_visble}")

    primary_content_height = 0.0
    if label_visble:
        primary_content_height = label.get_required_component_height()
    elif widget_visble:
        primary_content_height = widget.get_required_component_height()

    if link_visble:
        circle_radius = link.get_required_component_height() / 2.0
        circle_y_center = primary_content_height / 2.0
        circle_x_pos = -circle_radius - padding
        link.setPos(QPointF(circle_x_pos, circle_y_center))

    if label_visble:
        label.setPos(QPointF(0, current_y))
        current_y += components.label.get_required_component_height()

    if widget_visble:
        widget.setPos(QPointF(0, current_y))


def _layout_source_socket(
    components: SocketComponents,
    available_width: float,
    padding: float = theme.SOCKET_HORIZONTAL_PADDING,
) -> None:
    """Layout components for SOURCE role: [content][padding][circle]
    Content (label/widget) is stacked vertically and right-aligned within available_width.
    Circle is positioned to the right of content, vertically centered with the primary content component.
    """
    current_content_y = 0.0

    label, label_visble = components.label, components.label.isVisible()
    widget, widget_visble = components.widget, components.widget.isVisible()
    link, link_visble = components.link, components.link.isVisible()

    assert label_visble or widget_visble, (
        "CORRUPTION: At least one of label and widget needs to be visible."
    )

    primary_content_height = 0.0
    if label_visble:
        primary_content_height = label.get_required_component_height()
    elif widget_visble:
        primary_content_height = widget.get_required_component_height()

    if label_visble:
        label_width = label.get_required_component_width()
        label.setPos(QPointF(available_width - label_width, current_content_y))
        current_content_y += label.get_required_component_height()

    if widget_visble:
        widget_width = widget.get_required_component_width()
        widget.setPos(QPointF(available_width - widget_width, current_content_y))

    if link_visble:
        circle_radius = link.get_required_component_height() / 2.0
        circle_y_center = primary_content_height / 2.0
        circle_x_pos = available_width + circle_radius + padding
        link.setPos(QPointF(circle_x_pos, circle_y_center))


class SocketLinkItem(QGraphicsEllipseItem):
    """Represents the interactive circular connection point of a socket.

    Its (0,0) is its visual and logical center. It is linked to a logical
    socket entity via its name and parent node entity ID.

    Attributes:
        visual_type_key: A string key to determine visual styling from the theme.
    """

    def __init__(
        self,
        parent: QGraphicsItem | None,
        visual_type_key: str = "default",
    ) -> None:
        self._radius = theme.SOCKET_RADIUS
        ellipse_rect = QRectF(-self._radius, -self._radius, 2 * self._radius, 2 * self._radius)
        super().__init__(ellipse_rect, parent)

        self.visual_type_key = visual_type_key
        self._original_fill_color: QColor = theme.SOCKET_FILL_COLORS.get(
            self.visual_type_key, theme.SOCKET_FILL_COLOR_DEFAULT
        )
        self._hover_fill_color: QColor = self._original_fill_color.lighter(150)
        self._drop_target_highlight_color: QColor = QColor(Qt.GlobalColor.green).lighter(
            120
        )  # Placeholder: bright green

        self._is_hovered: bool = False
        self._is_drop_target: bool = False
        self._is_valid_drop_target: bool = False

        pen = QPen(theme.SOCKET_BORDER_COLOR)
        pen.setWidthF(1.0)

        self.setPen(pen)
        self.setBrush(QBrush(self._original_fill_color))
        self.setAcceptHoverEvents(True)

    @property
    def _socket_item(self) -> SocketItem:
        socket_item = cast(SocketItem, self.parentItem())
        assert isinstance(socket_item, SocketItem), (
            "CORRUPTION: parent item of {self} is not of type `SocketItem`"
        )

        return socket_item

    def _update_brush(self) -> None:
        """Updates the socket's fill brush based on its current state (hover, drop target)."""
        if self._is_drop_target:
            self.setBrush(QBrush(self._drop_target_highlight_color))
        elif self._is_hovered:
            self.setBrush(QBrush(self._hover_fill_color))
        else:
            self.setBrush(QBrush(self._original_fill_color))
        self.update()

    def get_required_component_width(self) -> float:
        return self.boundingRect().width()

    def get_required_component_height(self) -> float:
        return self.boundingRect().height()

    def set_not_valid_drop_target(self, disabled: bool) -> None:
        self._is_valid_drop_target = disabled
        self.setOpacity(0.3 if disabled else 1.0)

    def set_drop_target_highlight(self, highlight: bool) -> None:
        if self._is_valid_drop_target:
            return

        if not self._is_drop_target == highlight:
            self._is_drop_target = highlight
            self._update_brush()

    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = True
            self._update_brush()

        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        if not self._is_valid_drop_target:
            self._is_hovered = False
            self._update_brush()

        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._socket_item.handle_link_press(event)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        # Check if a drag is active before attempting to call the parent's handler.
        # The parent's handler might assume a drag is in progress.
        scene = cast("GraphicsScene", self.scene())
        if scene.is_dragging_edge():
            self._socket_item.handle_link_move(event)
            event.accept()
        else:
            # It's important to call the base class implementation if we're not handling the event,
            # especially for events like mouseMove that might be used by QGraphicsItem for other purposes.
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            # Similar to mouseMoveEvent, only delegate if a drag was active.
            scene = cast("GraphicsScene", self.scene())
            if scene.is_dragging_edge():
                self._socket_item.handle_link_release(event)
                event.accept()
            else:
                # If no drag was active, perhaps the press was consumed elsewhere or it was a simple click
                # without initiating a drag. Call super to ensure normal event processing.
                super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)


class SocketItem(QGraphicsObject):
    """A composable row for a socket, containing optional label, circle, and widget.

    This item manages the layout of its child components (label, circle, widget)
    based on whether it's an input or output socket and its connection state.
    """

    def __init__(
        self,
        role: SocketRole,
        entity_name: str,
        node_entity_id: str,
        components: SocketComponents,
        parent: QGraphicsObject | None = None,
    ) -> None:
        super().__init__(parent)

        self.role = role
        self.entity_name = entity_name
        self.node_entity_id = node_entity_id

        self.components = components
        for item in self.components:
            item.setParentItem(self)

        alignment = Qt.AlignmentFlag.AlignLeft
        if self.role == SocketRole.SOURCE:
            alignment = Qt.AlignmentFlag.AlignRight
        self.components.label.set_text_alignment(alignment)

        self._width: float = 0.0
        self._height: float = 0.0
        self._address: SocketAddress | None = None

        self._calculate_bounding_rect()

    @property
    def link_item(self) -> SocketLinkItem:
        """Provides access to the socket's connection circle (SocketLinkItem)."""
        return self.components.link

    @property
    def address(self) -> SocketAddress:
        if not self._address:
            self._address = SocketAddress(self.node_entity_id, self.entity_name, self.role)
        return self._address

    @property
    def _node_item(self) -> NodeItem:
        from edon_ui.items.node import NodeItem

        node_item = cast(NodeItem, self.parentItem())
        assert isinstance(node_item, NodeItem), (
            "CORRUPTION: parent item of {self} is not of type `NodeItem`"
        )

        return node_item

    @property
    def _scene(self) -> GraphicsScene:
        from edon_ui.views.scene import GraphicsScene

        scene = cast(GraphicsScene, self.scene())
        assert isinstance(scene, GraphicsScene), (
            "CORRUPTION: parent item of {self} is not of type `GraphicsScene`"
        )

        return scene

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._width, self._height)

    def handle_link_press(self, event: QGraphicsSceneMouseEvent) -> None:
        logger.debug(f"SocketItem link in {self.address} pressed at {event.scenePos()}")

        self._scene.edge_drag_initiation_request.emit(self.address, event.scenePos(), self._scene)

    def handle_link_move(self, event: QGraphicsSceneMouseEvent) -> None:
        # The scene's update_dragging_edge method typically doesn't need the socket_address,
        # just the current mouse position.
        self._scene.edge_drag_action(event.scenePos())

    def handle_link_release(self, event: QGraphicsSceneMouseEvent) -> None:
        logger.debug(
            f"SocketItem link '{self.node_entity_id}::{self.entity_name}' released at {event.scenePos()}"
        )

        self._scene.edge_drop_action(event.scenePos())

    def update_layout(self, available_width: float) -> None:
        """Updates the layout of socket components based on role and available width."""
        self._calculate_bounding_rect()

        if self.role == SocketRole.TARGET:
            _layout_target_socket(self.components, theme.SOCKET_HORIZONTAL_PADDING)
        else:
            _layout_source_socket(
                self.components, available_width, theme.SOCKET_HORIZONTAL_PADDING
            )

        self.update()

    def set_drop_target_highlight(self, highlight: bool) -> None:
        """Forwards the drop target highlight state to the underlying SocketLinkItem."""
        self.components.link.set_drop_target_highlight(highlight)

    def transition_to(self, linked: bool) -> None:
        if self.role == SocketRole.SOURCE:
            return

        if linked:
            self.components.transition_to(SocketDisplayState.LINK_LABEL)
        else:
            self.components.transition_to(self.components.display_state)

        self._calculate_bounding_rect()
        self._node_item._on_socket_row_layout_changed()

    def _calculate_bounding_rect(self) -> None:
        """Calculates the bounding rectangle for the SocketItem's main content area.
        This area is defined by the stacked label and/or widget components.
        The SocketItem's own (0,0) is considered the top-left of this label/widget block.
        """
        self.prepareGeometryChange()

        components = self.components.visible()
        assert components, (
            f"CORRUPTION: Node should always have at least one component. {self.components}"
        )

        self._width = self.components.width()
        self._height = self.components.height()

    # def paint(
    #     self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    # ) -> None:
    #     """Overrides the pure virtual paint method from QGraphicsObject.
    #
    #     This method must be implemented, even if it does nothing, to prevent
    #     a pure virtual function call error at runtime when Qt attempts to paint
    #     this QGraphicsObject. In this adaptor, painting is handled by the
    #     child QGraphicsTextItem, so this method intentionally does nothing.
    #     """
    #     pass


---
src/edon/errors.py
---
"""Defines structured error reasons for graph operations within the Edon core.

This module centralizes enumerations used to convey specific reasons for failures
or exceptional conditions encountered during operations on the edon entity system.

The enums are categorized by the type of operation or object they pertain to:
- `SocketConnectionErrorReason`: For issues arising during attempts to connect sockets.
- `GraphObjectErrorReason`: For problems related to the existence or validity of
                             nodes and sockets themselves.
- `SocketDisconnectionErrorReason`: For issues during attempts to disconnect sockets.
"""

from enum import Enum, auto


class SocketLinkErrorReason(Enum):
    """Enumerates reasons why a socket connection attempt might fail."""

    # Compatibility Issues
    CANNOT_LINK_TO_SELF = auto()
    DIRECTIONS_NOT_OPPOSITE = auto()
    SAME_PARENT_NODE = auto()
    TYPE_MISMATCH = auto()
    ALREADY_LINKED = auto()

    # Arity/Limit Issues
    INPUT_SOCKET_FULL = auto()  # e.g., Input socket already has a connection and doesn't allow more
    OUTPUT_SOCKET_LIMIT_REACHED = auto()  # If an output socket had a fan-out limit (less common)

    # General/Other
    TARGET_SOCKET_INVALID = auto()  # Placeholder if other_socket itself is None or invalid
    UNKNOWN = auto()  # Generic fallback
    CYCLE_DETECTED = auto()


class GraphObjectErrorReason(Enum):
    """Enumerates reasons for errors related to graph object (node/socket) access or validity."""

    NODE_NOT_FOUND = auto()
    SOCKET_NOT_FOUND = auto()
    SOCKET_DIRECTION_INVALID = auto()  # e.g. trying to use an input as an output in connect_sockets


class SocketUnlinkErrorReason(Enum):
    """Enumerates reasons why a socket disconnection attempt might fail."""

    SOCKETS_NOT_LINKED = auto()
    UNKNOWN = auto()  # Generic fallback


---
src/edon/executor.py
---
"""Provides the `ExecutionEngine` for processing and running `EntityGraph` instances.

This module defines the `ExecutionEngine`, which is responsible for the orderly
execution of an `EntityGraph`. The core functionality involves:
1.  Topologically sorting the nodes within the graph to determine a valid
    execution sequence that respects data dependencies. This is achieved
    using Kahn's algorithm.
2.  Iterating through the sorted nodes and invoking their `process()` method,
    allowing each node to perform its defined computation or action.

The engine ensures that graphs with cycles are not executed and provides
logging for the execution flow and any errors encountered.

Enhanced to support recursive execution of sub-graphs with depth tracking
and context management.
"""

from collections import deque
from loguru import logger

from edon.node import EntityNode
from edon.graph import EntityGraph
from edon.types import current_graph_context, current_execution_engine_context


class ExecutionEngine:
    """
    Handles the execution of a node graph, including topological sorting
    and node processing.

    Supports recursive execution of sub-graphs with configurable depth limits
    to prevent infinite recursion.
    """

    def __init__(self, max_depth: int = 10):
        """Initialize the execution engine.

        Args:
            max_depth: Maximum allowed nesting depth for sub-graph execution.
                      Prevents infinite recursion in malformed sub-graphs.
        """
        self.max_depth = max_depth
        self._current_depth = 0

    def _topological_sort(self, graph: EntityGraph) -> list[EntityNode]:
        """
        Performs a topological sort of the nodes in the graph using Kahn's algorithm.
        """
        # Initialize in-degree count for all nodes in the graph.
        # The in-degree of a node is the number of incoming edges.
        in_degree: dict[str, int] = {node_id: 0 for node_id in graph.nodes}

        # Calculate initial in-degrees for all nodes.
        # Use graph edges to determine dependencies instead of socket.links
        for edge in graph.edges:
            # In a directed edge from source to target, target depends on source
            # So target has incoming degree from source
            target_node_id = edge.target.node_id
            if target_node_id in in_degree:
                in_degree[target_node_id] += 1

        # Initialize a queue with all nodes that have an in-degree of 0.
        # These are the source nodes of the graph (nodes with no incoming dependencies).
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])

        execution_order: list[EntityNode] = []

        while queue:
            # Dequeue a node. This node is now processed and added to the execution order.
            u_node_id = queue.popleft()

            # Ensure the node ID from the queue is actually in the graph before accessing.
            # This is a robustness check, though unlikely to fail in a stable graph state.
            if u_node_id not in graph.nodes:
                logger.warning(
                    f"Node ID '{u_node_id}' from sort queue not in graph.nodes. Skipping."
                )
                continue

            u_node = graph.nodes[u_node_id]
            execution_order.append(u_node)

            # For each outgoing connection from the processed node (u_node):
            # Decrement the in-degree of the connected (dependent) node (v_node).
            for edge in graph.edges:
                if edge.source.node_id == u_node_id:
                    v_node_id = edge.target.node_id
                    if v_node_id in in_degree:
                        in_degree[v_node_id] -= 1
                        # If a dependent node's in-degree drops to 0, it means all its
                        # prerequisites are met, so it can be added to the queue for processing.
                        if in_degree[v_node_id] == 0:
                            queue.append(v_node_id)

        # After the loop, if the number of nodes in the execution order
        # does not match the total number of nodes in the graph, it indicates a cycle
        # or disconnected components that weren't processed.
        if len(execution_order) != len(graph.nodes):
            # Identify nodes that might be part of a cycle or are otherwise unreachable
            # through this specific sort (nodes with in_degree > 0 after the loop).
            # This condition also catches cases where some nodes might not have been
            # included in the initial in_degree calculation if the graph is inconsistent.
            problematic_nodes_ids = [nid for nid, deg in in_degree.items() if deg > 0]
            # Also consider nodes not in execution_order but were in graph.nodes
            unprocessed_nodes_ids = set(graph.nodes.keys()) - set(n.id for n in execution_order)

            # Combine and get names for a more informative message
            all_problem_ids = problematic_nodes_ids + list(
                unprocessed_nodes_ids - set(problematic_nodes_ids)
            )
            problem_node_names = [
                graph.nodes[nid].name for nid in all_problem_ids if nid in graph.nodes
            ]

            if not problem_node_names and len(execution_order) < len(graph.nodes):
                # This case might indicate nodes that were never dependencies and had no outputs,
                # or some other graph inconsistency.
                raise RuntimeError(
                    f"Graph execution error: Not all nodes were processed. "
                    f"Processed {len(execution_order)} of {len(graph.nodes)}. "
                    f"Possible disconnected graph segments or other issues."
                )

            raise RuntimeError(
                f"Graph has a cycle or is disconnected. "
                f"Problematic nodes might include: {problem_node_names}. Cannot execute."
            )

        return execution_order

    def execute_graph(self, graph: EntityGraph, context: str = "root") -> None:
        """
        Executes the provided graph by processing its nodes in topological order.

        The execution involves:
        1. Performing a topological sort of the graph nodes.
        2. Iterating through the sorted nodes and calling their `process()` method.

        Supports recursive execution of sub-graphs with depth tracking.

        Args:
            graph: The EntityGraph to execute
            context: Description of the execution context for logging

        Raises:
            RuntimeError: If maximum nesting depth is exceeded or graph has cycles
        """
        if self._current_depth >= self.max_depth:
            raise RuntimeError(
                f"Maximum sub-graph nesting depth ({self.max_depth}) exceeded. "
                f"Current context: {context}"
            )

        if not graph.nodes:
            logger.info(
                f"Graph is empty at depth {self._current_depth} ({context}). Nothing to execute."
            )
            return

        logger.info(f"Starting graph execution at depth {self._current_depth} ({context})...")

        # Set the active engine context
        engine_token = current_execution_engine_context.set(self)
        graph_token = current_graph_context.set(graph)

        try:
            execution_order = self._topological_sort(graph)
            logger.info(f"Execution order at {context}: {[node.name for node in execution_order]}")

            for node in execution_order:
                logger.debug(
                    f"Processing node: {node.name} (ID: {node.id}) at depth {self._current_depth}"
                )

                # Check if this is a SubGraphNode and handle recursion
                if self._is_subgraph_node(node):
                    self._execute_subgraph_node(node)
                else:
                    node.process()
        # Ensure this catch is broad enough or specific to critical execution errors
        # For now, catching RuntimeError from _topological_sort or other unexpected issues
        # Re-raising to allow higher-level handling if necessary
        except RuntimeError as e:
            logger.error(f"Failed to execute graph at {context}: {e}")
            raise
        finally:
            current_graph_context.reset(graph_token)
            current_execution_engine_context.reset(engine_token)

        logger.info(f"Graph execution complete at depth {self._current_depth} ({context}).")

    def _is_subgraph_node(self, node: EntityNode) -> bool:
        """Check if a node is a SubGraphNode without importing to avoid circular imports."""
        return node.__class__.__name__ == "SubGraphNode"

    def _execute_subgraph_node(self, subgraph_node: EntityNode) -> None:
        """Execute a sub-graph node with proper context management.

        This method manages the execution depth and delegates to the SubGraphNode's
        process method, which will call back into this engine for the internal graph.
        """
        self._current_depth += 1
        try:
            logger.debug(
                f"Entering sub-graph '{subgraph_node.name}' at depth {self._current_depth}"
            )
            subgraph_node.process()
            logger.debug(
                f"Exiting sub-graph '{subgraph_node.name}' at depth {self._current_depth}"
            )
        except Exception as e:
            logger.error(
                f"Error in sub-graph '{subgraph_node.name}' at depth {self._current_depth}: {e}"
            )
            raise
        finally:
            self._current_depth -= 1


---
src/edon/graph.py
---
"""Defines the core graph data structure for the Edon node editor.

This module provides the `EntityGraph` class, which serves as the central
representation of the node-based graph. It is responsible for managing the
collection of `EntityNode` instances and their interconnections via `EntitySocket`
objects.

"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, TypeAlias

from edon.errors import GraphObjectErrorReason, SocketLinkErrorReason
from edon.logging import logger
from edon.node import EntityNode
from edon.socket import EntitySocket
from edon.types import SocketAddress, SocketDef, SocketRole, current_execution_engine_context

if TYPE_CHECKING:
    from edon.types import EdgeKey


NodeMap: TypeAlias = MutableMapping[str, EntityNode]


@dataclass
class EntityGraph:
    """
    Represents the data structure for a directed graph of `EntityNode` objects,
    managing their links and providing operations for graph manipulation and
    inspection.

    It primarily consists of `nodes`, a mapping from node IDs to `EntityNode`
    instances, which forms the core storage of the graph's structure, and
    `edges`, a set of `EdgeKey` objects tracking all connections in the graph.
    """

    nodes: NodeMap = field(default_factory=dict)
    edges: set[EdgeKey] = field(default_factory=set)

    def add_node(self, node: EntityNode) -> None:
        """Adds a given `EntityNode` instance to the graph.

        If a node with the same ID already exists, a `ValueError` is raised.
        """
        assert node.id not in self.nodes, (
            f"CORRUPTION: Node with ID '{node.id} already exists in the graph'"
        )

        self.nodes[node.id] = node

    def remove_node(self, node_id: str) -> None:
        """Removes a node, identified by `node_id`, from the graph.

        All links connected to the sockets of the removed node are also unlinked.
        """
        node_to_remove = self.nodes.pop(node_id, None)
        assert node_to_remove is not None, (
            f"CORRUPTION: Node ID {node_id} to remove doesn't exist in the graph"
        )

        # Remove all edges connected to this node's sockets
        edges_to_remove = set()
        for edge in self.edges:
            if edge.source.node_id == node_id or edge.target.node_id == node_id:
                edges_to_remove.add(edge)

        for edge in edges_to_remove:
            self.edges.discard(edge)

        # Let's assert that we don't have any references to the node in our edges left
        for edge in self.edges:
            assert not edge.source.node_id == node_id and not edge.target.node_id == node_id, (
                f"CORRUPTION: Edge {edge} still references remove node {node_id} after cleanup"
            )

    def get_node(self, node_id: str) -> EntityNode:
        return self.nodes[node_id]

    def get_socket_links(self, socket_addr: SocketAddress) -> list[SocketAddress]:
        """Get all socket addresses linked to the given socket."""
        linked_addresses: list[SocketAddress] = []

        for edge in self.edges:
            if edge.source == socket_addr:
                linked_addresses.append(edge.target)
            elif edge.target == socket_addr:
                linked_addresses.append(edge.source)

        return linked_addresses

    def get_source_socket_for_target(
        self, target_socket_address: SocketAddress
    ) -> EntitySocket | None:
        """
        Retrieves the source EntitySocket connected to the given target socket address.
        Assumes a target socket is connected to at most one source socket.
        """
        assert target_socket_address.role == SocketRole.TARGET, (
            f"CORRUPTION: can only be called by socket with target role, not {target_socket_address}"
        )

        linked_source_socket = self.get_socket_links(target_socket_address)
        if not linked_source_socket:
            return None

        source_address = linked_source_socket[0]

        return self.get_node(source_address.node_id).sockets[source_address.name]

    def is_socket_linked(self, socket_addr: SocketAddress) -> bool:
        """Check if socket has any connections."""
        return len(self.get_socket_links(socket_addr)) > 0

    def can_link_sockets_internal(
        self, source_addr: SocketAddress, target_addr: SocketAddress
    ) -> tuple[bool, SocketLinkErrorReason | None]:
        """
        Internal socket validation logic moved from EntitySocket.can_link_to.

        Determines if two sockets can connect based on compatibility rules.
        """
        if source_addr == target_addr:
            return False, SocketLinkErrorReason.CANNOT_LINK_TO_SELF
        if source_addr.role == target_addr.role:
            return False, SocketLinkErrorReason.DIRECTIONS_NOT_OPPOSITE
        if source_addr.node_id == target_addr.node_id:
            return False, SocketLinkErrorReason.SAME_PARENT_NODE
        if source_addr in self.get_socket_links(target_addr):
            return False, SocketLinkErrorReason.ALREADY_LINKED

        source_socket = self.get_node(source_addr.node_id).sockets[source_addr.name]
        target_socket = self.get_node(target_addr.node_id).sockets[target_addr.name]

        # Check for type compatibility, allowing Any or matching/subclass relationships.
        types_are_compatible = False
        if source_socket.data_type == Any or target_socket.data_type == Any:
            types_are_compatible = True
        elif isinstance(source_socket.data_type, type) and isinstance(
            target_socket.data_type, type
        ):
            if issubclass(source_socket.data_type, target_socket.data_type):
                types_are_compatible = True

        if not types_are_compatible:
            return False, SocketLinkErrorReason.TYPE_MISMATCH

        return True, None

    def _is_reachable(self, start_node_id: str, end_node_id: str) -> bool:
        """Determines if a directed path exists from a start node to an end node.

        This method employs a depth-first search (DFS) algorithm, traversing
        the graph by following established links from source sockets to target sockets.
        The search proceeds from the node specified by `start_node_id` towards
        the node specified by `end_node_id`.

        Returns `True` if `end_node_id` is reachable from `start_node_id` following
        the directed edges of the graph, and `False` otherwise.
        """
        visited: set[str] = set()
        # Stack stores node IDs to visit for DFS
        stack: list[str] = [start_node_id]

        while stack:
            current_node_id = stack.pop()

            if current_node_id == end_node_id:
                # Path found from start_node_id to end_node_id.
                # If start_node_id == end_node_id, this means a zero-length path,
                # which is true. In the context of cycle detection, this call
                # is made with start_node_id != end_node_id (target_node.id, source_node.id),
                # because self-links are caught by EntitySocket.can_link_to.
                return True

            if current_node_id in visited:
                continue
            visited.add(current_node_id)

            current_node = self.get_node(current_node_id)
            if not current_node:
                # This can happen if start_node_id or an intermediate node_id is not in the graph.
                continue

            # Explore outgoing edges: from source sockets of current_node
            # to target sockets of neighbor_nodes.
            for source_socket in current_node.source_sockets:
                links = self.get_socket_links(source_socket.address)
                for linked_target_socket in links:
                    # linked_target_socket is a socket on another node.
                    # Its parent node is the neighbor in the graph.
                    neighbor_node = self.get_node(linked_target_socket.node_id)
                    if neighbor_node.id not in visited:
                        stack.append(neighbor_node.id)
                        # Optimization: if neighbor_node.id == end_node_id, could return True here.
                        # However, handling it at the pop() stage is also correct and standard.

        return False

    def _get_socket_and_node(self, socket_addr: SocketAddress) -> tuple[EntitySocket, EntityNode]:
        """Retrieves a socket and its parent node.

        This is an internal helper and assumes the socket_addr is valid and refers
        to an existing node and socket within that node.
        """
        node = self.get_node(socket_addr.node_id)
        assert node, f"CORRUPTION: Private node lookup failed on {socket_addr.node_id}"

        socket = node.sockets[socket_addr.name]
        assert socket, f"CORRUPTION: failed lookup for {SocketAddress}, in {node}"

        return socket, node

    def link_sockets(
        self, edge_key: EdgeKey
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """Establishes a directed link from a source socket to a target socket."""
        source_socket, source_node = self._get_socket_and_node(edge_key.source)
        target_socket, target_node = self._get_socket_and_node(edge_key.target)

        # Check if already linked
        if edge_key in self.edges:
            return False, SocketLinkErrorReason.ALREADY_LINKED

        # Check for cycles
        if self._is_reachable(target_node.id, source_node.id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        # Validate socket compatibility
        socket_compatible, reason = self.can_link_sockets_internal(
            edge_key.source, edge_key.target
        )
        if not socket_compatible:
            return False, reason

        # Add the edge
        self.edges.add(edge_key)
        logger.debug(f"Graph linked sockets: {source_socket.address} -> {target_socket.address}")

        return True, None

    def unlink_sockets(self, edge_key: EdgeKey) -> None:
        """Removes a specific link between a source socket and a target socket."""
        assert edge_key in self.edges, (
            f"CORRUPTION: Can't unlink an edge that doesn't exist, `{edge_key}`"
        )

        self.edges.discard(edge_key)

    def can_form_link(
        self, prospective_source_addr: SocketAddress, prospective_target_addr: SocketAddress
    ) -> tuple[bool, SocketLinkErrorReason | GraphObjectErrorReason | None]:
        """Determines if a new directed edge can be validly formed."""
        source_socket, source_node = self._get_socket_and_node(prospective_source_addr)
        target_socket, target_node = self._get_socket_and_node(prospective_target_addr)

        can_link, reason = self.can_link_sockets_internal(
            source_socket.address, target_socket.address
        )
        if not can_link:
            return False, reason

        # Check for cycles: A cycle is formed if the target node can already reach the source node.
        if self._is_reachable(target_node.id, source_node.id):
            return False, SocketLinkErrorReason.CYCLE_DETECTED

        return True, None

    def partition_valid_link_targets(
        self, source_socket_addr: SocketAddress
    ) -> tuple[set[SocketAddress], set[SocketAddress]]:
        """Determines valid and invalid drop target sockets for the given source socket.

        Returns a tuple of (valid_targets, invalid_targets) where each is a set of SocketAddress.
        """
        valid_targets: set[SocketAddress] = set()
        invalid_targets: set[SocketAddress] = set()

        # Determine the role of the source socket
        source_node = self.get_node(source_socket_addr.node_id)
        source_role = source_socket_addr.role

        # Iterate through all nodes to categorize their sockets
        for node in self.nodes.values():
            same_role_sockets: list[EntitySocket]
            other_role_sockets: list[EntitySocket]
            if source_role == SocketRole.SOURCE:
                same_role_sockets = node.source_sockets
                other_role_sockets = node.target_sockets
            else:
                same_role_sockets = node.target_sockets
                other_role_sockets = node.source_sockets

            # We iterate over each role list, we know that same role sockets will be
            # part of the invalid list as we have the internal rule when role == role
            # the link is not allowed.
            for socket in same_role_sockets:
                invalid_targets.add(socket.address)

            for socket in other_role_sockets:
                # Determine proper source and target for validation
                if source_role == SocketRole.SOURCE:
                    prospective_source_addr = source_socket_addr
                    prospective_target_addr = socket.address
                else:
                    prospective_source_addr = socket.address
                    prospective_target_addr = source_socket_addr

                can_form, _ = self.can_form_link(prospective_source_addr, prospective_target_addr)

                if can_form:
                    valid_targets.add(socket.address)
                else:
                    invalid_targets.add(socket.address)

        return valid_targets, invalid_targets

    def __repr__(self) -> str:
        return f"Graph(nodes_count={len(self.nodes)}, edges_count={len(self.edges)})"


@dataclass
class EntitySubGraphNode(EntityNode):
    """A node that encapsulates an entire EntityGraph.

    This node acts as a regular EntityNode in its parent graph, but internally
    contains a complete graph with its own nodes and connections. External
    sockets on this node are mapped to specific sockets within the internal graph.
    """

    internal_graph: EntityGraph = field(default_factory=EntityGraph)
    _proxy_mappings: dict[str, EntitySocket] = field(default_factory=dict)

    def _get_internal_socket(self, socket_addr: SocketAddress) -> EntitySocket:
        """Get a socket from the internal graph by its address."""
        assert socket_addr.node_id in self.internal_graph.nodes, (
            f"Node '{socket_addr.node_id}' not found in internal graph"
        )

        node = self.internal_graph.get_node(socket_addr.node_id)
        assert socket_addr.name in node.sockets, (
            f"Socket '{socket_addr.name}' not found on node '{socket_addr.node_id}'"
        )

        socket = node.sockets[socket_addr.name]
        assert socket.role == socket_addr.role, (
            f"Socket role mismatch: expected {socket_addr.role}, got {socket.role}"
        )

        return socket

    # def sync_exposed_sockets(self) -> None:
    #     for id_, node in self.internal_graph.nodes.items():
    #         c_sockets = node.sockets.copy()
    #         for name, socket in c_sockets.items():
    #             if not socket.exposed and name in self._proxy_mappings:
    #                 self._remove_proxy_socket(name)
    #             elif socket.exposed:
    #                 self._add_proxy_socket(name, socket.address)

    def add_proxy_socket(self, proxy_name: str, internal_addr: SocketAddress) -> None:
        """Dynamically add a new proxy socket mapping.

        This method allows runtime modification of the sub-graph's external interface
        by exposing additional internal sockets.
        """
        internal_socket = self._get_internal_socket(internal_addr)
        internal_socket.exposed = True

        assert internal_socket.exposed, (
            "CORRUPTION: Can only add 'exposed' sockets, {internal_addr} is not."
        )

        self._proxy_mappings[proxy_name] = internal_socket

        socket_def = SocketDef(
            name=proxy_name,
            socket_type=internal_socket.type_info,
            default=internal_socket.default_value,
            exposed=internal_socket.exposed,
        )
        self._add_socket_internal(socket_def, internal_addr.role)

        logger.debug(f"Added {internal_socket.role} proxy socket '{proxy_name}'")

    def remove_proxy_socket(self, proxy_name: str) -> None:
        del self._proxy_mappings[proxy_name]
        self.sockets.pop(proxy_name)

        logger.debug(f"Removed proxy socket '{proxy_name}'")

    def _propagate_sockets(self, role: SocketRole) -> None:
        for proxy_name, internal_socket in self._proxy_mappings.items():
            if not internal_socket.role == role:
                continue

            internal_socket.value = self.sockets[proxy_name].value
            logger.trace(f"Propagated: {proxy_name} -> {internal_socket.address}")

    def process(self) -> None:
        logger.debug(f"Processing SubGraphNode '{self.name}'")

        self._propagate_sockets(SocketRole.TARGET)

        active_engine = current_execution_engine_context.get()
        assert active_engine is not None, (
            "SubGraphNode.process() called without an active ExecutionEngine context"
        )

        # The active_engine is already managing depth, so it will increment it
        # when it calls execute_graph recursively.
        active_engine.execute_graph(self.internal_graph, context=f"sub-graph: {self.name}")

        # After we are done processing the graph we propagate the resulting values to the proxy
        # sockets to make available to the outer graph.
        self._propagate_sockets(SocketRole.SOURCE)

        logger.debug(f"Completed processing SubGraphNode '{self.name}'")


---
src/edon/logging.py
---
import os
import sys
from datetime import datetime
from types import TracebackType

from loguru import logger
from PySide6.QtCore import QCoreApplication  # Important for Qt app exit


# This will be our global excepthook
def an_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """
    Global excepthook that logs all unhandled exceptions using Loguru
    and then terminates the application.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Respect KeyboardInterrupt and let the default handler deal with it
        # which typically involves a clean exit.
        logger.warning("KeyboardInterrupt received. Exiting...")
        logger.complete()  # Flush logs before default handler takes over
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Log the critical error using Loguru, which will include the traceback
    logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical(
        f"CRITICAL UNHANDLED EXCEPTION ({exc_type.__name__}). Application will terminate."
    )

    # Ensure all logs are flushed before attempting to exit
    # Loguru's critical messages might flush, but being explicit is safer.
    logger.complete()

    # For Qt applications, it's often best to ask the QCoreApplication to exit first
    app = QCoreApplication.instance()
    if app:
        logger.info("Requesting QCoreApplication to exit due to unhandled exception.")
        # app.exit(1) # This signals the event loop to terminate.
        # However, sys.exit(1) below is more forceful and immediate
        # if we're in an excepthook.
        # If you experience issues with Qt cleanup, you might reinstate app.exit()
        # and potentially add a small delay or a more complex shutdown sequence.
        # For now, direct sys.exit after logging is often most reliable for tracebacks.
        pass  # Often, sys.exit is enough and more direct from an excepthook.

    # Forcefully exit the application.
    # This is crucial: if the excepthook returns, Python might consider the exception handled.
    sys.exit(1)  # Use a non-zero exit code to indicate an error.


def setup_logging(log_level: str = "INFO", enable_file_logging: bool = False) -> None:
    """
    Set up Loguru logging for the application.
    """
    logger.remove()  # Remove default handlers

    if enable_file_logging:
        logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        logs_dir = os.environ.get("EDON_LOGS_DIR", logs_dir)
        os.makedirs(logs_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = os.path.join(logs_dir, f"edon-{timestamp}.log")

        logger.add(
            log_file,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            backtrace=True,  # Essential for exceptions
            diagnose=True,  # Useful for variable values in tracebacks
            enqueue=True,  # Make file logging asynchronous and process-safe
        )
        logger.info(f"File logging initialized. Log file: {log_file}")

    # Console handler
    logger.add(
        sys.stderr,  # Log to stderr by convention for errors/diagnostics
        level=log_level,
        format="<level>{level: <8}</level> | <green>{name}</green>:<yellow>{function}</yellow>:<blue>{line}</blue> - <level>{message}</level>",
        colorize=True,
        backtrace=True,  # Ensure console also gets tracebacks for logged exceptions
        diagnose=True,
    )

    logger.info(f"Console logging initialized at level {log_level}.")

    # Set the global exception hook
    # The @logger.catch on an_exception_handler is not strictly necessary
    # if the handler itself is robust, but can catch errors within the handler.
    # For simplicity here, we'll make the handler robust.
    # If you want to use @logger.catch on the excepthook itself:
    # @logger.catch(onerror=lambda _: sys.exit(2)) # Exit with 2 if excepthook itself fails
    # def an_exception_handler_decorated(...): ...
    # sys.excepthook = an_exception_handler_decorated
    sys.excepthook = an_exception_handler
    logger.info("Global exception handler (sys.excepthook) configured.")


---
src/edon/node.py
---
"""Defines the core `EntityNode` class andrelated structures for the Edon graph.

This module provides the `EntityNode`, which is the base representation for all
nodes within the `EntityGraph`. Nodes are the primary computational units and
data containers in the graph. They manage their input and output sockets
(`EntitySocket` instances) and encapsulate specific processing logic.

The design facilitates a declarative approach for creating custom node types:
users can subclass `EntityNode` and define class-level attributes for `name`,
`node_type`, and lists of `SocketDef` objects to specify `source_socket_definitions`
and `target_socket_definitions`. The `EntityNode`'s `__post_init__` method
handles the instantiation of these sockets.

"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

from edon.socket import EntitySocket, SocketRole

if TYPE_CHECKING:
    from edon.types import SocketDef


@dataclass
class EntityNode:
    """
    Represents a single node in the node editor graph. Nodes manage their input and output sockets
    and define core processing logic.

    Subclasses can be defined declaratively by setting class attributes:
    """

    # --- Instance Attributes (can be passed via __init__ generated by @dataclass) ---
    # These allow overriding class attributes or direct instantiation without subclassing.
    name: str | None = field(default=None)
    node_type: str | None = field(default=None)

    # Socket definitions default to `None` at the instance level.
    # This allows `__post_init__` to distinguish between "not provided" (use class attr)
    # and "provided as empty list []" (use the empty list).
    source_socket_definitions: list[SocketDef] | None = field(default=None)
    target_socket_definitions: list[SocketDef] | None = field(default=None)

    # --- Internal Attributes ---
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sockets: dict[str, EntitySocket] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        cls: type[Self] = self.__class__

        # Resolve 'name': Instance > Class > Derived (for subclasses) > None
        if self.name is None:
            self.name = getattr(cls, "name", None)
            if self.name is None and cls is not EntityNode:
                self.name = cls.__name__.replace("Node", "")

        # Resolve 'node_type': Instance > Class > Derived (for subclasses) > None
        if self.node_type is None:
            self.node_type = getattr(cls, "node_type", None)
            if self.node_type is None and cls is not EntityNode:
                self.node_type = cls.__name__.lower().replace("Node", "")

        # Resolve 'source_socket_definitions': Instance > Class > Default []
        source_definitions: list[SocketDef]
        if self.source_socket_definitions is not None:
            source_definitions = self.source_socket_definitions
        else:
            class_s_defs = getattr(cls, "source_socket_definitions", None)
            source_definitions = class_s_defs if class_s_defs is not None else []

        # Resolve 'target_socket_definitions': Instance > Class > Default []
        target_definitions: list[SocketDef]
        if self.target_socket_definitions is not None:
            target_definitions = self.target_socket_definitions
        else:
            class_t_defs = getattr(cls, "target_socket_definitions", None)
            target_definitions = class_t_defs if class_t_defs is not None else []

        # Create sockets using the resolved definitions
        for sock_def in target_definitions:
            self._add_socket_internal(sock_def, SocketRole.TARGET)
        for sock_def in source_definitions:
            self._add_socket_internal(sock_def, SocketRole.SOURCE)

    def _add_socket_internal(
        self,
        socket_def: SocketDef,
        role: SocketRole,
    ) -> None:
        """
        Internal method to create and add a socket to the node.

        The `parent_node` for the socket is automatically set to this node instance.
        """
        if socket_def.name in self.sockets:
            raise ValueError(
                f"Socket with name '{socket_def.name}' already exists on node '{self.name}'."
            )

        socket_instance: EntitySocket = EntitySocket(
            name=socket_def.name,
            role=role,
            node=self,
            exposed=socket_def.exposed,
            type_info=socket_def.socket_type,
            default_value=socket_def.default,
        )

        self.sockets[socket_def.name] = socket_instance

    @property
    def source_sockets(self) -> list[EntitySocket]:
        return [sock for sock in self.sockets.values() if sock.role == SocketRole.SOURCE]

    @property
    def target_sockets(self) -> list[EntitySocket]:
        return [sock for sock in self.sockets.values() if sock.role == SocketRole.TARGET]

    def process(self) -> None:
        """
        The core computational logic of the node. Returns None.

        This method MUST be overridden by subclasses to define the node's behavior.
        It is called by the `ExecutionEngine` when the node is ready to be processed.

        Subclasses should typically:
        1. Access input sockets via `self.source_sockets['socket_name']`.
        2. Get input values:
           - Check `socket.is_connected()`.
           - If connected, access the value from the connected output socket,
             typically via `socket.connections[0].value`. The `ExecutionEngine`
             ensures upstream nodes are processed first.
           - If not connected, use the input socket's own `socket.value` as a
             default or based on node logic.
           - Ensure operations respect the `data_type` of the socket.
        3. Compute results based on these input values and the node's purpose.
        4. Set output values directly on output sockets:
           `self.target_sockets['socket_name'].value = result_value`.
           - Ensure the `result_value` is compatible with the output socket's `data_type`.

        The method signature is `-> None` because data is read from and written
        to the node's own `EntitySocket` instances. These sockets handle data type
        management and connection compatibility. The `process` method orchestrates
        the node's internal data transformation and state changes.
        """
        raise NotImplementedError(
            f"Node class '{self.__class__.__name__}' must implement the process() method."
        )

    def __repr__(self) -> str:
        return (
            f"Node(name='{self.name}', type='{self.node_type}', id='{self.id}', "
            f"sources={[sock.name for sock in self.source_sockets]}, "
            f"targets={[sock.name for sock in self.target_sockets]})"
        )


---
src/edon/socket.py
---
"""Defines the `EntitySocket` class, representing connection points on nodes.

This module provides `EntitySocket`, the core component for defining data input
and output points on `EntityNode` instances within the `EntityGraph`. Sockets
are responsible for managing their data type, current value, and connections
to other sockets.

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from edon.types import SocketAddress, SocketRole, SocketType, current_graph_context

if TYPE_CHECKING:
    from edon.node import EntityNode


@dataclass
class EntitySocket:
    """
    Pure data representation of a socket connection point on a Node.

    This class only holds data and computed properties. All connection
    management and validation logic is handled by EntityGraph.
    """

    name: str
    role: SocketRole
    node: EntityNode
    type_info: SocketType
    exposed: bool
    default_value: Any | None = None
    _value: Any | None = field(init=False)

    def __post_init__(self) -> None:
        self._value = self.default_value

    @property
    def data_type(self) -> type[Any]:
        """The Python data type this socket handles, for connection compatibility."""
        return self.type_info.python_type

    @property
    def address(self) -> SocketAddress:
        """Computed socket address for this socket."""
        return SocketAddress(self.node.id, self.name, self.role)

    @property
    def value(self) -> Any:
        # SOURCE sockets are the one we are pulling from, we are not pushing.
        if self.role == SocketRole.SOURCE:
            return self._value

        # Without a proper graph context set we can't figure out our links, a socket
        # needs this context to find it's partner.
        active_graph = current_graph_context.get()
        if active_graph:
            # If we don't find a link here, it just means that the socket doesn't have any
            # links, and we can return the default value, if set.
            source_socket = active_graph.get_source_socket_for_target(self.address)
            if source_socket is not None:
                return source_socket._value

        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        self._value = value

    def __repr__(self) -> str:
        parent_node_repr = self.node.name
        data_type_repr = self.data_type.__name__ if self.data_type != Any else "Any"
        if not isinstance(self.data_type, type) and self.data_type is not Any:
            data_type_repr = str(self.data_type)

        return (
            f"Socket(name='{self.name}', direction={self.role.name}, "
            f"data_type={data_type_repr}, parent_node='{parent_node_repr}')"
        )


---
src/edon/types.py
---
from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Protocol
from dataclasses import dataclass
from enum import Enum, auto

if TYPE_CHECKING:
    from edon.graph import EntityGraph
    from edon.executor import ExecutionEngine

current_graph_context: ContextVar[EntityGraph | None] = ContextVar(
    "current_graph_context", default=None
)
current_execution_engine_context: ContextVar[ExecutionEngine | None] = ContextVar(
    "current_execution_engine_context", default=None
)


class SocketRole(Enum):
    """Defines the direction of a socket, either Input or Output."""

    SOURCE = 1
    TARGET = 2


@dataclass(frozen=True, order=True)
class SocketAddress:
    """Represents a unique socket endpoint within the graph, identifying an entity socket.

    It is defined by `node_id`, the unique identifier of its parent node, and
    `socket_name`, the name of the socket on that node.
    """

    node_id: str
    name: str
    role: SocketRole


class SocketType(Enum):
    """
    Defines the comprehensive type of a socket, including its underlying
    Python data type and a key for its visual/widget representation.

    The enum member itself serves as the primary key for widget factories.
    The `value` tuple stores (python_data_type, description)
    """

    ANY = (object, "any")
    INTEGER = (int, "integer")
    FLOAT = (float, "float")
    STRING = (str, "string")
    LARGE_STRING = (str, "large_string")

    @property
    def python_type(self) -> type:
        """The underlying Python data type for this socket type (e.g., int, str)."""
        return self.value[0]

    @property
    def description(self) -> str:
        """A simple tag for debugging or logging, not typically used as a key."""
        return self.value[1]

    def __str__(self) -> str:
        return f"{self.name} (Python: {self.python_type.__name__})"


class SocketDisplayState(Enum):
    ALL = auto()
    LINK = auto()
    LINK_LABEL = auto()
    LINK_WIDGET = auto()
    LABEL = auto()
    WIDGET = auto()


@dataclass
class SocketDef:
    """
    Defines the specification for a socket to be created on a node.
    This is used during node initialization.
    """

    name: str
    socket_type: SocketType
    default: Any = None
    exposed: bool = False
    display_state: SocketDisplayState = SocketDisplayState.LINK_LABEL

    @property
    def python_type(self) -> type[Any]:
        """Convenience property to access the Python data type."""
        return self.socket_type.python_type

    @property
    def visual_key_for_widget_factory(self) -> SocketType:
        """Convenience property; the enum member itself is the key."""
        return self.socket_type

    def __repr__(self):
        return (
            f"SocketDef(name='{self.name}', socket_type='{self.socket_type.name}', "
            f"python_type={self.python_type.__name__}, "
            f"display_state={self.display_state.name}, default={self.default!r})"
        )


@dataclass(frozen=True)
class EdgeKey:
    """Uniquely identifies an edge by its source and target socket addresses.

    It is defined by its `source` and `target` `SocketAddress` instances,
    representing the two endpoints of the connection.
    """

    source: SocketAddress
    target: SocketAddress


class ProcessableNode(Protocol):
    """A protocol for nodes that define a core processing logic.

    This protocol ensures that conforming objects (typically `EntityNode` subclasses)
    implement a `process` method, which is called by the execution engine
    to perform the node's primary computation or action.
    """

    def process(self) -> None:
        """
        The core computational logic of the node. Returns None.

        This method is intended to be overridden by concrete node implementations
        to define their specific behavior. It typically involves:
        1. Accessing input sockets via `self.source_sockets`.
        2. Retrieving input values (respecting their `data_type` as defined by
           the node's `SocketDef`s).
        3. Performing computations.
        4. Setting output values on `self.target_sockets` (again, respecting
           their `data_type`).

        The method signature is `-> None` because data is read from and written
        to the node's own `EntitySocket` instances, which manage type compatibility
        at the connection level. The `process` method itself orchestrates this
        internal data flow based on the node's defined socket types.
        """
        ...


---
src/edon/nodes/utility.py
---
"""Defines utility nodes for the Edon graph system.

Utility nodes are special-purpose nodes that assist in graph management,
UI interactions, or other non-data-processing tasks.
"""

from __future__ import annotations

from edon.node import EntityNode
from edon.types import SocketDef, SocketDisplayState
from edon_ui.widgets.factories import SocketType


class SubgraphPromoterNode(EntityNode):
    """
    A utility node used within a graphs editing view to expose internal sockets
    to the parent SubGraphNode's interface.

    When a user drags an edge from an internal node's socket and drops it onto
    one of this node's special sockets, it signals an intent to create a
    corresponding proxy socket on the containing SubGraphNode.
    """

    node_type = "utility.subgraph.promoter"

    target_socket_definitions = [
        SocketDef(
            name="trg_promoter",
            socket_type=SocketType.ANY,
            display_state=SocketDisplayState.LINK_LABEL,
        ),
    ]

    source_socket_definitions = [
        SocketDef(
            name="src_promoter",
            socket_type=SocketType.ANY,
            display_state=SocketDisplayState.LINK_LABEL,
        ),
    ]


---
