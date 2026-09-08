"""Shared pytest fixtures for Edon tests.

This module provides common fixtures that can be used across multiple test files,
including node instances, graphs, and other test utilities.
"""

import os

import pytest
from hypothesis import settings

from edon.graph import EntityGraph
from edon.executor import ExecutionEngine
from tests.fixtures.nodes import (
    IntegerNode,
    FloatNode,
    StringNode,
    AddNode,
    MultiplyNode,
    ConcatNode,
    TEST_NODE_REGISTRY,
)


# Select once, before test modules are imported. Both profiles retain shrinking
# and health checks; CI increases the workload and uses deterministic generation.
settings.register_profile(
    "dev",
    max_examples=50,
    stateful_step_count=50,
    deadline=None,
    print_blob=True,
)
settings.register_profile(
    "ci",
    max_examples=200,
    stateful_step_count=100,
    deadline=None,
    derandomize=True,
    print_blob=True,
)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "dev"))


@pytest.fixture
def execution_engine():
    """Provide a standard ExecutionEngine for tests."""
    return ExecutionEngine()


@pytest.fixture
def empty_graph():
    """Provide an empty EntityGraph for tests."""
    return EntityGraph()


@pytest.fixture
def integer_node():
    """Provide an IntegerNode instance."""
    return IntegerNode()


@pytest.fixture
def float_node():
    """Provide a FloatNode instance."""
    return FloatNode()


@pytest.fixture
def add_node():
    """Provide an AddNode instance."""
    return AddNode()


@pytest.fixture
def multiply_node():
    """Provide a MultiplyNode instance."""
    return MultiplyNode()


@pytest.fixture
def string_node():
    """Provide a StringNode instance."""
    return StringNode()


@pytest.fixture
def concat_node():
    """Provide a ConcatNode instance."""
    return ConcatNode()


@pytest.fixture
def simple_add_graph():
    """Provide a simple graph with two integers feeding into an add node."""
    from edon.types import EdgeKey, SocketAddress, SocketRole

    graph = EntityGraph()

    # Create nodes
    int1 = IntegerNode()
    int2 = IntegerNode()
    add = AddNode()

    # Set values
    int1.sockets["trg_int"].value = 5
    int2.sockets["trg_int"].value = 3

    # Add to graph
    graph.add_node(int1)
    graph.add_node(int2)
    graph.add_node(add)

    # Create connections
    edge1 = EdgeKey(
        source=SocketAddress(int1.id, "src_int", SocketRole.SOURCE),
        target=SocketAddress(add.id, "a", SocketRole.TARGET),
    )
    edge2 = EdgeKey(
        source=SocketAddress(int2.id, "src_int", SocketRole.SOURCE),
        target=SocketAddress(add.id, "b", SocketRole.TARGET),
    )

    graph.link_sockets(edge1)
    graph.link_sockets(edge2)

    return graph, (int1, int2, add)


@pytest.fixture
def node_registry():
    """Provide the test node registry."""
    return TEST_NODE_REGISTRY
