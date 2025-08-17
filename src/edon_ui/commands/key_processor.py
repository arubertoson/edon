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
