"""Command System for Edon UI.

This package implements a comprehensive command and hotkey management system.

Exports:
    - Core components:
        - `Command`: Dataclass representing a command.
        - `CommandRegistry`: Manages all defined commands.
        - `EditorContext`: Type alias for the context passed to command actions.
        - `ContextProvider`: Protocol for objects providing `EditorContext`.
    - Hotkey management:
        - `HotkeyMapping`: Manages mappings between hotkey sequences and command IDs.
    - Event processing:
        - `KeyProcessor`: Processes input events to trigger commands.
    - Built-in command definitions:
        - `ALL_COMMAND_DEFINITIONS`: A list of pre-defined `Command` objects.
"""

from .core import Command, ContextProvider, EditorContext, CommandRegistry
from .key_mapping import KeyMapping
from .key_processor import KeyProcessor
from .builtins import ALL_COMMAND_DEFINITIONS

__all__ = [
    "Command",
    "CommandRegistry",
    "EditorContext",
    "ContextProvider",
    "KeyMapping",
    "KeyProcessor",
    "ALL_COMMAND_DEFINITIONS",
]
