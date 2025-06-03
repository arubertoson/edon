"""Command System for Edon UI.

This package implements a comprehensive command and hotkey management system.

Exports:
    - Core components:
        - `Command`: Dataclass representing a command.
        - `CommandRegistry`: Manages all defined commands.
        - `EditorContext`: Type alias for the context passed to command actions.
        - `ContextProvider`: Protocol for objects providing `EditorContext`.
    - Hotkey management:
        - `KeyMapping`: Manages mappings between hotkey sequences and command IDs.
    - Event processing:
        - `KeyProcessor`: Processes input events to trigger commands.
    - Built-in command definitions:
        - `ALL_COMMAND_DEFINITIONS`: A list of pre-defined `Command` objects.
    - Default registry instance:
        - `default_command_registry`: A pre-populated CommandRegistry instance.
"""

from .core import Command, ContextProvider, EditorContext, CommandRegistry
from .key_mapping import KeyMapping
from .key_processor import KeyProcessor
from .builtins import ALL_COMMAND_DEFINITIONS


def _create_and_populate_registry() -> CommandRegistry:
    """Creates and populates a CommandRegistry with all built-in commands."""
    registry = CommandRegistry()
    for cmd_def in ALL_COMMAND_DEFINITIONS:
        registry.register(cmd_def)
    return registry


default_command_registry: CommandRegistry = _create_and_populate_registry()

__all__ = [
    "Command",
    "CommandRegistry",
    "EditorContext",
    "ContextProvider",
    "KeyMapping",
    "KeyProcessor",
    "default_command_registry",
]
