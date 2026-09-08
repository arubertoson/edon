"""Behavioural coverage for the current subgraph proxy and execution API."""

import pytest

from edon.executor import ExecutionEngine
from edon.graph import EntityGraph, EntitySubGraphNode
from edon.node import EntityNode
from edon.types import EdgeKey, current_execution_engine_context, current_graph_context
from tests.fixtures.nodes import AddNode, FloatNode, IntegerNode, MultiplyNode


def connect(
    graph: EntityGraph,
    source: EntityNode,
    source_name: str,
    target: EntityNode,
    target_name: str,
) -> None:
    edge: EdgeKey = EdgeKey(
        source.sockets[source_name].address, target.sockets[target_name].address
    )
    success, reason = graph.link_sockets(edge)
    assert success, reason


def wrap_output(node: EntityNode, output_name: str) -> EntitySubGraphNode:
    subgraph: EntitySubGraphNode = EntitySubGraphNode()
    subgraph.internal_graph.add_node(node)
    subgraph.add_proxy_socket("output", node.sockets[output_name].address)
    return subgraph


def execute_node(node: EntityNode, engine: ExecutionEngine | None = None) -> None:
    graph: EntityGraph = EntityGraph()
    graph.add_node(node)
    active_engine: ExecutionEngine = engine if engine is not None else ExecutionEngine()
    active_engine.execute_graph(graph)


def test_simple_subgraph_creation_and_execution() -> None:
    first: IntegerNode = IntegerNode()
    second: IntegerNode = IntegerNode()
    addition: AddNode = AddNode()
    first.sockets["trg_int"].value = 5
    second.sockets["trg_int"].value = 3
    subgraph: EntitySubGraphNode = wrap_output(addition, "result")
    subgraph.internal_graph.add_node(first)
    subgraph.internal_graph.add_node(second)
    connect(subgraph.internal_graph, first, "src_int", addition, "a")
    connect(subgraph.internal_graph, second, "src_int", addition, "b")

    execute_node(subgraph)

    assert addition.sockets["result"].value == 8
    assert subgraph.sockets["output"].value == 8


def test_subgraph_with_input_parameters() -> None:
    addition: AddNode = AddNode()
    subgraph: EntitySubGraphNode = wrap_output(addition, "result")
    subgraph.add_proxy_socket("input_a", addition.sockets["a"].address)
    subgraph.add_proxy_socket("input_b", addition.sockets["b"].address)
    subgraph.sockets["input_a"].value = 10
    subgraph.sockets["input_b"].value = 15

    execute_node(subgraph)

    assert addition.sockets["a"].value == 10
    assert addition.sockets["b"].value == 15
    assert subgraph.sockets["output"].value == 25


def test_exposed_input_can_be_reconfigured_between_executions() -> None:
    integer: IntegerNode = IntegerNode()
    subgraph: EntitySubGraphNode = wrap_output(integer, "src_int")
    subgraph.add_proxy_socket("number", integer.sockets["trg_int"].address)
    for value in (42, 100, 0):
        subgraph.sockets["number"].value = value
        execute_node(subgraph)
        assert integer.sockets["trg_int"].value == value
        assert subgraph.sockets["output"].value == value


def test_nested_subgraphs_feed_downstream_nodes() -> None:
    addition: AddNode = AddNode()
    addition.sockets["a"].value = 5
    addition.sockets["b"].value = 3
    inner: EntitySubGraphNode = wrap_output(addition, "result")
    multiplication: MultiplyNode = MultiplyNode()
    factor: FloatNode = FloatNode()
    factor.sockets["trg_float"].value = 2.0
    outer: EntitySubGraphNode = wrap_output(multiplication, "result")
    outer.internal_graph.add_node(inner)
    outer.internal_graph.add_node(factor)
    connect(outer.internal_graph, inner, "output", multiplication, "b")
    connect(outer.internal_graph, factor, "src_float", multiplication, "a")

    execute_node(outer)

    assert inner.sockets["output"].value == 8
    assert outer.sockets["output"].value == 16.0


def test_subgraph_dynamic_socket_management() -> None:
    addition: AddNode = AddNode()
    subgraph: EntitySubGraphNode = EntitySubGraphNode()
    subgraph.internal_graph.add_node(addition)
    assert not subgraph.sockets
    subgraph.add_proxy_socket("input", addition.sockets["a"].address)
    subgraph.add_proxy_socket("output", addition.sockets["result"].address)
    assert set(subgraph.sockets) == {"input", "output"}
    subgraph.remove_proxy_socket("input")
    assert set(subgraph.sockets) == {"output"}
    addition.sockets["a"].value = 7
    execute_node(subgraph)
    assert subgraph.sockets["output"].value == 7
    subgraph.add_proxy_socket("input", addition.sockets["a"].address)
    subgraph.sockets["input"].value = 11
    execute_node(subgraph)
    assert subgraph.sockets["output"].value == 11


class FailingNode(IntegerNode):
    def process(self) -> None:
        raise ValueError("Intentional test failure")


def test_subgraph_error_propagation_and_context_restoration() -> None:
    subgraph: EntitySubGraphNode = wrap_output(FailingNode(), "src_int")
    engine: ExecutionEngine = ExecutionEngine(max_depth=2)
    previous_graph: EntityGraph | None = current_graph_context.get()
    previous_engine: ExecutionEngine | None = current_execution_engine_context.get()
    with pytest.raises(ValueError, match="Intentional test failure"):
        execute_node(subgraph, engine)
    assert current_graph_context.get() is previous_graph
    assert current_execution_engine_context.get() is previous_engine
    healthy: IntegerNode = IntegerNode()
    healthy.sockets["trg_int"].value = 42
    replacement: EntitySubGraphNode = wrap_output(healthy, "src_int")
    execute_node(replacement, engine)
    assert replacement.sockets["output"].value == 42


@pytest.mark.parametrize("max_depth, succeeds", [(2, False), (3, True)])
def test_subgraph_depth_boundary(max_depth: int, succeeds: bool) -> None:
    integer: IntegerNode = IntegerNode()
    integer.sockets["trg_int"].value = 42
    inner: EntitySubGraphNode = wrap_output(integer, "src_int")
    outer: EntitySubGraphNode = wrap_output(inner, "output")
    engine: ExecutionEngine = ExecutionEngine(max_depth=max_depth)
    if succeeds:
        execute_node(outer, engine)
        assert outer.sockets["output"].value == 42
    else:
        with pytest.raises(RuntimeError, match="Maximum sub-graph nesting depth"):
            execute_node(outer, engine)
        # A shallower graph must still run after the failed nested execution.
        execute_node(inner, engine)
        assert inner.sockets["output"].value == 42


class DerivedSubgraph(EntitySubGraphNode):
    pass


def test_depth_limit_applies_to_subgraph_subclasses() -> None:
    subgraph: DerivedSubgraph = DerivedSubgraph()
    subgraph.internal_graph.add_node(IntegerNode())
    with pytest.raises(RuntimeError, match="Maximum sub-graph nesting depth"):
        execute_node(subgraph, ExecutionEngine(max_depth=1))
