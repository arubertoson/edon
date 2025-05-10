from dataclasses import dataclass
from typing import Any, Protocol

from loguru import logger
from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent
from PySide6.QtWidgets import QMainWindow

from edon_ui.item.edge import EdgeItem
from edon_ui.item.node import NodeItem


class Command(Protocol):
    def execute(self, context: Any = None) -> bool:
        ...


class CommandRegistry:
    def __init__(self):
        self.commands: dict[str, Command] = {}

    def register(self, name: str, command: Command) -> None:
        self.commands[name] = command

    def execute(self, name: str, context: Any = None) -> bool:
        if name in self.commands:
            return self.commands[name].execute(context)
        logger.warning(f"Attempted to execute unknown command: {name}")
        return False


class DeleteSelectionCommand:
    def __init__(self, graph_manager):
        self.graph_manager = graph_manager

    def execute(self, context: Any = None) -> bool:
        if not context:
            logger.warning("DeleteSelectionCommand executed with empty context")
            return False

        node_items = [item for item in context if isinstance(item, NodeItem)]
        edge_items = [item for item in context if isinstance(item, EdgeItem)]

        logger.info(f"DeleteSelectionCommand: Deleting {len(node_items)} nodes and {len(edge_items)} edges")

        if node_items:
            node_ids = [node.node_entity_id for node in node_items]
            self.graph_manager.handle_ui_node_deletion_request(node_ids)

        if edge_items:
            edge_info = []
            for edge in edge_items:
                if edge.source_socket_item and edge.target_socket_item:
                    source = edge.source_socket_item.parent_node_entity_id
                    target = edge.target_socket_item.parent_node_entity_id
                    edge_info.append(f"{source}->{target}")
                else:
                    edge_info.append("incomplete_edge")
            logger.debug(f"Deleting edges: {edge_info}")
            self.graph_manager.handle_ui_edge_deletion_request(edge_items)

        return True


class ToggleFullscreenCommand:
    def execute(self, context: QMainWindow = None) -> bool:
        if not context:
            logger.warning("ToggleFullscreenCommand executed with invalid context (not a window)")
            return False

        current_state = context.isFullScreen()
        new_state = not current_state
        logger.info(f"Toggling fullscreen: {current_state} -> {new_state}")

        if current_state:
            context.showNormal()
        else:
            context.showFullScreen()
        return True


@dataclass
class KeyBinding:
    key: int
    modifiers: Qt.KeyboardModifier
    command_name: str
    description: str = ""


class ContextProvider(Protocol):
    def get_command_context(self, command_name: str) -> Any:
        ...


class KeyManager(QObject):
    sequence_changed = Signal(str)

    def __init__(self, command_registry: "CommandRegistry"):
        super().__init__()
        self.command_registry = command_registry
        self._bindings: dict[tuple[int, Qt.KeyboardModifier], KeyBinding] = {}
        self._sequences: dict[str, KeyBinding] = {}
        self._current_sequence_keys: list[tuple[int, Qt.KeyboardModifier]] = []
        self._current_sequence_text: str = ""
        self._sequence_timer = QTimer(self)
        self._sequence_timer.setSingleShot(True)
        self._sequence_timer.timeout.connect(self._reset_sequence)
        self._sequence_timeout = 1000  # ms

    def register_key(self, binding: KeyBinding) -> None:
        key = (binding.key, binding.modifiers)
        self._bindings[key] = binding
        key_txt = QKeySequence(binding.key).toString()
        mod_txt = self._get_modifier_text(binding.modifiers)
        logger.debug(f"Registered key binding: {mod_txt}{key_txt} -> {binding.command_name} ({binding.description})")

    def register_sequence(self, sequence: str, binding: KeyBinding) -> None:
        self._sequences[sequence] = binding
        logger.debug(f"Registered sequence binding: {sequence} -> {binding.command_name} ({binding.description})")

    def _get_modifier_text(self, modifiers: Qt.KeyboardModifier) -> str:
        mod_texts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            mod_texts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            mod_texts.append("Shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            mod_texts.append("Alt")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            mod_texts.append("Meta")
        if mod_texts:
            return "+".join(mod_texts) + "+"
        return ""

    def _append_to_sequence(self, key: int, modifiers: Qt.KeyboardModifier) -> str:
        self._current_sequence_keys.append((key, modifiers))
        key_txt = QKeySequence(key).toString()
        mod_txt = self._get_modifier_text(modifiers)
        if self._current_sequence_text:
            self._current_sequence_text += ", " + mod_txt + key_txt
        else:
            self._current_sequence_text = mod_txt + key_txt
        return self._current_sequence_text

    def _reset_sequence(self) -> None:
        if self._current_sequence_keys:
            logger.debug(f"Resetting key sequence: {self._current_sequence_text}")
        self._current_sequence_keys.clear()
        self._current_sequence_text = ""
        self._sequence_timer.stop()
        self.sequence_changed.emit("")

    def _get_command_context(self, event: QKeyEvent | QMouseEvent, command_name: str, context_provider: ContextProvider | None) -> tuple[Any, bool]:
        """
        Get the command context from the provider.

        Args:
            command_name: The name of the command to get context for
            context_provider: The context provider

        Returns:
            Tuple of (context, success_flag)
        """
        if not context_provider:
            logger.debug(f"No context provider for {command_name}")
            return None, True
        try:
            context = context_provider.get_command_context(event, command_name)
            logger.debug(f"Got context for {command_name}: {type(context).__name__}")
            return context, True
        except Exception as e:
            logger.error(f"Error getting context for {command_name}: {e}")
            return None, False

    def handle_key_event(self, event: QKeyEvent | QMouseEvent, context_provider: ContextProvider | None = None) -> bool:
        if event.type() != QKeyEvent.Type.KeyPress:
            return False

        key = event.key()
        modifiers = event.modifiers()

        key_txt = QKeySequence(key).toString()
        mod_txt = self._get_modifier_text(modifiers)
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            logger.debug(f"Skipping standalone modifier key: {mod_txt}")
            return False
        logger.debug(f"Handling key event: {mod_txt}{key_txt} (key={key}, modifiers={modifiers})")

        # First, check if this is a direct key binding (single key + modifiers)
        # This takes precedence over sequences for immediate response
        combo = (key, modifiers)
        if combo in self._bindings:
            binding = self._bindings[combo]
            logger.debug(f"Found direct key binding: {binding.command_name}")

            context, success = self._get_command_context(event,binding.command_name, context_provider)
            if not success:
                return False

            return self.command_registry.execute(binding.command_name, context)

        try:
            sequence_text = self._append_to_sequence(key, modifiers)
            logger.debug(f"Building sequence: {sequence_text}")
        except Exception as e:
            logger.error(f"Error building key sequence: {e}")
            self._reset_sequence()
            return False

        if sequence_text in self._sequences:
            binding = self._sequences[sequence_text]
            logger.debug(f"Found sequence match: {binding.command_name}")

            context, success = self._get_command_context(event,binding.command_name, context_provider)
            self._reset_sequence()
            if not success:
                return False

            return self.command_registry.execute(binding.command_name, context)

        possible_matches = [s for s in self._sequences.keys() if s.startswith(sequence_text)]
        if not possible_matches:
            logger.debug(f"Sequence '{sequence_text}' is not a prefix of any registered sequence")
            self._reset_sequence()
            return False

        self._sequence_timer.start(self._sequence_timeout)
        self.sequence_changed.emit(sequence_text)
        return True


class AddNodeCommand:
    def __init__(self, graph_manager):
        self.graph_manager = graph_manager

    def execute(self, context: Any = None) -> bool:
        """
        Context should be a dict with at least 'node_type' and optionally 'position'.
        Example: {'node_type': 'MyNodeType', 'position': QPointF(100, 100)}
        """
        if not context or 'node_type' not in context:
            logger.warning("AddNodeCommand executed with invalid context")
            return False

        node_type = context['node_type']
        position = context.get('position', None)
        try:
            self.graph_manager.handle_ui_node_creation_request(node_type, position)
            logger.info(f"AddNodeCommand: Added node of type {node_type} at {position}")
            return True
        except Exception as e:
            logger.error(f"AddNodeCommand failed: {e}")
            return False

