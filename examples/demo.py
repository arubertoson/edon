from loguru import logger
from PySide6.QtCore import QPointF

from edon.graph import EntityGraph
from edon.node import EntityNode
from edon_ui.main import main as edon_main


# --- Define a custom node and registry ---
class DemoNode(EntityNode):
    def __init__(self, name: str, **kwargs):
        input_defs = [("input_A", int)]
        output_defs = [("output_X", int)]
        super().__init__(
            name=name,
            node_type="demo.node",
            input_socket_definitions=input_defs,
            output_socket_definitions=output_defs,
            **kwargs,
        )

    def process(self):
        pass


example_node_type_registry = {"DemoNode": DemoNode}

# --- Build a logical graph ---
example_entity_graph = EntityGraph()

node1 = DemoNode(name="Node Alpha")
node2 = DemoNode(name="Node Beta")
example_entity_graph.add_node(node1)
example_entity_graph.add_node(node2)

# Connect Node Alpha's output_X to Node Beta's input_A
example_entity_graph.link_sockets((node1.id, "output_X"), (node2.id, "input_A"))


# --- Function to run demo commands ---
def run_example_commands(window, command_registry, graph_manager):
    logger.info("--- Running example commands via QTimer ---")
    # Example: Add a new node using the command system
    context = {"node_type": "DemoNode", "position": QPointF(300, 50)}
    success = command_registry.execute("add_node", context)
    logger.info(f"AddNode command execution success: {success}")

    # You can add more commands here, for example, to connect nodes programmatically
    # using a hypothetical "connect_nodes_command" if you implement one.


# --- Launch the app using the main entry point ---
if __name__ == "__main__":
    # Pass the pre-populated graph, registry, and the callback
    edon_main(
        entity_graph=example_entity_graph,
        node_registry=example_node_type_registry,
        after_setup_callback=run_example_commands,
    )
