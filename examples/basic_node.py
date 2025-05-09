from dataclasses import dataclass

# Assuming 'src' is on the PYTHONPATH or the project is structured
# such that 'edon' is a top-level package.
# If /opt/dev/edon is the project root and src/ is a source folder,
# then `from edon.node import Node` etc. should work.
# Alternatively, if PYTHONPATH needs adjustment or relative imports are preferred
# from a script running in examples/, that would be different.
# For now, assuming 'edon' is directly importable.

try:
    # If running examples from the root project directory
    # and src/edon is properly set up as a package
    from edon.node import Node
    from edon.graph import Graph
    from edon.executor import ExecutionEngine  # Import the new ExecutionEngine
except ImportError:
    # Fallback for some environments or if structure is different,
    # though direct import is cleaner if project is set up.
    # This assumes edon is a package within src.
    import sys
    import os

    # Add the 'src' directory to the Python path
    # This is a common pattern for running examples that are not part of the main package
    # when the main package is in a 'src' layout.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    src_path = os.path.join(project_root, "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from edon.node import Node

    # from edon.socket import SocketDirection # Not strictly needed here
    from edon.graph import Graph
    from edon.executor import ExecutionEngine


@dataclass
class ConstantNumberNode(Node):
    """
    A node that outputs a constant numerical value.
    """

    # The actual constant value is stored directly in the node for simplicity,
    # or it could be part of a more complex properties system.
    # For now, we'll assume it's set on an output socket's default value or during process.
    constant_value: float = 0.0

    def __init__(self, name: str = "Constant Number", constant_value: float = 0.0, **kwargs):
        # Define the output socket: name "value", type float
        output_definitions = [("value", float)]

        # Set the node_type for identification/categorization
        super().__init__(
            name=name, node_type="data.constant_number", output_socket_definitions=output_definitions, **kwargs
        )  # Pass id or other base Node args if any
        self.constant_value = constant_value

        # Initialize the output socket's value
        if "value" in self.output_sockets:
            self.output_sockets["value"].value = self.constant_value

    def process(self):
        """Sets the output socket's value to the configured constant_value."""
        # The value is already set in __init__ and directly if self.constant_value changes.
        # However, a process method might be called by a graph runner.
        if "value" in self.output_sockets:
            # Ensure the output socket reflects the current constant_value
            # This is somewhat redundant if constant_value is only set at init,
            # but good practice if it could change.
            self.output_sockets["value"].value = self.constant_value
        # print(f"ConstantNumberNode '{self.name}' processed. Output: {self.constant_value}")


@dataclass
class AddNode(Node):
    """
    A node that adds two numerical inputs and outputs their sum.
    """

    def __init__(self, name: str = "Add", **kwargs):
        # Define input sockets: "a" (float), "b" (float)
        input_definitions = [("a", float), ("b", float)]
        # Define output socket: "sum" (float)
        output_definitions = [("sum", float)]

        super().__init__(
            name=name,
            node_type="math.add",
            input_socket_definitions=input_definitions,
            output_socket_definitions=output_definitions,
            **kwargs,
        )

        # Set default values for input sockets if desired
        if "a" in self.input_sockets:
            self.input_sockets["a"].value = 0.0
        if "b" in self.input_sockets:
            self.input_sockets["b"].value = 0.0

    def process(self):
        """
        Retrieves values from input sockets 'a' and 'b', adds them,
        and sets the result on the output socket 'sum'.
        """
        val_a = 0.0
        val_b = 0.0

        input_socket_a = self.input_sockets.get("a")
        input_socket_b = self.input_sockets.get("b")

        if input_socket_a:
            if input_socket_a.is_connected():
                # Assuming single connection, value from connected output
                # and that the upstream node's process() has set its output value.
                # Also assuming type compatibility is handled by connection logic or is checked here.
                connected_output_a = input_socket_a.connections[0]
                val_a = connected_output_a.value if isinstance(connected_output_a.value, (int, float)) else 0.0
            else:
                # Use the socket's own value (default or set internally)
                val_a = input_socket_a.value if isinstance(input_socket_a.value, (int, float)) else 0.0

        if input_socket_b:
            if input_socket_b.is_connected():
                connected_output_b = input_socket_b.connections[0]
                val_b = connected_output_b.value if isinstance(connected_output_b.value, (int, float)) else 0.0
            else:
                val_b = input_socket_b.value if isinstance(input_socket_b.value, (int, float)) else 0.0

        result = val_a + val_b

        output_socket_sum = self.output_sockets.get("sum")
        if output_socket_sum:
            output_socket_sum.value = result
        # print(f"AddNode '{self.name}' processed. Inputs: ({val_a}, {val_b}), Output: {result}")


# Example Usage (could be in a separate main_demo.py)
if __name__ == "__main__":
    try:
        from edon.graph import Graph
    except ImportError:
        # Fallback, assuming the sys.path modification above worked
        from edon.graph import Graph

    # 1. Create a graph
    graph = Graph()

    # 1.5 Create an execution engine
    engine = ExecutionEngine()

    # 2. Create nodes
    const_node1 = ConstantNumberNode(name="Number_5", constant_value=5.0)
    const_node2 = ConstantNumberNode(name="Number_10", constant_value=10.0)
    add_node = AddNode(name="MyAdder")

    # 3. Add nodes to graph
    graph.add_node(const_node1)
    graph.add_node(const_node2)
    graph.add_node(add_node)

    print(f"Graph nodes: {graph.nodes}")

    # 4. Connect nodes
    # Connect ConstantNumberNode1's "value" output to AddNode's "a" input
    conn1_success = graph.connect_sockets(output_ref=(const_node1.id, "value"), input_ref=(add_node.id, "a"))
    # Connect ConstantNumberNode2's "value" output to AddNode's "b" input
    conn2_success = graph.connect_sockets(output_ref=(const_node2.id, "value"), input_ref=(add_node.id, "b"))

    print(f"Connection 1 successful: {conn1_success}")
    print(f"Connection 2 successful: {conn2_success}")

    # 5. Execute the graph using the engine
    print("\nExecuting graph (initial run)...")
    try:
        engine.execute_graph(graph)
    except RuntimeError as e:
        print(f"Graph execution error: {e}")

    # 6. Check the result
    result_socket = add_node.output_sockets.get("sum")
    if result_socket:
        print(f"Result of {add_node.name} ('{result_socket.name}'): {result_socket.value}")  # Expected: 15.0
    else:
        print(f"Could not find 'sum' output socket on {add_node.name}")

    # Test disconnection
    disconnect_success = graph.disconnect_sockets(output_ref=(const_node1.id, "value"), input_ref=(add_node.id, "a"))
    print(f"Disconnection successful: {disconnect_success}")
    print(f"Socket 'a' on {add_node.name} connected: {add_node.input_sockets['a'].is_connected()}")

    # Execute again
    print("\nExecuting graph (after disconnection)...")
    try:
        engine.execute_graph(graph)
    except RuntimeError as e:
        print(f"Graph execution error: {e}")

    if result_socket:
        print(
            f"Result of {add_node.name} after disconnecting 'a': {result_socket.value}"
        )  # Expected: 10.0 (0.0 + 10.0)
