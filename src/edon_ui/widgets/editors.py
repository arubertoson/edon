"""Specialized QWidget subclasses for editing socket values."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

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
    title: str

    def get_value(self) -> Any: ...
    def set_value(self, value: Any) -> None: ...


class ProxyAttributeMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
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
        content: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.scene: QGraphicsScene | None = scene
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

    def _position_title_bar_elements(self) -> None:
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
        self.accepted.emit()
        self.close()

    def reject(self) -> None:
        self.rejected.emit()
        self.close()

    def _on_accept(self) -> None:
        self.accept()

    def _on_reject(self) -> None:
        self.reject()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
        elif (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.accept()
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
        return cast(Any, super()).event(event)

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
        widget_factory: Callable[[], QWidget],
        icon_name: str = "fa5s.expand",
        parent: QWidget | None = None,
    ) -> None:
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
        parent_widget = self.parentWidget()
        if scene is None and parent_widget is not None:
            scene_getter = getattr(parent_widget, "scene", None)
            if callable(scene_getter):
                scene = scene_getter()

        if not isinstance(scene, QGraphicsScene):
            scene = None
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
        assert isinstance(widget, ValueWidget), (
            "widget_factory must return a QWidget implementing ValueWidget"
        )
        widget.set_value(self.value)

        dialog = CustomDialogWidget(
            parent=window,
            scene=scene,  # scene can be None
            title=widget.title,
            content=widget,
        )

        def _clear_focus() -> None:
            logger.trace(f"ExpandLineEdit: Clearing focus on its proxy {self.proxy}")
            self.clearFocus()
            self.proxy.clearFocus()

        def _update_value() -> None:
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

        icon_rect = QRect((rect.width() // 2) - 2, rect.y(), rect.width(), rect.height())
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
    widget: QWidget,
    screen_geometry: QRect,
    width_ratio: float = 0.5,
    height_ratio: float = 0.5,
) -> None:
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
