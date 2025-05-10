import os
import sys
from typing import Any  # For data types

from PySide6.QtWidgets import QApplication

from edon.graph import Graph as EntityGraph
from edon.node import Node as EntityNode
from edon_ui.graph_ui_manager import GraphUIManager

# QGraphicsView is not directly used here anymore, MainWindow handles it.
# from PySide6.QtGui import QPainter # Not directly used here anymore
# GraphicsScene is also not directly instantiated here, MainWindow creates it.
# from edon_ui.graphics_scene import GraphicsScene
from edon_ui.window import MainWindow

# Adjust path to import from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load the stylesheet (similar to main.py)
    # Assuming styles/main_style.qss is relative to src/edon_ui/
    # and this example is run from the project root.
    stylesheet_path = os.path.join(src_path, "edon_ui", "styles", "main_style.qss")
    try:
        with open(stylesheet_path, "r") as f:
            stylesheet = f.read()
        app.setStyleSheet(stylesheet)
    except FileNotFoundError:
        print(f"Warning: Stylesheet not found at {stylesheet_path}. Using default styles.")
    except Exception as e:
        print(f"Error loading stylesheet: {e}")

    # Create the main window
    main_window = MainWindow()

    # Access the scene from the MainWindow
    scene_from_main_window = main_window.scene
    # Alternatively, could be main_window.canvas.scene() if scene wasn't a direct attribute

    # Define a concrete node type for testing
    class MyTestNode(EntityNode):
        def __init__(self, name: str, node_type: str = "test.my_node", **kwargs):
            # Default socket definitions
            default_input_defs = [("input_A", int), ("input_B", str)]
            default_output_defs = [("output_X", float)]

            # Use provided definitions from kwargs if they exist, otherwise use defaults
            # .pop() removes the key from kwargs if it exists, preventing it from being passed again via **kwargs
            current_input_defs = kwargs.pop("input_socket_definitions", default_input_defs)
            current_output_defs = kwargs.pop("output_socket_definitions", default_output_defs)

            super().__init__(
                name=name,
                node_type=node_type,
                input_socket_definitions=current_input_defs,
                output_socket_definitions=current_output_defs,
                **kwargs,  # Pass any other remaining kwargs (like 'id' if provided)
            )

        def process(self):
            print(f"Processing {self.name}")  # Placeholder
            # Actual processing logic would go here
            if "output_X" in self.output_sockets and "input_A" in self.input_sockets:
                # Example: self.output_sockets["output_X"].value = float(self.input_sockets["input_A"].value * 2.0)
                pass

    my_logical_graph = EntityGraph()

    node1_entity = MyTestNode(name="Alpha Node")
    node2_entity = MyTestNode(
        name="Beta Node", input_socket_definitions=[("in_bool", bool)], output_socket_definitions=[("out_any", Any)]
    )
    node3_entity = MyTestNode(name="Gamma Node", input_socket_definitions=[("in_float", float)])

    my_logical_graph.add_node(node1_entity)
    my_logical_graph.add_node(node2_entity)
    my_logical_graph.add_node(node3_entity)

    # Connect Alpha's 'output_X' to Gamma's 'in_float'
    # This connection is made BEFORE populating the scene so the UI can draw it.
    # if node1_entity.output_sockets.get("output_X") and node3_entity.input_sockets.get("in_float"):
    #     connection_success = my_logical_graph.connect_sockets(
    #         (node1_entity.id, "output_X"), (node3_entity.id, "in_float")
    #     )
    #     print(f"Logical connection attempt between Alpha:output_X and Gamma:in_float success: {connection_success}")
    # else:
    #     print("Could not find sockets for test connection: Alpha:output_X or Gamma:in_float.")

    # --- Setup Node Type Registry for GraphUIManager ---
    # This maps string hints (used by UI actions) to actual EntityNode classes.
    node_type_registry = {
        "MyTestNode": MyTestNode  # MyTestNode is defined locally in this example
        # In a real application, EntityNode subclasses would be imported from edon.nodes or a plugin system.
    }

    # --- Initialize GraphUIManager and Populate Scene ---
    graph_ui_manager = GraphUIManager(my_logical_graph, scene_from_main_window, node_type_registry=node_type_registry)
    graph_ui_manager._populate_scene_from_logical_graph()  # Populate UI from the logical model

    # Connect GraphicsView signal to GraphUIManager slot
    # Assuming main_window.canvas is the GraphicsView instance.
    # If main_window.ui.graphics_view is the instance, use that.
    # We need to ensure main_window has an accessible GraphicsView instance.
    # For the example, let's assume main_window.canvas exists and is the GraphicsView.
    # If not, this connection needs to be made where both are available.
    if hasattr(main_window, "canvas") and main_window.canvas is not None:
        graphics_view_instance = main_window.canvas
        # Connect node creation signal
        graphics_view_instance.new_node_requested_at_scene_pos.connect(graph_ui_manager.handle_ui_request_add_node)
        print("Connected GraphicsView.new_node_requested_at_scene_pos to GraphUIManager.handle_ui_request_add_node")

        # Connect node deletion signal
        graphics_view_instance.node_deletion_requested.connect(graph_ui_manager.handle_ui_node_deletion_request)
        print("Connected GraphicsView.node_deletion_requested to GraphUIManager.handle_ui_node_deletion_request")

        # Connect edge deletion signal
        graphics_view_instance.edge_deletion_requested.connect(graph_ui_manager.handle_ui_edge_deletion_request)
        print("Connected GraphicsView.edge_deletion_requested to GraphUIManager.handle_ui_edge_deletion_request")
    else:
        print("Warning: Could not find main_window.canvas to connect UI signals.")
        print("         Please ensure main_window exposes its GraphicsView instance, perhaps as self.canvas.")

    # Assuming Alpha Node has 'output_X' and Beta Node has 'in_bool'
    # (or some other compatible input like 'input_A' if MyTestNode is used for both)
    # Let's connect Alpha's output_X (float) to Beta's input_A (int)
    # This might not be type-compatible by default in edon.socket.Socket.can_connect_to
    # Let's make a more compatible connection for the test:
    # Alpha (output_X: float) to another MyTestNode's input_A (int)
    # OR ensure MyTestNode's input_A is float, or output_X is int, or data_type=Any

    # For a clear test, let's add a third node and connect 1 to 3.

    # Connect Alpha's 'output_X' to Gamma's 'input_A'
    # (Assuming MyTestNode still has output_X:float and input_A:int.
    # edon.socket.Socket.can_connect_to might prevent float -> int.
    # Let's make output_X an int for this test or input_A a float or Any)

    # To ensure connection works, let's redefine MyTestNode slightly for the example:
    # In examples/show_sockets_ui.py, modify MyTestNode's output_defs:
    # output_defs = [("output_X", int)] # Make it int to connect to input_A (int)

    # Then connect:
    # --- This connection block was moved to before scene population ---
    # if node1_entity.output_sockets.get("output_X") and node3_entity.input_sockets.get("in_float"):
    #     connection_success = my_logical_graph.connect_sockets(
    #         (node1_entity.id, "output_X"), (node3_entity.id, "in_float")
    #     )
    #     print(f"Logical connection attempt between Alpha:output_X and Gamma:in_float success: {connection_success}")
    # else:
    #     print("Could not find sockets for test connection.")
    # Show the main window
    main_window.show()
    sys.exit(app.exec())
