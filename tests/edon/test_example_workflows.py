"""Executable examples of graph composition through the current proxy API."""

from edon.executor import ExecutionEngine
from edon.graph import EntityGraph, EntitySubGraphNode
from edon.node import EntityNode
from edon.types import EdgeKey
from tests.fixtures.nodes import (
    AddNode,
    ConcatNode,
    FloatNode,
    IntegerNode,
    MultiplyNode,
    StringNode,
)


def link(
    graph: EntityGraph,
    source: EntityNode,
    output: str,
    target: EntityNode,
    input_name: str,
) -> None:
    edge: EdgeKey = EdgeKey(source.sockets[output].address, target.sockets[input_name].address)
    success, reason = graph.link_sockets(edge)
    assert success, reason


def add_component() -> EntitySubGraphNode:
    addition: AddNode = AddNode()
    component: EntitySubGraphNode = EntitySubGraphNode(name="AddTwo")
    component.internal_graph.add_node(addition)
    component.add_proxy_socket("a", addition.sockets["a"].address)
    component.add_proxy_socket("b", addition.sockets["b"].address)
    component.add_proxy_socket("result", addition.sockets["result"].address)
    return component


def test_simple_math_workflow(execution_engine: ExecutionEngine) -> None:
    graph: EntityGraph = EntityGraph()
    first: IntegerNode = IntegerNode()
    second: IntegerNode = IntegerNode()
    factor: FloatNode = FloatNode()
    addition: AddNode = AddNode()
    multiplication: MultiplyNode = MultiplyNode()
    first.sockets["trg_int"].value = 5
    second.sockets["trg_int"].value = 3
    factor.sockets["trg_float"].value = 2.5
    for node in (first, second, factor, addition, multiplication):
        graph.add_node(node)
    link(graph, first, "src_int", addition, "a")
    link(graph, second, "src_int", addition, "b")
    link(graph, addition, "result", multiplication, "b")
    link(graph, factor, "src_float", multiplication, "a")
    execution_engine.execute_graph(graph)
    assert multiplication.sockets["result"].value == 20.0


def test_string_processing_workflow(execution_engine: ExecutionEngine) -> None:
    graph: EntityGraph = EntityGraph()
    first: StringNode = StringNode()
    second: StringNode = StringNode()
    third: StringNode = StringNode()
    concat_first: ConcatNode = ConcatNode()
    concat_last: ConcatNode = ConcatNode()
    first.sockets["trg_text"].value = "Hello"
    second.sockets["trg_text"].value = ", "
    third.sockets["trg_text"].value = "World!"
    for node in (first, second, third, concat_first, concat_last):
        graph.add_node(node)
    link(graph, first, "src_text", concat_first, "a")
    link(graph, second, "src_text", concat_first, "b")
    link(graph, concat_first, "result", concat_last, "a")
    link(graph, third, "src_text", concat_last, "b")
    execution_engine.execute_graph(graph)
    assert concat_last.sockets["result"].value == "Hello, World!"


def test_reusable_math_component(execution_engine: ExecutionEngine) -> None:
    graph: EntityGraph = EntityGraph()
    component: EntitySubGraphNode = add_component()
    first: IntegerNode = IntegerNode()
    second: IntegerNode = IntegerNode()
    first.sockets["trg_int"].value = 10
    second.sockets["trg_int"].value = 25
    for node in (first, second, component):
        graph.add_node(node)
    link(graph, first, "src_int", component, "a")
    link(graph, second, "src_int", component, "b")
    execution_engine.execute_graph(graph)
    assert component.sockets["result"].value == 35


def test_parameterized_subgraph(execution_engine: ExecutionEngine) -> None:
    component: EntitySubGraphNode = EntitySubGraphNode(name="ScalingComponent")
    factor: FloatNode = FloatNode()
    internal_input: IntegerNode = IntegerNode()
    multiplication: MultiplyNode = MultiplyNode()
    for node in (factor, internal_input, multiplication):
        component.internal_graph.add_node(node)
    link(component.internal_graph, factor, "src_float", multiplication, "a")
    link(component.internal_graph, internal_input, "src_int", multiplication, "b")
    component.add_proxy_socket("input", internal_input.sockets["trg_int"].address)
    component.add_proxy_socket("scale_factor", factor.sockets["trg_float"].address)
    component.add_proxy_socket("output", multiplication.sockets["result"].address)
    component.sockets["scale_factor"].value = 3.5
    graph: EntityGraph = EntityGraph()
    source: IntegerNode = IntegerNode()
    source.sockets["trg_int"].value = 10
    graph.add_node(source)
    graph.add_node(component)
    link(graph, source, "src_int", component, "input")
    execution_engine.execute_graph(graph)
    assert component.sockets["output"].value == 35.0


def test_nested_subgraphs_workflow(execution_engine: ExecutionEngine) -> None:
    inner: EntitySubGraphNode = add_component()
    outer: EntitySubGraphNode = EntitySubGraphNode(name="DoubleAdd")
    multiplication: MultiplyNode = MultiplyNode()
    outer.internal_graph.add_node(inner)
    outer.internal_graph.add_node(multiplication)
    link(outer.internal_graph, inner, "result", multiplication, "b")
    outer.add_proxy_socket("a", inner.sockets["a"].address)
    outer.add_proxy_socket("b", inner.sockets["b"].address)
    outer.add_proxy_socket("factor", multiplication.sockets["a"].address)
    outer.add_proxy_socket("output", multiplication.sockets["result"].address)
    first: IntegerNode = IntegerNode()
    second: IntegerNode = IntegerNode()
    factor: FloatNode = FloatNode()
    first.sockets["trg_int"].value = 7
    second.sockets["trg_int"].value = 13
    factor.sockets["trg_float"].value = 2.0
    graph: EntityGraph = EntityGraph()
    for node in (first, second, factor, outer):
        graph.add_node(node)
    link(graph, first, "src_int", outer, "a")
    link(graph, second, "src_int", outer, "b")
    link(graph, factor, "src_float", outer, "factor")
    execution_engine.execute_graph(graph)
    assert outer.sockets["output"].value == 40.0
