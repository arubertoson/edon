from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent
from loguru import logger
from typing import Any
from .base import CommandRegistry, ContextProvider
from .builtins import KeyBinding

class KeyManager(QObject):
    sequence_changed = Signal(str)

    def __init__(self, command_registry: CommandRegistry):
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
        combo = (key, modifiers)
        if combo in self._bindings:
            binding = self._bindings[combo]
            logger.debug(f"Found direct key binding: {binding.command_name}")
            context, success = self._get_command_context(event, binding.command_name, context_provider)
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
            context, success = self._get_command_context(event, binding.command_name, context_provider)
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