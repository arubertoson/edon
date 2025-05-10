from PySide6.QtCore import QPoint, Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QKeyEvent, QMouseEvent, QCursor
from PySide6.QtWidgets import QGraphicsView
from typing import Any

from .context_menu import AppContextMenu


class GraphicsView(QGraphicsView):
    # Signal emitted when the user requests to add a new node.
    # Arguments:
    #   - QPointF: The desired position in scene coordinates.
    #   - str: A hint for the type of node to create (e.g., "default", "math_add").
    new_node_requested_at_scene_pos = Signal(QPointF, str)
    node_deletion_requested = Signal(list)  # List of node_entity_id strings
    edge_deletion_requested = Signal(list)  # List of EdgeItem instances

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

        if self.scene() and hasattr(self.scene(), "scene_changed"):
            self.scene().scene_changed.connect(self._update_view_behavior)

    def _update_view_behavior(self):
        current_scene = self.scene()
        if not current_scene.node_items:
            self._interaction_enabled = False
            self.setDragMode(QGraphicsView.NoDrag)
            self.resetTransform()
            if current_scene and hasattr(current_scene, "empty_scene_text"):
                self.centerOn(current_scene.empty_scene_text)
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

    def wheelEvent(self, event):
        if not self._interaction_enabled:
            event.ignore()
            return

        zoom_in = event.angleDelta().y() > 0
        zoom_factor_val = self._zoom_factor if zoom_in else (1 / self._zoom_factor)

        self.scale(zoom_factor_val, zoom_factor_val)
        self._request_scene_rect_adjustment()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            main_window = self.window()
            if main_window.is_position_on_resize_edge(event.globalPosition()):
                return event.ignore()

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

    def initiate_add_new_node_request(self, global_menu_pos: QPoint):
        """
        Called when a request to add a new node is initiated (e.g., from context menu).
        This method calculates the scene position and emits the
        new_node_requested_at_scene_pos signal.
        """
        if not self.scene():
            print("GraphicsView: No scene to add node to.")
            return

        # Map the global mouse position to view coordinates, then to scene coordinates
        view_pos = self.mapFromGlobal(global_menu_pos)
        scene_pos = self.mapToScene(view_pos)  # scene_pos is a QPointF

        # XXX: For now, use a placeholder node type hint.
        # This can be made more dynamic later if the context menu offers choices.
        node_type_hint = "MyTestNode"  # Let's use a hint that matches our test node class for now

        self.new_node_requested_at_scene_pos.emit(scene_pos, node_type_hint)
        print(f"GraphicsView: Emitted new_node_requested_at_scene_pos({scene_pos}, '{node_type_hint}')")

    def get_command_context(self, event: QKeyEvent | QMouseEvent, command_name: str) -> Any:
        """Get the appropriate context for a command

        This method provides different contexts based on the command being executed:
        - For selection-based commands: returns the selected items
        - For view commands: returns self (the view)
        - For window commands: returns the main window
        - Default: returns a dict with common objects
        """
        if command_name == "add_node":
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            scene_pos = self.mapToScene(mouse_pos)
            return {'node_type': 'MyNodeType', 'position': scene_pos}

        # Command-specific contexts
        if command_name in ["delete_selection", "duplicate_selection", "cut", "copy"]:
            return self.scene().selectedItems()

        elif command_name in ["toggle_fullscreen", "window_maximize", "window_minimize"]:
            return self.window()

        elif command_name in ["zoom_in", "zoom_out", "reset_zoom", "pan_view"]:
            return self  # The view itself

        return {
            "view": self,
            "event": event,
            "scene": self.scene(),
            "window": self.window(),
            "selected_items": self.scene().selectedItems(),
        }

    def keyPressEvent(self, event):
        # Pass self as the context provider
        if hasattr(self, "key_manager") and self.key_manager.handle_key_event(event, self):
            return

        # if event.key() == Qt.Key_Delete:
        #     if not self._interaction_enabled:
        #         event.ignore()
        #         return

        # current_scene = self.scene()
        # if (
        #     current_scene and hasattr(current_scene, "selectedItems") and hasattr(current_scene, "node_items")
        # ):  # Ensure scene is valid
        #     selected_items = current_scene.selectedItems()
        #     node_entity_ids_to_delete = []
        #     edges_to_delete = []

        #     from .node import NodeItem  # Local import for type check
        #     from .edge import EdgeItem  # Local import for type check

        #     for item in selected_items:
        #         if isinstance(item, NodeItem):
        #             if hasattr(item, "node_entity_id") and item.node_entity_id:
        #                 node_entity_ids_to_delete.append(item.node_entity_id)
        #         elif isinstance(item, EdgeItem):
        #             edges_to_delete.append(item)

        #     if node_entity_ids_to_delete:
        #         print(f"GraphicsView: Deletion requested for node IDs: {node_entity_ids_to_delete}")
        #         self.node_deletion_requested.emit(node_entity_ids_to_delete)
        #         event.accept()
        #         return  # XXX: Nodes processed, don't process edges in same event for now

        #     if edges_to_delete:
        #         print(f"GraphicsView: Deletion requested for EdgeItems: {edges_to_delete}")
        #         self.edge_deletion_requested.emit(edges_to_delete)
        #         event.accept()
        #         return

        super().keyPressEvent(event)  # Pass to base class if not handled