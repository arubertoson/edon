from loguru import logger

from edon.graph import EntityGraph
from edon.node import EntityNode
from edon.types import SocketDisplayState, SocketDef
from edon_ui.app import EdonApplication  # Import EdonApplication instead of main
from edon_ui.widgets.factories import SocketType  # Import the new enum

# --- Define custom nodes declaratively ---


class IntegerNode(EntityNode):
    """A node that outputs a single integer value (defined declaratively)."""

    # Class attributes define the node's properties and sockets
    node_type = "constant.int"
    source_socket_definitions = [
        SocketDef(name="src_int", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_int", socket_type=SocketType.INTEGER, display_state=SocketDisplayState.WIDGET
        ),
    ]

    def process(self):
        self.target_sockets["trg_int"].value = self.source_sockets["src_int"].value
        return self.target_sockets["trg_int"].value


class FloatNode(EntityNode):
    """A node that outputs a single float value (defined declaratively)."""

    # Class attributes define the node's properties and sockets
    node_type = "constant.float"
    source_socket_definitions = [
        SocketDef(name="src_float", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_float",
            socket_type=SocketType.FLOAT,
            display_state=SocketDisplayState.LINK_WIDGET,
        ),
    ]

    def process(self):
        self.target_sockets["trg_float"].value = self.source_sockets["src_float"].value
        return self.target_sockets["trg_float"].value


class StringNode(EntityNode):
    """A node that outputs a single string value (defined declaratively)."""

    # Class attributes define the node's properties and sockets
    node_type = "string.text"
    source_socket_definitions = [
        SocketDef(name="src_text", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_text", socket_type=SocketType.STRING, display_state=SocketDisplayState.WIDGET
        )
    ]

    def process(self):
        self.target_sockets["trg_text"].value = self.source_sockets["src_text"].value
        return self.target_sockets["trg_text"].value


class LargeTextNode(EntityNode):
    """A node that accepts a large string input via a popup editor."""

    node_type = "text.large_input"
    source_socket_definitions = [
        SocketDef(name="src_text", socket_type=SocketType.LARGE_STRING),
    ]
    target_socket_definitions = [
        SocketDef(
            name="trg_text", socket_type=SocketType.STRING, display_state=SocketDisplayState.WIDGET
        )
    ]

    def process(self):
        self.target_sockets["trg_text"].value = self.source_sockets["src_text"].value
        return self.target_sockets["trg_text"].value


class AddNode(EntityNode):
    """A node that adds two integer inputs and outputs the result (declaratively)."""

    node_type = "math.add"
    source_socket_definitions = [
        SocketDef(name="result", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [
        SocketDef(name="a", socket_type=SocketType.INTEGER, display_state=SocketDisplayState.ALL),
        SocketDef(name="b", socket_type=SocketType.INTEGER, display_state=SocketDisplayState.ALL),
    ]

    def process(self):
        # Access sockets created by the base class based on definitions
        a_socket = self.source_sockets["a"]
        b_socket = self.source_sockets["b"]

        # Get input values (assuming defaults or connections provide them)
        # Sockets should have a default value (e.g., None or 0) upon creation
        # or the graph executor handles pulling values from connections.
        a_value = 0
        b_value = 0

        if a_socket.is_linked():
            connected_socket = a_socket.links[0]
            a_value = connected_socket.value if connected_socket.value is not None else 0
        elif a_socket.value is not None:
            a_value = a_socket.value  # Use default value if not connected

        if b_socket.is_linked():
            connected_socket = b_socket.links[0]
            b_value = connected_socket.value if connected_socket.value is not None else 0
        elif b_socket.value is not None:
            b_value = b_socket.value  # Use default value if not connected

        result = a_value + b_value
        self.target_sockets["result"].value = result
        logger.debug(f"AddNode ({self.name}): {a_value} + {b_value} = {result}")


class MultiplyNode(EntityNode):
    """A node that multiplies a float and an integer and outputs the result (declaratively)."""

    node_type = "math.multiply"
    source_socket_definitions = [
        SocketDef(name="result", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [
        SocketDef(name="a", socket_type=SocketType.FLOAT, display_state=SocketDisplayState.ALL),
        SocketDef(name="b", socket_type=SocketType.INTEGER, display_state=SocketDisplayState.ALL),
    ]

    def process(self):
        # Access sockets created by the base class based on definitions
        a_socket = self.source_sockets["a"]
        b_socket = self.source_sockets["b"]

        # Get input values
        a_value = 0.0
        b_value = 0

        if a_socket.is_linked():
            connected_socket = a_socket.links[0]
            a_value = connected_socket.value if connected_socket.value is not None else 0.0
        elif a_socket.value is not None:
            a_value = a_socket.value  # Use default value if not connected

        if b_socket.is_linked():
            connected_socket = b_socket.links[0]
            b_value = connected_socket.value if connected_socket.value is not None else 0
        elif b_socket.value is not None:
            b_value = b_socket.value  # Use default value if not connected

        result = a_value * b_value
        self.target_sockets["result"].value = result
        logger.debug(f"MultiplyNode ({self.name}): {a_value} * {b_value} = {result}")


class ConcatNode(EntityNode):
    """A node that concatenates two string inputs and outputs the result (declaratively)."""

    node_type = "string.concat"
    source_socket_definitions = [
        SocketDef(name="result", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(name="a", socket_type=SocketType.STRING),
        SocketDef(name="b", socket_type=SocketType.STRING),
    ]

    def process(self):
        # Access sockets created by the base class based on definitions
        a_socket = self.source_sockets["a"]
        b_socket = self.source_sockets["b"]

        # Get input values
        a_value = ""
        b_value = ""

        if a_socket.is_linked():
            connected_socket = a_socket.links[0]
            a_value = connected_socket.value if connected_socket.value is not None else ""
        elif a_socket.value is not None:
            a_value = a_socket.value  # Use default value if not connected

        if b_socket.is_linked():
            connected_socket = b_socket.links[0]
            b_value = connected_socket.value if connected_socket.value is not None else ""
        elif b_socket.value is not None:
            b_value = b_socket.value  # Use default value if not connected

        result = a_value + b_value
        self.target_sockets["result"].value = result
        logger.debug(f"ConcatNode ({self.name}): '{a_value}' + '{b_value}' = '{result}'")


# --- Register custom nodes ---
custom_node_registry = {
    # Keys should match the class names (which become default node names)
    "IntegerNode": IntegerNode,
    "FloatNode": FloatNode,
    "StringNode": StringNode,
    "AddNode": AddNode,
    "MultiplyNode": MultiplyNode,
    "ConcatNode": ConcatNode,
    "LargeTextNode": LargeTextNode,  # Register LargeTextNode
}


# --- Build a sample graph ---
def create_sample_graph():
    graph = EntityGraph()

    # Create nodes - __init__ is handled by @dataclass and EntityNode.__post_init__
    int_node = IntegerNode()
    float_node = FloatNode()
    multiply_node = MultiplyNode()

    # Create string nodes
    string_node1 = StringNode()
    string_node2 = StringNode()
    concat_node = ConcatNode()
    large_text_node1 = LargeTextNode()  # Create an instance

    logger.debug(f"Node rpl: {string_node1}")
    print("!!!!!")

    # Add nodes to graph
    graph.add_node(int_node)
    graph.add_node(float_node)
    graph.add_node(multiply_node)
    graph.add_node(string_node1)
    graph.add_node(string_node2)
    graph.add_node(concat_node)
    graph.add_node(large_text_node1)  # Add to graph

    # Set initial values for the nodes
    int_node.sockets["trg_int"].value = 5
    float_node.sockets["trg_float"].value = 2.5
    string_node1.sockets["trg_text"].value = "Hello, "
    string_node2.sockets["trg_text"].value = "World!"

    # large_text_node1.source_sockets[
    # "trg_large_text"
    # ].value = "This is some initial large text.\nIt can span multiple lines."

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
    print(graph)

    return graph


# --- Launch the app using the EdonApplication class ---
if __name__ == "__main__":
    # Create and run the application with our custom graph and node registry
    graph = create_sample_graph()
    app = EdonApplication(custom_node_registry, log_level="TRACE")
    app.load_graph(graph)

    # Set our custom graph and node registry using property setters
    # app.entity_graph = create_sample_graph()
    # app.node_registry = custom_node_registry

    # Run the application
    import sys

    sys.exit(app.run())
