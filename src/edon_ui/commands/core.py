"""Core data structures and protocols for the command system.

Defines:
- `EditorContext`: A type alias for the context object passed to commands.
- `ContextProvider`: A protocol for objects that can provide an `EditorContext`.
- `Command`: A dataclass representing an executable action with metadata.
- `CommandRegistry`: A class to manage a collection of `Command` objects.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from loguru import logger

from edon_ui.graphics.view import EditorContext

if TYPE_CHECKING:
    from PySide6.QtGui import QInputEvent


class ContextProvider(Protocol):
    """A protocol for objects that can provide an EditorContext.

    This interface ensures that any object responsible for generating
    the context for command execution adheres to a common contract.
    """

    def provide_context(self, event: "QInputEvent | None" = None) -> EditorContext:
        """Provides the current editor context.

        The context might be influenced by the current state of the UI,
        the active document, or the event that triggered the command.

        Args:
            event: An optional QKeyEvent that might influence context creation.
                   For example, mouse position for context menus.

        Returns:
            The relevant EditorContext for a command action.
        """
        ...


@dataclass
class Command:
    """Represents a unique, executable command within the application.

    A command encapsulates an action, its metadata (like a user-facing label
    and category), and an optional default hotkey sequence.

    Attributes:
        id: A unique string identifier for the command (e.g., "file.save").
        label: A user-friendly name for the command (e.g., "Save File").
        category: A string used to group related commands (e.g., "File", "Edit").
        action: The callable to execute when the command is triggered.
            It takes an `EditorContext` object and should return `True` if the
            action was successful or handled, `False` otherwise.
        default_hotkey_sequence: An optional list of strings representing the
            suggested default hotkey sequence (e.g., `["Ctrl+S"]` or `["Ctrl+K", "S"]`).
        description: An optional, more detailed description of the command.
    """

    id: str
    label: str
    category: str
    action: Callable[[EditorContext], bool]
    default_hotkey_sequence: list[str] | None = None
    description: str | None = None


class CommandRegistry:
    """Manages the collection of all available commands.

    This registry provides a central place to store and retrieve `Command` objects.
    It ensures that command IDs are unique and allows for easy lookup of commands
    by ID or category.
    """

    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        """Registers a command with the registry.

        If a command with the same ID already exists, it will be overwritten.
        Consider logging a warning in such cases.

        Args:
            command: The `Command` object to register.
        """
        if command.id in self._commands:
            logger.warning(f"Command '{command.id}' is being overwritten in CommandRegistry.")
        self._commands[command.id] = command

    def get_command(self, command_id: str) -> Command | None:
        """Retrieves a command by its unique ID.

        Args:
            command_id: The ID of the command to retrieve.

        Returns:
            The `Command` object if found, otherwise `None`.
        """
        return self._commands.get(command_id)

    def get_all_commands(self) -> list[Command]:
        """Retrieves all registered commands.

        Returns:
            A list of all `Command` objects in the registry.
        """
        return list(self._commands.values())

    def get_commands_by_category(self) -> dict[str, list[Command]]:
        """Groups all registered commands by their category.

        Returns:
            A dictionary where keys are category names and values are lists
            of `Command` objects belonging to that category.
        """
        categories: dict[str, list[Command]] = {}
        for command_instance in self._commands.values():
            categories.setdefault(command_instance.category, []).append(command_instance)
        return categories
