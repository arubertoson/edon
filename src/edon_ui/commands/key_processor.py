"""Processes raw input events to trigger commands based on hotkey mappings.

This module defines the `KeyProcessor` class, which listens to input events
(keyboard and mouse), manages partial key/action sequences, and, upon matching
a complete hotkey sequence, retrieves and executes the corresponding command.
"""

from loguru import logger
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QInputEvent, QKeySequence

if TYPE_CHECKING:
    from .core import CommandRegistry, ContextProvider
    from .key_mapping import KeyMapping


class KeyProcessor(QObject):
    """Processes Qt input events (keyboard/mouse) for command execution."""

    def __init__(
        self,
        command_registry: "CommandRegistry",
        hotkey_mapping: "KeyMapping",
        parent: QObject | None = None,
        sequence_timeout_ms: int = 1500,
    ) -> None:
        super().__init__(parent)
        self.command_registry = command_registry
        self.hotkey_mapping = hotkey_mapping
        self._current_typed_sequence: list[str] = []

        self._sequence_timer = QTimer(self)
        self._sequence_timer.setSingleShot(True)
        self._sequence_timer.timeout.connect(self._reset_typed_sequence)
        self._sequence_timeout_ms: int = sequence_timeout_ms

    def _qkeyevent_to_string(self, event: QKeyEvent) -> str | None:
        """Converts a QKeyEvent to a canonical string representation."""
        if event.type() != QKeyEvent.Type.KeyPress:
            return None

        # Ignore pure modifier keys -> "Ctrl+Control"
        if event.key() in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return None

        key_str = QKeySequence(event.keyCombination()).toString(QKeySequence.PortableText)
        return key_str if key_str else None

    def _qmouseevent_to_string(self, event: QMouseEvent) -> str | None:
        """Converts a QMouseEvent to a canonical string representation.

        Handles MouseButtonPress events.
        Format: [Modifiers+]MouseButtonAction (e.g., "Ctrl+LMBClick", "RMBClick")
        """
        if event.type() != QMouseEvent.Type.MouseButtonPress:
            return None

        modifiers_str = ""
        qt_mods = event.modifiers()
        if qt_mods & Qt.KeyboardModifier.ControlModifier:
            modifiers_str += "Ctrl+"
        if qt_mods & Qt.KeyboardModifier.MetaModifier:  # Cmd on macOS
            modifiers_str += "Meta+"
        if qt_mods & Qt.KeyboardModifier.AltModifier:
            modifiers_str += "Alt+"
        if qt_mods & Qt.KeyboardModifier.ShiftModifier:
            modifiers_str += "Shift+"

        button_action_str: str | None = None
        if event.button() == Qt.MouseButton.LeftButton:
            button_action_str = "LMBClick"
        elif event.button() == Qt.MouseButton.RightButton:
            button_action_str = "RMBClick"
        elif event.button() == Qt.MouseButton.MiddleButton:
            button_action_str = "MMBClick"
        # Potentially handle Qt.MouseButton.BackButton, Qt.MouseButton.ForwardButton if needed

        if not button_action_str:
            return None  # Unhandled mouse button for sequences

        return modifiers_str + button_action_str

    def process_input_event(self, event: QInputEvent, context_provider: "ContextProvider") -> bool:
        """Handles an incoming input event (keyboard or mouse)."""
        action_str: str | None = None

        if isinstance(event, QKeyEvent):
            action_str = self._qkeyevent_to_string(event)
        elif isinstance(event, QMouseEvent):
            action_str = self._qmouseevent_to_string(event)
        else:
            return False  # Not a keyboard or mouse event we process for sequences

        if not action_str:
            # This can happen if it's a key release, unhandled mouse button, or empty QKeySequence string.
            # self._reset_typed_sequence_and_log_issue(event if isinstance(event, (QKeyEvent, QMouseEvent)) else None, "Event to string conversion failed or event type not processed")
            # Don't reset sequence here if it's just an uninteresting event (e.g. mouse move)
            return False

        # For QKeyEvents, "pure modifier" strings like "Ctrl" should typically only continue a sequence.
        # If action_str is a pure modifier and no sequence is active, generally ignore.
        # This is tricky because "Ctrl" might be a valid first element of a sequence like ("Ctrl", "K").
        # QKeySequence.toString usually makes "Ctrl+K".
        # This logic might need refinement based on how QKeySequence.toString() outputs single modifiers.
        is_standalone_modifier_str = action_str in ("Ctrl", "Shift", "Alt", "Meta")
        if is_standalone_modifier_str and not self._current_typed_sequence and isinstance(event, QKeyEvent):
            # logger.trace(f"Ignoring standalone modifier string: {action_str}")
            return False

        self._current_typed_sequence.append(action_str)
        logger.debug(f"Current sequence: {self._current_typed_sequence}")
        self._sequence_timer.start(self._sequence_timeout_ms)
        current_sequence_tuple = tuple(self._current_typed_sequence)

        command_id = self.hotkey_mapping.get_command_id_for_sequence(current_sequence_tuple)
        if command_id:
            command = self.command_registry.get_command(command_id)
            if command:
                editor_context = context_provider.provide_context(event)
                logger.info(f"Executing command '{command.id}' for sequence: {current_sequence_tuple}")
                command.action(editor_context)
                self._reset_typed_sequence()
                if hasattr(event, "accept"):
                    event.accept()
                return True
            else:
                logger.error(
                    f"Command ID '{command_id}' found in hotkey map but not in registry. Sequence: {current_sequence_tuple}"
                )
                self._reset_typed_sequence()
                return False

        if self.hotkey_mapping.is_prefix_of_any_binding(current_sequence_tuple):
            logger.debug(f"Current sequence {current_sequence_tuple} is a prefix.")
            if hasattr(event, "accept"):
                event.accept()
            return True

        # Not a full match and not a prefix
        # logger.debug(f"Sequence {current_sequence_tuple} not a command or prefix. Resetting.")
        self._reset_typed_sequence()  # Reset if the appended action_str didn't lead to a match or prefix
        return False

    def _reset_typed_sequence_and_log_issue(self, event: QInputEvent | None, issue_message: str) -> None:
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
            logger.debug(f"Resetting sequence: {self._current_typed_sequence}")
            self._current_typed_sequence.clear()
        if self._sequence_timer.isActive():
            self._sequence_timer.stop()

    def set_sequence_timeout(self, timeout_ms: int) -> None:
        """Sets the timeout for multi-key sequences."""
        if timeout_ms > 0:
            self._sequence_timeout_ms = timeout_ms
        else:
            logger.warning(f"Attempted to set invalid sequence timeout: {timeout_ms}ms. Using current or default.")
