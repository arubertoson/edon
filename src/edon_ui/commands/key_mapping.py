"""Manages the mapping between hotkey sequences and command identifiers.

This module defines the `HotkeyMapping` class, which is responsible for
storing and resolving hotkey bindings. It allows for setting default
bindings based on command definitions and can be extended to support
loading and saving user-customized hotkey configurations.
"""

from typing import TYPE_CHECKING, Self
from loguru import logger

if TYPE_CHECKING:
    from edon_ui.commands.core import Command


class KeyMapping:
    """Manages the current mapping between hotkey sequences and command IDs.

    This class stores user-configurable hotkey bindings. It can be initialized
    with default hotkeys derived from command definitions and provides methods
    to look up command IDs by key sequence and vice-versa.
    """

    def __init__(self) -> None:
        self._bindings: dict[tuple[str, ...], str] = {}  # sequence_tuple -> command_id

    @classmethod
    def from_command_defaults(cls, commands: list["Command"]) -> Self:
        """Creates a new KeyMapping instance populated with command defaults.

        Args:
            commands: A list of `Command` objects to derive default hotkeys from.

        Returns:
            A new KeyMapping instance with default bindings loaded.
        """
        instance = cls()
        for cmd in commands:
            if cmd.default_hotkey_sequence:
                sequence_tuple = tuple(cmd.default_hotkey_sequence or [])
                instance.set_binding(sequence_tuple, cmd.id)
        return instance

    def set_binding(self, sequence: tuple[str, ...], command_id: str) -> None:
        """Sets or overwrites a hotkey binding for a command ID.

        Associates a key sequence with a command ID. Overwrites existing bindings
        for the sequence or the command ID to maintain a one-to-one relationship
        between a sequence and its command, and a command to its primary sequence.

        Args:
            sequence: A tuple of strings representing the key sequence.
            command_id: The unique identifier of the command to bind.
        """
        if sequence in self._bindings:
            existing_cmd_id = self._bindings[sequence]
            if existing_cmd_id != command_id:
                logger.warning(
                    f"KeyMapping: Sequence {sequence} reassigned from '{existing_cmd_id}' to '{command_id}'."
                )
            del self._bindings[sequence]

        current_sequence_for_command = self.get_sequence_for_command_id(command_id)
        if current_sequence_for_command and current_sequence_for_command != sequence:
            logger.warning(
                f"KeyMapping: Command '{command_id}' remapped from {current_sequence_for_command} to {sequence}."
            )
            if current_sequence_for_command in self._bindings:
                del self._bindings[current_sequence_for_command]

        self._bindings[sequence] = command_id
        logger.debug(f"KeyMapping: Bound sequence {sequence} to command '{command_id}'.")

    def get_command_id_for_sequence(self, sequence: tuple[str, ...]) -> str | None:
        """Retrieves the command ID associated with a given hotkey sequence.

        Args:
            sequence: A tuple of strings representing the key sequence.

        Returns:
            The command ID if the sequence is bound, otherwise `None`.
        """
        return self._bindings.get(sequence)

    def get_sequence_for_command_id(self, command_id: str) -> tuple[str, ...] | None:
        """Retrieves the hotkey sequence associated with a given command ID.

        Args:
            command_id: The unique identifier of the command.

        Returns:
            The hotkey sequence if bound, otherwise `None`.
        """
        for seq, cmd_id in self._bindings.items():
            if cmd_id == command_id:
                return seq
        return None

    def get_all_bindings(self) -> dict[tuple[str, ...], str]:
        """Retrieves all current hotkey bindings.

        Returns:
            A copy of all sequence-to-command_id mappings.
        """
        return self._bindings.copy()

    def is_prefix_of_any_binding(self, sequence_tuple: tuple[str, ...]) -> bool:
        """Checks if the given sequence is a prefix of any longer bound sequence.

        Args:
            sequence_tuple: The sequence to check.

        Returns:
            True if `sequence_tuple` is a prefix of at least one longer binding,
            False otherwise.
        """
        if not sequence_tuple:  # An empty sequence cannot be a prefix
            return False

        for bound_sequence in self._bindings.keys():
            if len(bound_sequence) > len(sequence_tuple) and bound_sequence[: len(sequence_tuple)] == sequence_tuple:
                return True
        return False

    # TODO(dev): Add methods to load/save from/to JSON/config file
    # e.g., def load_from_config(self, config_path: str) -> None:
    # e.g., def save_to_config(self, config_path: str) -> None:
