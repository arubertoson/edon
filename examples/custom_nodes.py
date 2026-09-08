from loguru import logger

from edon.graph import EntityGraph, EntitySubGraphNode
from edon.node import EntityNode
from edon.nodes.utility import SubgraphPromoterNode
from edon.types import (
    SocketDisplayState,
    SocketDef,
)
from edon_ui.app import EdonApplication
from edon_ui.widgets.factories import SocketType


class IntegerNode(EntityNode):
    """A node that outputs a single integer value (defined declaratively)."""

    node_type = "constant.int"
    source_socket_definitions = [
        SocketDef(name="src_int", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_int",
            socket_type=SocketType.INTEGER,
            display_state=SocketDisplayState.WIDGET,
            default=0,
        ),
    ]

    def process(self):
        self.sockets["src_int"].value = self.sockets["trg_int"].value
        logger.debug(f"IntegerNode ({self.name}) processed value: {self.sockets['trg_int'].value}")


class FloatNode(EntityNode):
    """A node that outputs a single float value (defined declaratively)."""

    node_type = "constant.float"
    source_socket_definitions = [
        SocketDef(name="src_float", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_float",
            socket_type=SocketType.FLOAT,
            display_state=SocketDisplayState.LINK_WIDGET,
            default=0.0,
        ),
    ]

    def process(self):
        self.sockets["src_float"].value = self.sockets["trg_float"].value
        logger.debug(f"FloatNode ({self.name}) processed value: {self.sockets['trg_int'].value}")


class StringNode(EntityNode):
    """A node that outputs a single string value (defined declaratively)."""

    node_type = "string.text"
    source_socket_definitions = [  # Output
        SocketDef(name="src_text", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [  # Input
        SocketDef(
            name="trg_text",
            socket_type=SocketType.STRING,
            display_state=SocketDisplayState.WIDGET,
            default="",
        )
    ]

    def process(self):
        self.sockets["src_text"].value = self.sockets["trg_text"].value


class LargeTextNode(EntityNode):
    """A node that accepts a large string input via a popup editor."""

    node_type = "text.large_input"
    source_socket_definitions = [
        SocketDef(name="src_text", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_text",
            socket_type=SocketType.LARGE_STRING,
            display_state=SocketDisplayState.WIDGET,
            default="",
        )
    ]

    def process(self):
        self.sockets["src_text"].value = self.sockets["trg_text"].value


class AddNode(EntityNode):
    """A node that adds two integer inputs and outputs the result (declaratively)."""

    node_type = "math.add"
    source_socket_definitions = [  # Output
        SocketDef(name="result", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [  # Inputs
        SocketDef(
            name="a",
            socket_type=SocketType.INTEGER,
            display_state=SocketDisplayState.ALL,
            default=0,
        ),
        SocketDef(
            name="b",
            socket_type=SocketType.INTEGER,
            display_state=SocketDisplayState.ALL,
            default=0,
        ),
    ]

    def process(self):
        a_val = self.sockets["a"].value
        b_val = self.sockets["b"].value
        result = a_val + b_val

        self.sockets["result"].value = result
        logger.debug(f"AddNode ({self.name}): {a_val} + {b_val} = {result}")


class MultiplyNode(EntityNode):
    """A node that multiplies a float and an integer and outputs the result (declaratively)."""

    node_type = "math.multiply"
    source_socket_definitions = [  # Output
        SocketDef(name="result", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [  # Inputs
        SocketDef(
            name="a",
            socket_type=SocketType.FLOAT,
            display_state=SocketDisplayState.ALL,
            default=0.0,
        ),
        SocketDef(
            name="b",
            socket_type=SocketType.INTEGER,
            display_state=SocketDisplayState.ALL,
            default=0,
        ),
    ]

    def process(self):
        a_val = self.sockets["a"].value
        b_val = self.sockets["b"].value
        result = a_val * b_val

        self.sockets["result"].value = result
        logger.debug(f"MultiplyNode ({self.name}): {a_val} * {b_val} = {result}")


class ConcatNode(EntityNode):
    """A node that concatenates two string inputs and outputs the result (declaratively)."""

    node_type = "string.concat"
    source_socket_definitions = [  # Output
        SocketDef(name="result", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [  # Inputs
        SocketDef(name="a", socket_type=SocketType.STRING, default=""),
        SocketDef(name="b", socket_type=SocketType.STRING, default=""),
    ]

    def process(self):
        a_val = self.sockets["a"].value
        b_val = self.sockets["b"].value
        result = a_val + b_val

        self.sockets["result"].value = result
        logger.debug(f"ConcatNode ({self.name}): '{a_val}' + '{b_val}' = '{result}'")


# --- Register custom nodes ---
custom_node_registry = {
    "IntegerNode": IntegerNode,
    "FloatNode": FloatNode,
    "StringNode": StringNode,
    "AddNode": AddNode,
    "MultiplyNode": MultiplyNode,
    "ConcatNode": ConcatNode,
    "LargeTextNode": LargeTextNode,
    "SubGraphNode": EntitySubGraphNode,
    # Add the new promoter node here for testing/availability
    "SubgraphPromoterNode": SubgraphPromoterNode,
}


# --- Build a sample graph ---
def create_sample_graph():
    graph = EntityGraph()

    # Create nodes - __init__ is handled by @dataclass and EntityNode.__post_init__
    # Giving explicit names to help with debugging and identification in UI
    int_node = IntegerNode(name="MyInt")
    float_node = FloatNode(name="MyFloat")
    multiply_node = MultiplyNode(name="MyMultiplier")

    # Create string nodes
    string_node1 = StringNode(name="Str1")
    string_node2 = StringNode(name="Str2")
    concat_node = ConcatNode(name="MyConcatenator")
    large_text_node1 = LargeTextNode(name="MyLargeText")

    # Create a SubGraphNode
    sub_graph_node = EntitySubGraphNode(name="MyFirstSubGraph")

    # To make the SubGraphNode display sockets, we need to define some proxy sockets.
    # We can do this by adding internal nodes and then exposing their sockets.
    # Example: Create an internal AddNode and expose its input and output.
    internal_adder = AddNode(name="InternalAdder")  # This node needs inputs and outputs defined
    for sck in internal_adder.sockets.values():
        sck.exposed = True

    sub_graph_node.internal_graph.add_node(internal_adder)

    # Add nodes to graph
    graph.add_node(int_node)
    graph.add_node(float_node)
    graph.add_node(multiply_node)
    graph.add_node(string_node1)
    graph.add_node(string_node2)
    graph.add_node(concat_node)
    graph.add_node(large_text_node1)
    graph.add_node(sub_graph_node)  # Add the sub-graph node to the main graph

    # Set initial values for the nodes
    # Accessing sockets via self.sockets dictionary is generally safer if names are guaranteed unique
    # For EntityNode, target_sockets and source_sockets are dictionaries.
    int_node.sockets["trg_int"].value = 5
    float_node.sockets["trg_float"].value = 2.5
    string_node1.sockets["trg_text"].value = "Hello, "
    string_node2.sockets["trg_text"].value = "World!"
    # For LargeTextNode, the input socket was renamed to 'trg_text'
    large_text_node1.sockets["trg_text"].value = "Initial large text for the popup."

    # Set values for the SubGraphNode's internal adder via its exposed inputs (optional for testing)
    # This would typically happen through connections or parameter setting.
    # For UI testing, the proxy sockets should appear.
    # Example: Set the value of the proxy socket on the SubGraphNode itself
    if "sub_input_A" in sub_graph_node.sockets:  # Sockets on SubGraphNode are its proxy sockets
        sub_graph_node.sockets["sub_input_A"].value = 10
    if "sub_input_B" in sub_graph_node.sockets:
        sub_graph_node.sockets["sub_input_B"].value = 20
    # The internal_adder.process() would then use these values if the sub-graph is processed.

    # Connect float_node and int_node to multiply_node
    # success1, reason1 = graph.connect_sockets(
    #     SocketAddress(float_node.id, "src_float"), SocketAddress(multiply_node.id, "a")
    # )
    # success2, reason2 = graph.connect_sockets(
    #     SocketAddress(int_node.id, "src_int"), SocketAddress(multiply_node.id, "b")
    # )
    # if not success1:
    #     logger.error(f"Failed to connect float_node to multiply_node: {reason1}")
    # if not success2:
    #     logger.error(f"Failed to connect int_node to multiply_node: {reason2}")

    # # Connect string nodes to concat node
    # success3, reason3 = graph.connect_sockets(
    #     SocketAddress(string_node1.id, "src_text"), SocketAddress(concat_node.id, "a")
    # )
    # success4, reason4 = graph.connect_sockets(
    #     SocketAddress(string_node2.id, "src_text"), SocketAddress(concat_node.id, "b")
    # )
    # if not success3:
    #     logger.error(f"Failed to connect string_node1 to concat_node: {reason3}")
    # if not success4:
    #     logger.error(f"Failed to connect string_node2 to concat_node: {reason4}")

    return graph


# --- Launch the app using the EdonApplication class ---
if __name__ == "__main__":
    # Create and run the application with our custom graph and node registry
    graph = create_sample_graph()
    app = EdonApplication(custom_node_registry, log_level="DEBUG")  # Use TRACE for detailed logs
    app.load_graph(graph)

    # Run the application
    import sys

    sys.exit(app.run())
