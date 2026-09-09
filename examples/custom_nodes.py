"""Show how to define, connect, and display custom Edon nodes.

The sample workspace contains two complete flows—a small order calculation and a
text formatter—plus an editable subgraph with promoted inputs and output.
"""

import sys

from loguru import logger

from edon.graph import EntityGraph, EntitySubGraphNode
from edon.node import EntityNode
from edon.nodes.utility import SubgraphPromoterNode
from edon.types import EdgeKey, SocketDef, SocketDisplayState, SocketType
from edon_ui.app import EdonApplication


class IntegerNode(EntityNode):
    """Provide an editable integer value."""

    node_type = "constant.int"
    source_socket_definitions = [
        SocketDef(name="value", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [
        SocketDef(
            name="input",
            socket_type=SocketType.INTEGER,
            display_state=SocketDisplayState.WIDGET,
            default=0,
        ),
    ]

    def process(self) -> None:
        value = self.sockets["input"].value
        self.sockets["value"].value = value
        logger.debug("{} produced {}", self.name, value)


class FloatNode(EntityNode):
    """Provide an editable floating-point value."""

    node_type = "constant.float"
    source_socket_definitions = [
        SocketDef(name="value", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [
        SocketDef(
            name="input",
            socket_type=SocketType.FLOAT,
            display_state=SocketDisplayState.WIDGET,
            default=0.0,
        ),
    ]

    def process(self) -> None:
        value = self.sockets["input"].value
        self.sockets["value"].value = value
        logger.debug("{} produced {}", self.name, value)


class StringNode(EntityNode):
    """Provide an editable single-line string."""

    node_type = "constant.string"
    source_socket_definitions = [
        SocketDef(name="text", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(
            name="input",
            socket_type=SocketType.STRING,
            display_state=SocketDisplayState.WIDGET,
            default="",
        ),
    ]

    def process(self) -> None:
        self.sockets["text"].value = self.sockets["input"].value


class LargeTextNode(EntityNode):
    """Provide multiline text through the popup editor widget."""

    node_type = "constant.large_text"
    source_socket_definitions = [
        SocketDef(name="text", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(
            name="input",
            socket_type=SocketType.LARGE_STRING,
            display_state=SocketDisplayState.WIDGET,
            default="",
        ),
    ]

    def process(self) -> None:
        self.sockets["text"].value = self.sockets["input"].value


class AddNode(EntityNode):
    """Add two integers."""

    node_type = "math.add"
    source_socket_definitions = [
        SocketDef(name="sum", socket_type=SocketType.INTEGER),
    ]
    target_socket_definitions = [
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

    def process(self) -> None:
        a = self.sockets["a"].value
        b = self.sockets["b"].value
        result = a + b
        self.sockets["sum"].value = result
        logger.debug("{} calculated {} + {} = {}", self.name, a, b, result)


class MultiplyNode(EntityNode):
    """Multiply a float by an integer."""

    node_type = "math.multiply"
    source_socket_definitions = [
        SocketDef(name="product", socket_type=SocketType.FLOAT),
    ]
    target_socket_definitions = [
        SocketDef(
            name="price",
            socket_type=SocketType.FLOAT,
            display_state=SocketDisplayState.ALL,
            default=0.0,
        ),
        SocketDef(
            name="quantity",
            socket_type=SocketType.INTEGER,
            display_state=SocketDisplayState.ALL,
            default=0,
        ),
    ]

    def process(self) -> None:
        price = self.sockets["price"].value
        quantity = self.sockets["quantity"].value
        result = price * quantity
        self.sockets["product"].value = result
        logger.debug("{} calculated {} × {} = {}", self.name, price, quantity, result)


class ConcatNode(EntityNode):
    """Join two strings."""

    node_type = "string.concat"
    source_socket_definitions = [
        SocketDef(name="text", socket_type=SocketType.STRING),
    ]
    target_socket_definitions = [
        SocketDef(name="first", socket_type=SocketType.STRING, default=""),
        SocketDef(name="second", socket_type=SocketType.STRING, default=""),
    ]

    def process(self) -> None:
        result = self.sockets["first"].value + self.sockets["second"].value
        self.sockets["text"].value = result
        logger.debug("{} produced {!r}", self.name, result)


class TextOutputNode(EntityNode):
    """Consume text and report it when the graph executes."""

    node_type = "output.text"
    source_socket_definitions = []
    target_socket_definitions = [
        SocketDef(
            name="text",
            socket_type=SocketType.STRING,
            display_state=SocketDisplayState.ALL,
            default="",
        ),
    ]

    def process(self) -> None:
        logger.info("{}: {}", self.name, self.sockets["text"].value)


custom_node_registry: dict[str, type[EntityNode]] = {
    "Integer": IntegerNode,
    "Float": FloatNode,
    "String": StringNode,
    "Large Text": LargeTextNode,
    "Add": AddNode,
    "Multiply": MultiplyNode,
    "Concatenate": ConcatNode,
    "Text Output": TextOutputNode,
    "Subgraph": EntitySubGraphNode,
    "Promote Socket": SubgraphPromoterNode,
}


def _connect(
    graph: EntityGraph,
    source_node: EntityNode,
    source_name: str,
    target_node: EntityNode,
    target_name: str,
) -> None:
    edge = EdgeKey(
        source=source_node.sockets[source_name].address,
        target=target_node.sockets[target_name].address,
    )
    linked, reason = graph.link_sockets(edge)
    assert linked, f"Example contains an invalid connection: {reason}"


def _create_math_subgraph() -> EntitySubGraphNode:
    subgraph = EntitySubGraphNode(name="Reusable Adder")
    adder = AddNode(name="Add Inside Subgraph", position=(50.0, 50.0))
    subgraph.internal_graph.add_node(adder)

    subgraph.add_proxy_socket("first", adder.sockets["a"].address)
    subgraph.add_proxy_socket("second", adder.sockets["b"].address)
    subgraph.add_proxy_socket("result", adder.sockets["sum"].address)
    subgraph.sockets["first"].value = 10
    subgraph.sockets["second"].value = 20
    return subgraph


def create_sample_graph() -> EntityGraph:
    """Create connected flows ordered for the editor's row-based default layout."""
    graph = EntityGraph()

    base_quantity = IntegerNode(name="Base Quantity", position=(50.0, 50.0))
    extra_quantity = IntegerNode(name="Extra Quantity", position=(50.0, 250.0))
    total_quantity = AddNode(name="Total Quantity", position=(350.0, 150.0))
    unit_price = FloatNode(name="Unit Price", position=(650.0, 50.0))
    order_total = MultiplyNode(name="Order Total", position=(950.0, 150.0))

    message = LargeTextNode(name="Message", position=(50.0, 500.0))
    recipient = StringNode(name="Recipient", position=(50.0, 700.0))
    greeting = ConcatNode(name="Greeting", position=(350.0, 600.0))
    preview = TextOutputNode(name="Greeting Preview", position=(650.0, 600.0))
    reusable_adder = _create_math_subgraph()
    reusable_adder.position = (950.0, 600.0)

    # Explicit model positions produce two readable left-to-right workflows.
    for node in (
        base_quantity,
        extra_quantity,
        total_quantity,
        unit_price,
        order_total,
        message,
        recipient,
        greeting,
        preview,
        reusable_adder,
    ):
        graph.add_node(node)

    base_quantity.sockets["input"].value = 3
    extra_quantity.sockets["input"].value = 2
    unit_price.sockets["input"].value = 12.5
    message.sockets["input"].value = "Welcome to Edon, "
    recipient.sockets["input"].value = "graph builder!"

    _connect(graph, base_quantity, "value", total_quantity, "a")
    _connect(graph, extra_quantity, "value", total_quantity, "b")
    _connect(graph, unit_price, "value", order_total, "price")
    _connect(graph, total_quantity, "sum", order_total, "quantity")
    _connect(graph, message, "text", greeting, "first")
    _connect(graph, recipient, "text", greeting, "second")
    _connect(graph, greeting, "text", preview, "text")

    return graph


def main() -> int:
    graph = create_sample_graph()
    app = EdonApplication(custom_node_registry, log_level="DEBUG")
    app.key_mapping.set_binding(("Ctrl+Return",), "graph.execute_node")
    app.load_graph(graph)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
