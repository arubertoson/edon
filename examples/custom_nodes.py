from loguru import logger

from edon.graph import EntityGraph
from edon.node import EntityNode, SocketDef
from edon_ui.app import EdonApplication  # Import EdonApplication instead of main

# --- Define custom nodes declaratively ---


class IntegerNode(EntityNode):
    """A node that outputs a single integer value (defined declaratively)."""

    # Class attributes define the node's properties and sockets
    node_type = "constant.int"
    input_socket_definitions = [
        SocketDef(name="in_int", type=int, visual_type_key="number", accepts_connection=False),
    ]
    output_socket_definitions = [
        SocketDef(name="out_int", type=int, visual_type_key="number"),
    ]

    def process(self):
        self.output_sockets["out_int"].value = self.input_sockets["in_int"].value
        return self.output_sockets["out_int"].value


class FloatNode(EntityNode):
    """A node that outputs a single float value (defined declaratively)."""

    # Class attributes define the node's properties and sockets
    node_type = "constant.float"
    input_socket_definitions = [
        SocketDef(name="in_float", type=float, visual_type_key="number", accepts_connection=False),
    ]
    output_socket_definitions = [
        SocketDef(name="out_float", type=float, visual_type_key="number"),
    ]

    def process(self):
        self.output_sockets["out_float"].value = self.input_sockets["in_float"].value
        return self.output_sockets["out_float"].value


class StringNode(EntityNode):
    """A node that outputs a single string value (defined declaratively)."""

    # Class attributes define the node's properties and sockets
    node_type = "string.text"
    input_socket_definitions = [
        SocketDef(name="in_string", type=str, visual_type_key="string", accepts_connection=False),
    ]
    output_socket_definitions = [
        SocketDef(name="out_string", type=str, visual_type_key="string"),
    ]

    def process(self):
        self.output_sockets["out_string"].value = self.input_sockets["in_string"].value
        return self.output_sockets["out_string"].value


class AddNode(EntityNode):
    """A node that adds two integer inputs and outputs the result (declaratively)."""

    node_type = "math.add"
    input_socket_definitions = [
        SocketDef(name="a", type=int, visual_type_key="number"),
        SocketDef(name="b", type=int, visual_type_key="number"),
    ]
    output_socket_definitions = [SocketDef(name="result", type=int, visual_type_key="number")]

    def process(self):
        # Access sockets created by the base class based on definitions
        a_socket = self.input_sockets["a"]
        b_socket = self.input_sockets["b"]

        # Get input values (assuming defaults or connections provide them)
        # Sockets should have a default value (e.g., None or 0) upon creation
        # or the graph executor handles pulling values from connections.
        a_value = 0
        b_value = 0

        if a_socket.is_connected():
            connected_socket = a_socket.connections[0]
            a_value = connected_socket.value if connected_socket.value is not None else 0
        elif a_socket.value is not None:
            a_value = a_socket.value  # Use default value if not connected

        if b_socket.is_connected():
            connected_socket = b_socket.connections[0]
            b_value = connected_socket.value if connected_socket.value is not None else 0
        elif b_socket.value is not None:
            b_value = b_socket.value  # Use default value if not connected

        result = a_value + b_value
        self.output_sockets["result"].value = result
        logger.debug(f"AddNode ({self.name}): {a_value} + {b_value} = {result}")


class MultiplyNode(EntityNode):
    """A node that multiplies a float and an integer and outputs the result (declaratively)."""

    node_type = "math.multiply"
    input_socket_definitions = [
        SocketDef(name="a", type=float, visual_type_key="number"),
        SocketDef(name="b", type=int, visual_type_key="number"),
    ]
    output_socket_definitions = [SocketDef(name="result", type=float)]

    def process(self):
        # Access sockets created by the base class based on definitions
        a_socket = self.input_sockets["a"]
        b_socket = self.input_sockets["b"]

        # Get input values
        a_value = 0.0
        b_value = 0

        if a_socket.is_connected():
            connected_socket = a_socket.connections[0]
            a_value = connected_socket.value if connected_socket.value is not None else 0.0
        elif a_socket.value is not None:
            a_value = a_socket.value  # Use default value if not connected

        if b_socket.is_connected():
            connected_socket = b_socket.connections[0]
            b_value = connected_socket.value if connected_socket.value is not None else 0
        elif b_socket.value is not None:
            b_value = b_socket.value  # Use default value if not connected

        result = a_value * b_value
        self.output_sockets["result"].value = result
        logger.debug(f"MultiplyNode ({self.name}): {a_value} * {b_value} = {result}")


class ConcatNode(EntityNode):
    """A node that concatenates two string inputs and outputs the result (declaratively)."""

    node_type = "string.concat"
    input_socket_definitions = [
        SocketDef(name="a", type=str, visual_type_key="string"),
        SocketDef(name="b", type=str, visual_type_key="string"),
    ]
    output_socket_definitions = [SocketDef(name="result", type=str, visual_type_key="string")]

    def process(self):
        # Access sockets created by the base class based on definitions
        a_socket = self.input_sockets["a"]
        b_socket = self.input_sockets["b"]

        # Get input values
        a_value = ""
        b_value = ""

        if a_socket.is_connected():
            connected_socket = a_socket.connections[0]
            a_value = connected_socket.value if connected_socket.value is not None else ""
        elif a_socket.value is not None:
            a_value = a_socket.value  # Use default value if not connected

        if b_socket.is_connected():
            connected_socket = b_socket.connections[0]
            b_value = connected_socket.value if connected_socket.value is not None else ""
        elif b_socket.value is not None:
            b_value = b_socket.value  # Use default value if not connected

        result = a_value + b_value
        self.output_sockets["result"].value = result
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

    # Add nodes to graph
    graph.add_node(int_node)
    graph.add_node(float_node)
    graph.add_node(multiply_node)
    graph.add_node(string_node1)
    graph.add_node(string_node2)
    graph.add_node(concat_node)

    # Set initial values for the nodes
    int_node.input_sockets["in_int"].value = 5
    float_node.input_sockets["in_float"].value = 2.5
    string_node1.input_sockets["in_string"].value = "Hello, "
    string_node2.input_sockets["in_string"].value = "World!"

    # Connect float_node and int_node to multiply_node
    success1, reason1 = graph.connect_sockets((float_node.id, "out_float"), (multiply_node.id, "a"))
    success2, reason2 = graph.connect_sockets((int_node.id, "out_int"), (multiply_node.id, "b"))
    if not success1:
        logger.error(f"Failed to connect float_node to multiply_node: {reason1}")
    if not success2:
        logger.error(f"Failed to connect int_node to multiply_node: {reason2}")

    # Connect string nodes to concat node
    success3, reason3 = graph.connect_sockets((string_node1.id, "out_string"), (concat_node.id, "a"))
    success4, reason4 = graph.connect_sockets((string_node2.id, "out_string"), (concat_node.id, "b"))
    if not success3:
        logger.error(f"Failed to connect string_node1 to concat_node: {reason3}")
    if not success4:
        logger.error(f"Failed to connect string_node2 to concat_node: {reason4}")

    return graph


# --- Launch the app using the EdonApplication class ---
if __name__ == "__main__":
    # Create and run the application with our custom graph and node registry
    app = EdonApplication(debug_mode=True)

    # Set our custom graph and node registry using property setters
    app.entity_graph = create_sample_graph()
    app.node_registry = custom_node_registry

    # Run the application
    import sys

sys.exit(app.run())
