"""Built-in command definitions for the application.

This file is responsible for defining the `ALL_COMMAND_DEFINITIONS` list,
which aggregates all command objects used by the application.
It imports action functions from the `actions` sub-package.
"""

from edon_ui.commands.actions.basic_actions import (
    close_action,
    delete_selection_action,
    help_action,
    window_toggle_maximize_action,
    action_show_node_spawner,
    action_enter_subgraph,
    action_exit_subgraph,
)
from edon_ui.commands.core import Command


def _parse_hotkey_sequence(hotkey_str: str | None) -> list[str] | None:
    """Parses a comma-separated hotkey string into a list of sequences."""
    if not hotkey_str:
        return None
    return hotkey_str.split(",")


ALL_COMMAND_DEFINITIONS: list[Command] = [
    Command(
        id="app.close",
        label="Close",
        category="Application",
        description="Close the application.",
        action=close_action,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+X"),
    ),
    Command(
        id="help.show",
        label="Help",
        category="Help",
        description="Show help dialog.",
        action=help_action,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+H"),
    ),
    Command(
        id="window.toggle_maximize",
        label="Toggle Maximize/Fullscreen",
        category="Window",
        description="Toggle window maximize/fullscreen state.",
        action=window_toggle_maximize_action,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+K,Ctrl+F"),
    ),
    Command(
        id="edit.delete_selection",
        label="Delete Selection",
        category="Edit",
        description="Delete selected items (nodes and edges).",
        action=delete_selection_action,
        default_hotkey_sequence=_parse_hotkey_sequence("D"),
    ),
    Command(
        id="graph.show_node_spawner",
        label="Add Node...",
        category="Graph",
        description="Opens a panel to search and add new nodes to the graph.",
        action=action_show_node_spawner,
        default_hotkey_sequence=_parse_hotkey_sequence("Shift+A"),
    ),
    Command(
        id="graph.enter_subgraph",
        label="Enter Subgraph",
        category="Graph Navigation",
        description="Enter the selected subgraph node to view/edit its internal graph.",
        action=action_enter_subgraph,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+E"),
    ),
    Command(
        id="graph.exit_subgraph",
        label="Exit Subgraph",
        category="Graph Navigation",
        description="Exit the current subgraph and return to its parent graph.",
        action=action_exit_subgraph,
        default_hotkey_sequence=_parse_hotkey_sequence("Ctrl+U"), # "U" for "Up"
    ),
]
