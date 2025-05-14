from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QInputEvent, QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsView

from ..context_menu import AppContextMenu

if TYPE_CHECKING:
    from PySide6.QtWidgets import QGraphicsItem, QMainWindow

    from edon.graph import EntityGraph
    from edon_ui.commands.key_processor import KeyProcessor  # For type hint
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
    RIGHT_CLICK_MOVE_THRESHOLD = 5  # Pixels to move before considering it a drag for window move

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        # Add attributes for the new command system
        self.key_processor: "KeyProcessor | None" = None
        # GraphicsView itself will be the context_provider passed to KeyProcessor in main.py
        # So, when KeyProcessor calls context_provider.provide_context, it calls this view's method.

        # View settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)  # Enable smooth rendering of lines and shapes
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)  # Zoom centers on mouse cursor
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )  # Keep content centered when resizing window
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # Hide scrollbars since we use pan/zoom
        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )  # Hide scrollbars since we use pan/zoom
        # Set RubberBandDrag as the default when interactions are enabled
        # This will be overridden by _update_view_behavior if scene is empty
        # RubberBandDrag lets users click and drag to draw a selection rectangle
        # that selects multiple items in the scene
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # Zoom and pan state
        self._pan_active = False
        self._last_pan_pos = None
        self._zoom_factor = 1.1

        # Right-click handling
        self._right_click_pos = None
        self._right_click_moved = False

        self._interaction_enabled = True
        self._update_view_behavior()

        if self.scene() and hasattr(self.scene(), "scene_changed"):
            self.scene().scene_changed.connect(self._update_view_behavior)

    def _update_view_behavior(self):
        current_scene = self.scene()
        if not current_scene or not hasattr(current_scene, "node_items") or not current_scene.node_items:  # Defensive
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
        # Clamp padding to a reasonable min/max if necessary
        min_padding = 200.0  # Minimum padding
        padding_w = max(min_padding, padding_w)
        padding_h = max(min_padding, padding_h)

        # Create a new rect based on the view's visible area plus padding
        padded_visible_rect = visible_rect_in_scene_coords.adjusted(-padding_w, -padding_h, padding_w, padding_h)

        # Unite the current sceneRect with the padded visible rect to ensure the scene boundaries
        # encompass both the existing scene area and the newly visible area.
        new_scene_rect = current_s_rect.united(padded_visible_rect)

        if new_scene_rect != current_s_rect:
            current_scene.setSceneRect(new_scene_rect)

    def scene_content_changed(self):
        """Public method that can be called if scene changes state externally"""
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

    def mousePressEvent(self, event: QMouseEvent):
        # Try command system first
        if self.key_processor and self:  # 'self' is the ContextProvider
            handled_by_command = self.key_processor.process_input_event(event, self)
            if handled_by_command:
                event.accept()
                return

        if event.button() == Qt.MouseButton.LeftButton:
            main_window = self.window()
            if main_window and hasattr(main_window, "is_position_on_resize_edge"):
                if main_window.is_position_on_resize_edge(event.globalPosition()):
                    super().mousePressEvent(event)
                    return

        if event.button() == Qt.MouseButton.MiddleButton:
            if not self._interaction_enabled:
                event.ignore()
                return
            self._pan_active = True
            self._last_pan_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._right_click_pos = event.globalPosition().toPoint()
            self._right_click_moved = False
            event.accept()
        else:
            if not self._interaction_enabled:
                event.ignore()
                return
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._pan_active and self._last_pan_pos:
            if not self._interaction_enabled:
                return

            # In the case of panning, we need to calculate the delta between the current and last pan positions
            # and then update the scroll bars with the delta, which will move the viewport in the opposite direction
            # of the mouse movement.
            current_pos = event.position().toPoint()
            delta = current_pos - self._last_pan_pos
            self._last_pan_pos = current_pos

            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())

            self._request_scene_rect_adjustment()
            event.accept()
        elif self._right_click_pos and event.buttons() & Qt.MouseButton.RightButton:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self._right_click_pos
            # If mouse has moved beyond threshold and we haven't started moving window yet,
            # initiate window drag operation to allow moving window by right-click dragging
            if (
                abs(delta.x()) > self.RIGHT_CLICK_MOVE_THRESHOLD or abs(delta.y()) > self.RIGHT_CLICK_MOVE_THRESHOLD
            ) and not self._right_click_moved:
                self._right_click_moved = True
                if self.window() and self.window().windowHandle():
                    self.window().windowHandle().startSystemMove()  # type: ignore
            event.accept()

        elif event.buttons() & Qt.MouseButton.LeftButton and self._interaction_enabled:
            super().mouseMoveEvent(event)

        elif not self._interaction_enabled:
            event.ignore()

        else:
            super().mouseMoveEvent(event)  # Catch-all for other unhandled GView events

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.MiddleButton:
            if self._pan_active:
                self._pan_active = False
                self._last_pan_pos = None
                self.setCursor(Qt.CursorShape.ArrowCursor)
                event.accept()

        elif event.button() == Qt.MouseButton.RightButton:
            if self._right_click_pos and not self._right_click_moved:
                # NOTE: This is a hack to get the context menu to work when the right button is released
                # This is because the right button is used to move the window, and we need to show the context menu
                # when the right button is released.
                menu = AppContextMenu(self, position=event.globalPos(), main_window=self.window(), view=self)
                menu.exec(event.globalPos())

            self._right_click_pos = None
            self._right_click_moved = False
            event.accept()
        else:
            if not self._interaction_enabled:
                event.ignore()
                return
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        # Try command system first
        if self.key_processor and self:  # 'self' is the ContextProvider
            handled_by_command = self.key_processor.process_input_event(event, self)
            if handled_by_command:
                event.accept()
                return

        super().keyPressEvent(event)
