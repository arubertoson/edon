"""Integration tests for sub-graph functionality.

These tests validate the complete sub-graph workflow including creation,
parameter exposure, proxy socket mapping, and execution.
"""

import pytest
from loguru import logger

from edon.graph import EntityGraph
from edon.executor import ExecutionEngine
from edon.subgraph import SubGraphNode, ParameterMapping
from edon.types import SocketAddress, SocketRole, SocketDef, SocketType
from tests.fixtures.nodes import IntegerNode, AddNode, MultiplyNode, FloatNode


class TestSubGraphIntegration:
    """Integration tests for SubGraphNode functionality."""

    def test_simple_subgraph_creation_and_execution(self):
        """Test creating a simple sub-graph with two nodes and executing it."""
        # Create internal graph: IntegerNode -> AddNode
        internal_graph = EntityGraph()

        # Create nodes for internal graph
        int_node1 = IntegerNode()
        int_node2 = IntegerNode()
        add_node = AddNode()

        # Set initial values
        int_node1.sockets["trg_int"].value = 5
        int_node2.sockets["trg_int"].value = 3

        # Add nodes to internal graph
        internal_graph.add_node(int_node1)
        internal_graph.add_node(int_node2)
        internal_graph.add_node(add_node)

        # Create connections within internal graph
        from edon.types import EdgeKey

        edge1 = EdgeKey(
            source=SocketAddress(int_node1.id, "src_int", SocketRole.SOURCE),
            target=SocketAddress(add_node.id, "a", SocketRole.TARGET),
        )
        edge2 = EdgeKey(
            source=SocketAddress(int_node2.id, "src_int", SocketRole.SOURCE),
            target=SocketAddress(add_node.id, "b", SocketRole.TARGET),
        )

        success1, _ = internal_graph.link_sockets(edge1)
        success2, _ = internal_graph.link_sockets(edge2)
        assert success1 and success2, "Failed to create internal connections"

        # Create SubGraphNode
        subgraph_node = SubGraphNode(
            name="AddTwoNumbers",
            internal_graph=internal_graph,
            proxy_source_mappings={
                "result": SocketAddress(add_node.id, "result", SocketRole.SOURCE)
            },
        )

        # Create parent graph with the sub-graph
        parent_graph = EntityGraph()
        parent_graph.add_node(subgraph_node)

        # Execute the parent graph (which should execute the sub-graph)
        engine = ExecutionEngine()
        engine.execute_graph(parent_graph)

        # Verify the result
        result_socket = subgraph_node.sockets["result"]
        assert result_socket.value == 8, f"Expected 8, got {result_socket.value}"

    def test_subgraph_with_input_parameters(self):
        """Test sub-graph with exposed input parameters."""
        # Create internal graph: AddNode only
        internal_graph = EntityGraph()
        add_node = AddNode()
        internal_graph.add_node(add_node)

        # Create SubGraphNode with input and output proxy mappings
        subgraph_node = SubGraphNode(
            name="ParameterizedAdd",
            internal_graph=internal_graph,
            proxy_target_mappings={
                "input_a": SocketAddress(add_node.id, "a", SocketRole.TARGET),
                "input_b": SocketAddress(add_node.id, "b", SocketRole.TARGET),
            },
            proxy_source_mappings={
                "output": SocketAddress(add_node.id, "result", SocketRole.SOURCE)
            },
        )

        # Verify proxy sockets were created
        assert "input_a" in subgraph_node.sockets
        assert "input_b" in subgraph_node.sockets
        assert "output" in subgraph_node.sockets

        # Set input values on proxy sockets
        subgraph_node.sockets["input_a"].value = 10
        subgraph_node.sockets["input_b"].value = 15

        # Create parent graph and execute
        parent_graph = EntityGraph()
        parent_graph.add_node(subgraph_node)

        engine = ExecutionEngine()
        engine.execute_graph(parent_graph)

        # Verify the result
        assert subgraph_node.sockets["output"].value == 25

    def test_subgraph_parameter_exposure(self):
        """Test exposing internal sockets as configurable parameters."""
        # Create internal graph with IntegerNode
        internal_graph = EntityGraph()
        int_node = IntegerNode()
        int_node.sockets["trg_int"].value = 42  # Initial value
        internal_graph.add_node(int_node)

        # Create SubGraphNode
        subgraph_node = SubGraphNode(
            name="ConfigurableInteger",
            internal_graph=internal_graph,
            proxy_source_mappings={
                "value": SocketAddress(int_node.id, "src_int", SocketRole.SOURCE)
            },
        )

        # Expose the integer input as a parameter
        subgraph_node.expose_socket_as_parameter(
            SocketAddress(int_node.id, "trg_int", SocketRole.TARGET), "number_value"
        )

        # Verify parameter was created
        assert len(subgraph_node.parameter_mappings) == 1
        assert "number_value" in subgraph_node.parameter_values
        assert subgraph_node.parameter_values["number_value"] == 42

        # Change parameter value
        subgraph_node.set_parameter_value("number_value", 100)
        assert subgraph_node.parameter_values["number_value"] == 100

        # Execute and verify parameter was applied
        parent_graph = EntityGraph()
        parent_graph.add_node(subgraph_node)

        engine = ExecutionEngine()
        engine.execute_graph(parent_graph)

        # The parameter should have been applied to the internal socket
        assert int_node.sockets["trg_int"].value == 100
        assert subgraph_node.sockets["value"].value == 100

    def test_nested_subgraphs(self):
        """Test sub-graphs containing other sub-graphs (nested execution)."""
        # Create inner sub-graph: IntegerNode -> AddNode
        inner_graph = EntityGraph()
        int_node1 = IntegerNode()
        int_node2 = IntegerNode()
        add_node = AddNode()

        int_node1.sockets["trg_int"].value = 5
        int_node2.sockets["trg_int"].value = 3

        inner_graph.add_node(int_node1)
        inner_graph.add_node(int_node2)
        inner_graph.add_node(add_node)

        # Connect inner graph
        from edon.types import EdgeKey

        edge1 = EdgeKey(
            source=SocketAddress(int_node1.id, "src_int", SocketRole.SOURCE),
            target=SocketAddress(add_node.id, "a", SocketRole.TARGET),
        )
        edge2 = EdgeKey(
            source=SocketAddress(int_node2.id, "src_int", SocketRole.SOURCE),
            target=SocketAddress(add_node.id, "b", SocketRole.TARGET),
        )
        inner_graph.link_sockets(edge1)
        inner_graph.link_sockets(edge2)

        # Create inner SubGraphNode
        inner_subgraph = SubGraphNode(
            name="InnerAdd",
            internal_graph=inner_graph,
            proxy_source_mappings={"sum": SocketAddress(add_node.id, "result", SocketRole.SOURCE)},
        )

        # Create outer sub-graph: InnerSubGraph -> MultiplyNode
        outer_graph = EntityGraph()
        multiply_node = MultiplyNode()
        float_node = FloatNode()
        float_node.sockets["trg_float"].value = 2.0

        outer_graph.add_node(inner_subgraph)
        outer_graph.add_node(multiply_node)
        outer_graph.add_node(float_node)

        # Connect outer graph: inner_subgraph.sum -> multiply.b, float_node -> multiply.a
        edge3 = EdgeKey(
            source=SocketAddress(inner_subgraph.id, "sum", SocketRole.SOURCE),
            target=SocketAddress(multiply_node.id, "b", SocketRole.TARGET),
        )
        edge4 = EdgeKey(
            source=SocketAddress(float_node.id, "src_float", SocketRole.SOURCE),
            target=SocketAddress(multiply_node.id, "a", SocketRole.TARGET),
        )
        outer_graph.link_sockets(edge3)
        outer_graph.link_sockets(edge4)

        # Create outer SubGraphNode
        outer_subgraph = SubGraphNode(
            name="OuterMultiply",
            internal_graph=outer_graph,
            proxy_source_mappings={
                "final_result": SocketAddress(multiply_node.id, "result", SocketRole.SOURCE)
            },
        )

        # Create top-level graph
        top_graph = EntityGraph()
        top_graph.add_node(outer_subgraph)

        # Execute with depth tracking
        engine = ExecutionEngine(max_depth=5)
        engine.execute_graph(top_graph)

        # Verify nested execution: (5 + 3) * 2.0 = 16.0
        assert outer_subgraph.sockets["final_result"].value == 16.0

    def test_subgraph_dynamic_socket_management(self):
        """Test adding and removing proxy sockets dynamically."""
        # Create internal graph
        internal_graph = EntityGraph()
        add_node = AddNode()
        internal_graph.add_node(add_node)

        # Create SubGraphNode with no initial proxy mappings
        subgraph_node = SubGraphNode(name="DynamicSockets", internal_graph=internal_graph)

        # Initially should have no sockets
        assert len(subgraph_node.sockets) == 0

        # Add input proxy socket
        subgraph_node.add_proxy_socket(
            "dynamic_input_a", SocketAddress(add_node.id, "a", SocketRole.TARGET), is_input=True
        )

        # Add output proxy socket
        subgraph_node.add_proxy_socket(
            "dynamic_output",
            SocketAddress(add_node.id, "result", SocketRole.SOURCE),
            is_input=False,
        )

        # Verify sockets were created
        assert "dynamic_input_a" in subgraph_node.sockets
        assert "dynamic_output" in subgraph_node.sockets
        assert len(subgraph_node.sockets) == 2

        # Remove a socket
        subgraph_node.remove_proxy_socket("dynamic_input_a")
        assert "dynamic_input_a" not in subgraph_node.sockets
        assert len(subgraph_node.sockets) == 1

    def test_subgraph_error_propagation(self):
        """Test that errors in sub-graphs are properly propagated."""
        # Create a sub-graph that will cause an error
        internal_graph = EntityGraph()

        # Create a node that will fail during processing
        class FailingNode(IntegerNode):
            def process(self):
                raise ValueError("Intentional test failure")

        failing_node = FailingNode()
        internal_graph.add_node(failing_node)

        subgraph_node = SubGraphNode(name="FailingSubGraph", internal_graph=internal_graph)

        parent_graph = EntityGraph()
        parent_graph.add_node(subgraph_node)

        # Execution should propagate the error
        engine = ExecutionEngine()
        with pytest.raises(ValueError, match="Intentional test failure"):
            engine.execute_graph(parent_graph)

    def test_subgraph_depth_limit(self):
        """Test that deeply nested sub-graphs respect depth limits."""

        def create_nested_subgraph(depth: int) -> SubGraphNode:
            """Recursively create nested sub-graphs."""
            if depth == 0:
                # Base case: simple integer node
                internal_graph = EntityGraph()
                int_node = IntegerNode()
                int_node.sockets["trg_int"].value = depth
                internal_graph.add_node(int_node)

                return SubGraphNode(
                    name=f"Level{depth}",
                    internal_graph=internal_graph,
                    proxy_source_mappings={
                        "value": SocketAddress(int_node.id, "src_int", SocketRole.SOURCE)
                    },
                )
            else:
                # Recursive case: sub-graph containing another sub-graph
                internal_graph = EntityGraph()
                nested_subgraph = create_nested_subgraph(depth - 1)
                internal_graph.add_node(nested_subgraph)

                return SubGraphNode(
                    name=f"Level{depth}",
                    internal_graph=internal_graph,
                    proxy_source_mappings={
                        "value": SocketAddress(nested_subgraph.id, "value", SocketRole.SOURCE)
                    },
                )

        # Create a deeply nested structure that exceeds the default limit
        deep_subgraph = create_nested_subgraph(15)  # Deeper than default max_depth=10

        parent_graph = EntityGraph()
        parent_graph.add_node(deep_subgraph)

        # Should fail due to depth limit
        engine = ExecutionEngine(max_depth=10)
        with pytest.raises(RuntimeError, match="Maximum sub-graph nesting depth"):
            engine.execute_graph(parent_graph)

        # Should succeed with higher limit
        engine_high_limit = ExecutionEngine(max_depth=20)
        engine_high_limit.execute_graph(parent_graph)  # Should not raise


class TestSubGraphCircularImportFix:
    """Tests for addressing the circular import issue."""

    def test_execution_engine_injection(self):
        """Test potential solution: injecting ExecutionEngine into SubGraphNode."""
        # This test explores a potential architectural improvement
        # where we pass the ExecutionEngine to avoid circular imports

        # Create a simple sub-graph
        internal_graph = EntityGraph()
        int_node = IntegerNode()
        int_node.sockets["trg_int"].value = 42
        internal_graph.add_node(int_node)

        subgraph_node = SubGraphNode(
            name="TestInjection",
            internal_graph=internal_graph,
            proxy_source_mappings={
                "value": SocketAddress(int_node.id, "src_int", SocketRole.SOURCE)
            },
        )

        # Current implementation imports ExecutionEngine inside process()
        # This test verifies it works, but we should consider alternatives
        parent_graph = EntityGraph()
        parent_graph.add_node(subgraph_node)

        engine = ExecutionEngine()
        engine.execute_graph(parent_graph)

        assert subgraph_node.sockets["value"].value == 42

        # TODO: Consider architectural improvements:
        # 1. Pass ExecutionEngine instance to SubGraphNode.process()
        # 2. Use dependency injection pattern
        # 3. Create ExecutionContext class
        # 4. Restructure module dependencies
