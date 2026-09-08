"""Topological ordering properties for independently constructed DAGs."""

import hypothesis.strategies as st
from hypothesis import given

from edon.executor import ExecutionEngine
from edon.graph import EntityGraph
from edon.node import EntityNode
from edon.types import EdgeKey
from tests.fixtures.nodes import AddNode


@st.composite
def acyclic_graphs_strategy(draw: st.DrawFn) -> EntityGraph:
    """Only link lower-ranked nodes to higher-ranked nodes, never creating cycles.

    All sockets have integer types. Each target gets at most one source, so every
    generated edge must be accepted; rejection is a failure, not a discarded case.
    Insertion order is shuffled to avoid giving the sorter an already sorted graph.
    """
    graph: EntityGraph = EntityGraph()
    node_count: int = draw(st.integers(min_value=0, max_value=8))
    nodes: list[AddNode] = [AddNode(name=f"Rank_{index}") for index in range(node_count)]
    for node in draw(st.permutations(nodes)):
        graph.add_node(node)

    for rank, target in enumerate(nodes):
        for input_name in ("a", "b"):
            source_rank: int = draw(st.integers(min_value=-1, max_value=rank - 1))
            if source_rank == -1:
                continue
            edge: EdgeKey = EdgeKey(
                source=nodes[source_rank].sockets["result"].address,
                target=target.sockets[input_name].address,
            )
            success, reason = graph.link_sockets(edge)
            assert success, f"Valid DAG edge rejected: {edge}: {reason}"
    return graph


@given(graph=acyclic_graphs_strategy())
def test_toposort_output_nodes_are_valid(graph: EntityGraph) -> None:
    engine: ExecutionEngine = ExecutionEngine()
    sorted_nodes: list[EntityNode] = engine._topological_sort(graph)
    assert len(sorted_nodes) == len(graph.nodes)
    assert {node.id for node in sorted_nodes} == set(graph.nodes)


@given(graph=acyclic_graphs_strategy())
def test_toposort_dependencies_precede_dependents(graph: EntityGraph) -> None:
    engine: ExecutionEngine = ExecutionEngine()
    sorted_nodes: list[EntityNode] = engine._topological_sort(graph)
    positions: dict[str, int] = {node.id: index for index, node in enumerate(sorted_nodes)}
    for edge in graph.edges:
        assert positions[edge.source.node_id] < positions[edge.target.node_id]
