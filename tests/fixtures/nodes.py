"""Custom node types for testing Edon functionality.

This module provides a collection of simple node types that can be used
in integration tests, particularly for sub-graph functionality testing.
These nodes are designed to be lightweight and focused on testing core
graph execution and data flow.
"""

from loguru import logger

from edon.node import EntityNode
from edon.types import SocketDisplayState, SocketDef, SocketType


class IntegerNode(EntityNode):
    """A node that outputs a single integer value."""

    node_type = "test.constant.int"
    source_socket_definitions = [
        SocketDef(name="src_int", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_int", 
            socket_type=SocketType.INTEGER, 
            display_state=SocketDisplayState.WIDGET,
            default=0
        ),
    ]

    def process(self) -> None:
        """Copy input value to output."""
        input_value = self.sockets["trg_int"].value
        if input_value is None:
            input_value = 0
        self.sockets["src_int"].value = input_value
        logger.trace(f"IntegerNode ({self.name}): output = {input_value}")


class FloatNode(EntityNode):
    """A node that outputs a single float value."""

    node_type = "test.constant.float"
    source_socket_definitions = [
        SocketDef(name="src_float", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_float",
            socket_type=SocketType.FLOAT,
            display_state=SocketDisplayState.WIDGET,
            default=0.0
        ),
    ]

    def process(self) -> None:
        """Copy input value to output."""
        input_value = self.sockets["trg_float"].value
        if input_value is None:
            input_value = 0.0
        self.sockets["src_float"].value = input_value
        logger.trace(f"FloatNode ({self.name}): output = {input_value}")


class StringNode(EntityNode):
    """A node that outputs a single string value."""

    node_type = "test.constant.string"
    source_socket_definitions = [
        SocketDef(name="src_text", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_text", 
            socket_type=SocketType.STRING, 
            display_state=SocketDisplayState.WIDGET,
            default=""
        )
    ]

    def process(self) -> None:
        """Copy input value to output."""
        input_value = self.sockets["trg_text"].value
        if input_value is None:
            input_value = ""
        self.sockets["src_text"].value = input_value
        logger.trace(f"StringNode ({self.name}): output = '{input_value}'")


class AddNode(EntityNode):
    """A node that adds two integer inputs and outputs the result."""

    node_type = "test.math.add"
    source_socket_definitions = [
        SocketDef(name="result", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [
        SocketDef(name="a", socket_type=SocketType.INTEGER, default=0),
        SocketDef(name="b", socket_type=SocketType.INTEGER, default=0),
    ]

    def process(self) -> None:
        """Add the two input values."""
        a_value = self.sockets["a"].value or 0
        b_value = self.sockets["b"].value or 0
        
        result = a_value + b_value
        self.sockets["result"].value = result
        logger.trace(f"AddNode ({self.name}): {a_value} + {b_value} = {result}")


class MultiplyNode(EntityNode):
    """A node that multiplies a float and an integer and outputs the result."""

    node_type = "test.math.multiply"
    source_socket_definitions = [
        SocketDef(name="result", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [
        SocketDef(name="a", socket_type=SocketType.FLOAT, default=0.0),
        SocketDef(name="b", socket_type=SocketType.INTEGER, default=0),
    ]

    def process(self) -> None:
        """Multiply the two input values."""
        a_value = self.sockets["a"].value or 0.0
        b_value = self.sockets["b"].value or 0
        
        result = float(a_value) * float(b_value)
        self.sockets["result"].value = result
        logger.trace(f"MultiplyNode ({self.name}): {a_value} * {b_value} = {result}")


class ConcatNode(EntityNode):
    """A node that concatenates two string inputs and outputs the result."""

    node_type = "test.string.concat"
    source_socket_definitions = [
        SocketDef(name="result", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(name="a", socket_type=SocketType.STRING, default=""),
        SocketDef(name="b", socket_type=SocketType.STRING, default=""),
    ]

    def process(self) -> None:
        """Concatenate the two input strings."""
        a_value = self.sockets["a"].value or ""
        b_value = self.sockets["b"].value or ""
        
        result = str(a_value) + str(b_value)
        self.sockets["result"].value = result
        logger.trace(f"ConcatNode ({self.name}): '{a_value}' + '{b_value}' = '{result}'")


# Registry for easy access in tests
TEST_NODE_REGISTRY = {
    "IntegerNode": IntegerNode,
    "FloatNode": FloatNode,
    "StringNode": StringNode,
    "AddNode": AddNode,
    "MultiplyNode": MultiplyNode,
    "ConcatNode": ConcatNode,
}
