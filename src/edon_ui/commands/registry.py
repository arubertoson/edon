from loguru import logger
from PySide6.QtCore import Qt
from .base import CommandRegistry
from .builtins import DeleteSelectionCommand, ToggleFullscreenCommand, AddNodeCommand, KeyBinding
from .manager import KeyManager

def setup_commands(graph_manager):
    logger.debug("Setting up commands")
    registry = CommandRegistry()
    registry.register("delete_selection", DeleteSelectionCommand(graph_manager))
    registry.register("toggle_fullscreen", ToggleFullscreenCommand())
    registry.register("add_node", AddNodeCommand(graph_manager))
    logger.debug(f"Registered {len(registry.commands)} commands")
    return registry

def setup_key_bindings(key_manager: KeyManager):
    logger.debug("Setting up key bindings")
    bindings = {
        "delete_selection": {
            "description": "Delete selected items",
            "keys": [
                (Qt.Key_Delete, Qt.KeyboardModifier.NoModifier),
                (Qt.Key_D, Qt.KeyboardModifier.ControlModifier),
            ],
            "sequences": [],
        },
        "add_node": {
            "description": "Add a new node",
            "keys": [
                (Qt.Key_A, Qt.KeyboardModifier.ShiftModifier),
            ],
            "sequences": [],
        },
        "toggle_fullscreen": {
            "description": "Toggle fullscreen mode",
            "keys": [
                (Qt.Key_F11, Qt.KeyboardModifier.NoModifier),
                (Qt.Key_Return, Qt.KeyboardModifier.AltModifier),
            ],
            "sequences": ["Ctrl+K, Ctrl+F"],
        },
        "zoom_in": {
            "description": "Zoom in",
            "keys": [(Qt.Key_Plus, Qt.KeyboardModifier.ControlModifier)],
            "sequences": [],
        },
        "zoom_out": {
            "description": "Zoom out",
            "keys": [(Qt.Key_Minus, Qt.KeyboardModifier.ControlModifier)],
            "sequences": [],
        },
        "reset_zoom": {
            "description": "Reset zoom level",
            "keys": [(Qt.Key_0, Qt.KeyboardModifier.ControlModifier)],
            "sequences": ["Ctrl+K, Ctrl+Z"],
        },
    }
    for command_name, binding_info in bindings.items():
        description = binding_info["description"]
        for key, modifiers in binding_info["keys"]:
            key_manager.register_key(KeyBinding(key, modifiers, command_name, description))
            logger.trace(f"Registered key binding: {key} + {modifiers} -> {command_name}")
        for sequence in binding_info["sequences"]:
            key_manager.register_sequence(
                sequence, KeyBinding(0, Qt.KeyboardModifier.NoModifier, command_name, description)
            )
            logger.trace(f"Registered sequence binding: {sequence} -> {command_name}")
    logger.debug(
        f"Registered {sum(len(b['keys']) for b in bindings.values())} key bindings and {sum(len(b['sequences']) for b in bindings.values())} sequences"
    ) 