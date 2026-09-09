"""Focused tests for executing an individual node dependency closure."""

import asyncio

import pytest

from edon.errors import GraphCycleError
from edon.executor import ExecutionEngine, NodeExecutionFailed
from edon.graph import EntityGraph
from edon.node import EntityNode
from edon.types import EdgeKey, SocketDef, SocketType
from tests.fixtures.nodes import AddNode, IntegerNode


class CountingIntegerNode(IntegerNode):
    calls: int = 0

    def process(self) -> None:
        self.calls += 1
        super().process()


class CountingAddNode(AddNode):
    calls: int = 0

    def process(self) -> None:
        self.calls += 1
        super().process()


class AsyncPassthroughNode(EntityNode):
    source_socket_definitions = [SocketDef("output", SocketType.INTEGER)]
    target_socket_definitions = [SocketDef("input", SocketType.INTEGER, default=0)]

    async def process(self) -> None:
        await asyncio.sleep(0)
        self.sockets["output"].value = self.sockets["input"].value


class FailingNode(EntityNode):
    source_socket_definitions = [SocketDef("output", SocketType.INTEGER)]
    target_socket_definitions = [SocketDef("input", SocketType.INTEGER, default=0)]

    def process(self) -> None:
        raise ValueError("invalid value")


def link(
    graph: EntityGraph,
    source: EntityNode,
    output: str,
    target: EntityNode,
    input_name: str,
) -> None:
    linked, reason = graph.link_sockets(
        EdgeKey(source.sockets[output].address, target.sockets[input_name].address)
    )
    assert linked, reason


def test_execute_node_runs_only_upstream_dependencies_and_reuses_values() -> None:
    graph = EntityGraph()
    first = CountingIntegerNode()
    second = CountingIntegerNode()
    target = CountingAddNode()
    unrelated = CountingIntegerNode()
    for node in (first, second, target, unrelated):
        graph.add_node(node)
    graph.set_input_value(first.sockets["trg_int"].address, 2)
    graph.set_input_value(second.sockets["trg_int"].address, 3)
    link(graph, first, "src_int", target, "a")
    link(graph, second, "src_int", target, "b")

    engine = ExecutionEngine()
    asyncio.run(engine.execute_node(graph, target.id))
    asyncio.run(engine.execute_node(graph, target.id))

    assert target.sockets["result"].value == 5
    assert (first.calls, second.calls, target.calls, unrelated.calls) == (1, 1, 1, 0)


def test_input_change_invalidates_cached_execution() -> None:
    graph = EntityGraph()
    source = CountingIntegerNode()
    target = CountingAddNode()
    graph.add_node(source)
    graph.add_node(target)
    link(graph, source, "src_int", target, "a")

    engine = ExecutionEngine()
    asyncio.run(engine.execute_node(graph, target.id))
    graph.set_input_value(source.sockets["trg_int"].address, 4)
    asyncio.run(engine.execute_node(graph, target.id))

    assert source.calls == 2
    assert target.calls == 2
    assert target.sockets["result"].value == 4


def test_resolve_socket_value_works_without_execution_context() -> None:
    graph = EntityGraph()
    source = IntegerNode()
    target = AddNode()
    graph.add_node(source)
    graph.add_node(target)
    link(graph, source, "src_int", target, "a")
    graph.set_input_value(source.sockets["trg_int"].address, 7)
    asyncio.run(ExecutionEngine().execute_node(graph, target.id))

    assert graph.resolve_socket_value(target.sockets["a"].address) == 7


def test_failure_is_attached_to_the_failing_node() -> None:
    graph = EntityGraph()
    failure = FailingNode()
    target = CountingAddNode()
    graph.add_node(failure)
    graph.add_node(target)
    link(graph, failure, "output", target, "a")

    with pytest.raises(NodeExecutionFailed) as raised:
        asyncio.run(ExecutionEngine().execute_node(graph, target.id))

    assert raised.value.node_id == failure.id
    assert isinstance(failure.execution_error, ValueError)
    assert failure.execution_dirty
    assert target.calls == 0


def test_async_node_process_is_awaited() -> None:
    graph = EntityGraph()
    node = AsyncPassthroughNode()
    graph.add_node(node)
    graph.set_input_value(node.sockets["input"].address, 9)

    asyncio.run(ExecutionEngine().execute_node(graph, node.id))

    assert node.sockets["output"].value == 9


def test_cycle_in_execution_subset_is_rejected() -> None:
    graph = EntityGraph()
    first = AddNode()
    second = AddNode()
    graph.add_node(first)
    graph.add_node(second)
    graph.edges.update(
        {
            EdgeKey(first.sockets["result"].address, second.sockets["a"].address),
            EdgeKey(second.sockets["result"].address, first.sockets["a"].address),
        }
    )

    with pytest.raises(GraphCycleError):
        asyncio.run(ExecutionEngine().execute_node(graph, first.id))
