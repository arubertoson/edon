from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from loguru import logger
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QInputEvent, QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsView, QApplication, QLineEdit, QTextEdit, QPlainTextEdit, QGraphicsProxyWidget

from ..context_menu import AppContextMenu

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsItem, QMainWindow

    from edon.graph import EntityGraph
    from edon_ui.commands.key_processor import KeyProcessor
    from edon_ui.graph_controller import GraphController
    from edon_ui.graphics.scene import GraphicsScene


@dataclass
class EditorContext:
    view: "GraphicsView"
    scene: "GraphicsScene"
    window: "QMainWindow"
    manager: "GraphController"
    entity_graph: "EntityGraph"
    selected_items: list["QGraphicsItem"]
    event: QInputEvent | None = None
    params: dict[str, Any] = field(default_factory=dict)


class GraphicsView(QGraphicsView):
    RIGHT_CLICK_MOVE_THRESHOLD = 5

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        logger.info(f"GraphicsView initialized with scene: {scene}")

        self.key_processor: "KeyProcessor | None" = None

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

        self._update_view_behavior()
        if self.scene() and hasattr(self.scene(), "scene_changed"):
            self.scene().scene_changed.connect(self._update_view_behavior)

    def _update_view_behavior(self):
        current_scene = self.scene()
        if QApplication.mouseButtons() != Qt.MouseButton.NoButton:
            if not current_scene or not hasattr(current_scene, "node_items") or not current_scene.node_items:
                self._interaction_enabled = False
            else:
                self._interaction_enabled = True
            return
        if not current_scene or not hasattr(current_scene, "node_items") or not current_scene.node_items:
            self._interaction_enabled = False
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.resetTransform()
            if current_scene and hasattr(current_scene, "empty_scene_text"):
                self.centerOn(current_scene.empty_scene_text)
        else:
            self._interaction_enabled = True
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

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
        padded_visible_rect = visible_rect_in_scene_coords.adjusted(-padding_w, -padding_h, padding_w, padding_h)

        # Unite the current sceneRect with the padded visible rect to ensure the scene boundaries
        # encompass both the existing scene area and the newly visible area.
        new_scene_rect = current_s_rect.united(padded_visible_rect)

        # Only update the sceneRect if it has actually changed to avoid unnecessary redraws.
        if new_scene_rect != current_s_rect:
            current_scene.setSceneRect(new_scene_rect)

    def scene_content_changed(self):
        self._update_view_behavior()

    def provide_context(self, event: QInputEvent | None = None) -> EditorContext:
        return EditorContext(
            view=self,
            scene=self.scene(),
            window=self.window(),
            manager=self.scene().controller,
            entity_graph=self.scene().controller.entity_graph,
            selected_items=self.scene().selectedItems(),
            event=event,
            params={},
        )

    def wheelEvent(self, event: QWheelEvent):
        if not self._interaction_enabled:
            event.ignore()
            return
        zoom_in = event.angleDelta().y() > 0
        zoom_factor_val = self._zoom_factor if zoom_in else (1 / self._zoom_factor)
        self.scale(zoom_factor_val, zoom_factor_val)
        self._request_scene_rect_adjustment()

    def _route_key_event(self, event: QKeyEvent) -> None:
        event_type_str = "KeyPress" if event.type() == QEvent.Type.KeyPress else "KeyRelease"
        scene_focus_item = self.scene().focusItem() if self.scene() else None

        logger.trace(f"GV.{event_type_str}: key={event.key()}, text='{event.text()}'. SceneFocus: {scene_focus_item}")

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
        # In both cases, after delegating to the base implementation, we return to prevent further processing.
        # This structure keeps the event routing logic clear and maintainable.
        if isinstance(scene_focus_item, QGraphicsProxyWidget):
            logger.debug(f"GV.{event_type_str}: Scene-focused proxy widget ({scene_focus_item}) processing.")
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

    def mousePressEvent(self, event: QMouseEvent):
        scene_item_under_mouse = self.itemAt(event.pos())
        logger.trace(
            f"GV.mousePress: btn={event.button()}, pos={event.pos()}. ItemUnderMouse: {scene_item_under_mouse}. "
            f"AppFocus: {QApplication.focusWidget()}, SceneFocus: {self.scene().focusItem() if self.scene() else None}"
        )

        # XXX: This should also be a command.
        main_window = self.window()
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
            if not self._interaction_enabled:
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
            logger.trace("  Right mouse: Initiating context menu/move sequence.")
            self._right_click_pos = event.globalPosition().toPoint()
            self._right_click_moved = False
            event.accept()
            return

        if not self._interaction_enabled:
            logger.trace("  Interaction disabled, ignoring further mouse press processing.")
            event.ignore()
            return

        logger.trace("  GV.mousePress: Passing to super() for item interaction / rubber band.")
        super().mousePressEvent(event)
        logger.trace(
            f"  GV.mousePress: After super(), event.accepted={event.isAccepted()}, AppFocus: {QApplication.focusWidget()}, SceneFocus: {self.scene().focusItem() if self.scene() else None}"
        )

        if not event.isAccepted():
            if self.key_processor and self.key_processor._process_event_for_command_sequence(event, self):
                logger.debug("  GV.mousePress: Event accepted by key_processor.")
                event.accept()
            else:
                logger.trace("  GV.mousePress: Event not accepted by key_processor.")
        else:
            logger.trace("  GV.mousePress: Event already accepted before key_processor check.")

    def mouseReleaseEvent(self, event: QMouseEvent):
        logger.trace(f"GV.mouseRelease: btn={event.button()}, pos={event.pos()}")

        # Priority 1: Specific view actions for button releases
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
                menu = AppContextMenu(self, position=event.globalPos(), main_window=self.window(), view=self)
                menu.exec(event.globalPos())
            else:
                logger.trace("  Right mouse release (dragged or no initial pos): Resetting state.")
            self._right_click_pos = None
            self._right_click_moved = False
            event.accept()
            return  # Crucial: If right or middle button was handled, we return.

        # Priority 2: Interaction enabled check for further processing
        if not self._interaction_enabled:
            logger.trace("  Interaction disabled, ignoring further mouse release processing.")
            event.ignore()
            return

        # Priority 3: Pass to QGraphicsItems via super().mouseReleaseEvent()
        logger.trace("  GV.mouseRelease: Passing to super() for item processing.")
        super().mouseReleaseEvent(event)
        logger.trace(f"  GV.mouseRelease: After super(), event.accepted={event.isAccepted()}")

        # Priority 4: Key processor (if event not already accepted by items/view actions)
        if not event.isAccepted():
            if self.key_processor and self.key_processor._process_event_for_command_sequence(event, self):
                logger.debug("  GV.mouseRelease: Event accepted by key_processor.")
                event.accept()
            else:
                logger.trace("  GV.mouseRelease: Event not accepted by key_processor.")
        else:
            logger.trace("  GV.mouseRelease: Event already accepted before key_processor check.")

    def mouseMoveEvent(self, event: QMouseEvent):
        # Panning logic (middle mouse drag)
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
                abs(delta.x()) > self.RIGHT_CLICK_MOVE_THRESHOLD or abs(delta.y()) > self.RIGHT_CLICK_MOVE_THRESHOLD
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
