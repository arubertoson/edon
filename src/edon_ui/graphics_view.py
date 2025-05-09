from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView

from .context_menu import AppContextMenu


class GraphicsView(QGraphicsView):
    RIGHT_CLICK_MOVE_THRESHOLD = 5  # Pixels to move before considering it a drag for window move

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        # View settings
        self.setRenderHint(QPainter.Antialiasing)  # Enable smooth rendering of lines and shapes
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)  # Zoom centers on mouse cursor
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)  # Keep content centered when resizing window
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Hide scrollbars since we use pan/zoom
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Hide scrollbars since we use pan/zoom
        # Set RubberBandDrag as the default when interactions are enabled
        # This will be overridden by _update_view_behavior if scene is empty
        # RubberBandDrag lets users click and drag to draw a selection rectangle
        # that selects multiple items in the scene
        self.setDragMode(QGraphicsView.RubberBandDrag)

        # Zoom and pan state
        self._pan_active = False
        self._last_pan_pos = None
        self._zoom_factor = 1.1

        # Right-click handling
        self._right_click_pos = None
        self._right_click_moved = False

        self._interaction_enabled = True
        self._update_view_behavior()

        if self.scene() and hasattr(self.scene(), 'scene_changed'):
            self.scene().scene_changed.connect(self._update_view_behavior)

    def _update_view_behavior(self):
        current_scene = self.scene()

        has_nodes = False
        if current_scene and hasattr(current_scene, "node_items"):
            has_nodes = bool(current_scene.node_items)

        if not has_nodes:
            self._interaction_enabled = False
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            self._interaction_enabled = True
            self.setDragMode(QGraphicsView.RubberBandDrag)

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
        min_padding = 200.0 # Minimum padding
        padding_w = max(min_padding, padding_w)
        padding_h = max(min_padding, padding_h)

        # Create a new rect based on the view's visible area plus padding
        padded_visible_rect = visible_rect_in_scene_coords.adjusted(-padding_w, -padding_h, padding_w, padding_h)

        # Unite the current sceneRect with the padded visible rect to ensure the scene boundaries
        # encompass both the existing scene area and the newly visible area.
        new_scene_rect = current_s_rect.united(padded_visible_rect)

        if new_scene_rect != current_s_rect:
            current_scene.setSceneRect(new_scene_rect)

    def wheelEvent(self, event):
        if not self._interaction_enabled:
            event.ignore()
            return

        zoom_in = event.angleDelta().y() > 0
        zoom_factor_val = self._zoom_factor if zoom_in else (1 / self._zoom_factor)

        self.scale(zoom_factor_val, zoom_factor_val)
        self._request_scene_rect_adjustment()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if not self._interaction_enabled:
                event.ignore()
                return

            self._pan_active = True
            self._last_pan_pos = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.RightButton:
            self._right_click_pos = event.globalPosition().toPoint()
            self._right_click_moved = False
            event.accept()
        else:
            if not self._interaction_enabled:
                event.ignore()
                return
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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
        elif self._right_click_pos and event.buttons() & Qt.RightButton:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self._right_click_pos
            # If mouse has moved beyond threshold and we haven't started moving window yet,
            # initiate window drag operation to allow moving window by right-click dragging
            if (
                abs(delta.x()) > self.RIGHT_CLICK_MOVE_THRESHOLD or abs(delta.y()) > self.RIGHT_CLICK_MOVE_THRESHOLD
            ) and not self._right_click_moved:
                self._right_click_moved = True
                if self.window() and self.window().windowHandle():  # Check if window and handle exist
                    self.window().windowHandle().startSystemMove()
            event.accept()

        elif event.buttons() & Qt.LeftButton and self._interaction_enabled:
            super().mouseMoveEvent(event)

        elif not self._interaction_enabled:
            event.ignore()

        else:
            super().mouseMoveEvent(event)  # Catch-all for other unhandled GView events

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if self._pan_active:
                self._pan_active = False
                self._last_pan_pos = None
                self.setCursor(Qt.ArrowCursor)
                event.accept()
            # else:
            #     super().mouseReleaseEvent(event) # This was causing issues with context menu

        elif event.button() == Qt.RightButton:
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

    def scene_content_changed(self):
        """Public method that can be called if scene changes state externally"""
        self._update_view_behavior()

    def _handle_request_add_new_node(self, global_pos: QPoint):
        """Handles the request from the context menu to add a new node."""
        if not self.scene():
            return

        # Map the global mouse position to view coordinates, then to scene coordinates
        view_pos = self.mapFromGlobal(global_pos)
        scene_pos = self.mapToScene(view_pos)

        # Delegate node creation to the scene
        # This will trigger GraphicsScene.addItem -> _update_scene_appearance -> node_presence_changed signal
        # which in turn calls self._update_view_behavior via the connection.
        self.scene().add_new_node_at(scene_pos)
        # self.scene_content_changed() # This call is now redundant due to the signal/slot mechanism
