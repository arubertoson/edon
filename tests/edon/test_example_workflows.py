"""Example workflow tests demonstrating Edon functionality.

These tests serve as both integration tests and runnable examples,
showing how to use Edon's core features including sub-graphs.
"""

import pytest
from loguru import logger

from edon.graph import EntityGraph
from edon.executor import ExecutionEngine
from edon.subgraph import SubGraphNode
from edon.types import SocketAddress, SocketRole, EdgeKey
from tests.fixtures.nodes import IntegerNode, AddNode, MultiplyNode, FloatNode, ConcatNode, StringNode


class TestBasicWorkflows:
    """Test basic graph execution workflows."""

    def test_simple_math_workflow(self, execution_engine):
        """Example: Create a simple math workflow and execute it."""
        # Create a graph that computes (5 + 3) * 2.5 = 20.0
        graph = EntityGraph()
        
        # Create nodes
        int1 = IntegerNode()
        int2 = IntegerNode()
        float1 = FloatNode()
        add_node = AddNode()
        multiply_node = MultiplyNode()
        
        # Set initial values
        int1.sockets["trg_int"].value = 5
        int2.sockets["trg_int"].value = 3
        float1.sockets["trg_float"].value = 2.5
        
        # Add nodes to graph
        for node in [int1, int2, float1, add_node, multiply_node]:
            graph.add_node(node)
        
        # Create connections: int1 + int2 -> add_node
        edge1 = EdgeKey(
            source=SocketAddress(int1.id, "src_int", SocketRole.SOURCE),
            target=SocketAddress(add_node.id, "a", SocketRole.TARGET)
        )
        edge2 = EdgeKey(
            source=SocketAddress(int2.id, "src_int", SocketRole.SOURCE),
            target=SocketAddress(add_node.id, "b", SocketRole.TARGET)
        )
        
        # Connect add result and float to multiply
        edge3 = EdgeKey(
            source=SocketAddress(add_node.id, "result", SocketRole.SOURCE),
            target=SocketAddress(multiply_node.id, "b", SocketRole.TARGET)
        )
        edge4 = EdgeKey(
            source=SocketAddress(float1.id, "src_float", SocketRole.SOURCE),
            target=SocketAddress(multiply_node.id, "a", SocketRole.TARGET)
        )
        
        # Link all edges
        for edge in [edge1, edge2, edge3, edge4]:
            success, reason = graph.link_sockets(edge)
            assert success, f"Failed to link {edge}: {reason}"
        
        # Execute the graph
        execution_engine.execute_graph(graph)
        
        # Verify the result: (5 + 3) * 2.5 = 20.0
        final_result = multiply_node.sockets["result"].value
        assert final_result == 20.0, f"Expected 20.0, got {final_result}"
        
        logger.info(f"Math workflow result: {final_result}")

    def test_string_processing_workflow(self, execution_engine):
        """Example: Create a string processing workflow."""
        graph = EntityGraph()
        
        # Create nodes for string concatenation
        str1 = StringNode()
        str2 = StringNode()
        str3 = StringNode()
        concat1 = ConcatNode()
        concat2 = ConcatNode()
        
        # Set initial values
        str1.sockets["trg_text"].value = "Hello"
        str2.sockets["trg_text"].value = ", "
        str3.sockets["trg_text"].value = "World!"
        
        # Add nodes to graph
        for node in [str1, str2, str3, concat1, concat2]:
            graph.add_node(node)
        
        # Create connections: str1 + str2 -> concat1, concat1 + str3 -> concat2
        edges = [
            EdgeKey(
                source=SocketAddress(str1.id, "src_text", SocketRole.SOURCE),
                target=SocketAddress(concat1.id, "a", SocketRole.TARGET)
            ),
            EdgeKey(
                source=SocketAddress(str2.id, "src_text", SocketRole.SOURCE),
                target=SocketAddress(concat1.id, "b", SocketRole.TARGET)
            ),
            EdgeKey(
                source=SocketAddress(concat1.id, "result", SocketRole.SOURCE),
                target=SocketAddress(concat2.id, "a", SocketRole.TARGET)
            ),
            EdgeKey(
                source=SocketAddress(str3.id, "src_text", SocketRole.SOURCE),
                target=SocketAddress(concat2.id, "b", SocketRole.TARGET)
            ),
        ]
        
        # Link all edges
        for edge in edges:
            success, reason = graph.link_sockets(edge)
            assert success, f"Failed to link {edge}: {reason}"
        
        # Execute the graph
        execution_engine.execute_graph(graph)
        
        # Verify the result
        final_result = concat2.sockets["result"].value
        assert final_result == "Hello, World!", f"Expected 'Hello, World!', got '{final_result}'"
        
        logger.info(f"String workflow result: '{final_result}'")


class TestSubGraphWorkflows:
    """Test sub-graph functionality with real-world examples."""

    def test_reusable_math_component(self, execution_engine):
        """Example: Create a reusable 'AddTwo' sub-graph component."""
        # Create the internal graph for the sub-graph
        internal_graph = EntityGraph()
        
        # Create an AddNode that will be wrapped in the sub-graph
        add_node = AddNode()
        internal_graph.add_node(add_node)
        
        # Create the sub-graph node
        add_two_subgraph = SubGraphNode(
            name="AddTwoNumbers",
            internal_graph=internal_graph,
            proxy_target_mappings={
                "first_number": SocketAddress(add_node.id, "a", SocketRole.TARGET),
                "second_number": SocketAddress(add_node.id, "b", SocketRole.TARGET)
            },
            proxy_source_mappings={
                "sum": SocketAddress(add_node.id, "result", SocketRole.SOURCE)
            }
        )
        
        # Use the sub-graph in a larger workflow
        main_graph = EntityGraph()
        
        # Create input nodes
        input1 = IntegerNode()
        input2 = IntegerNode()
        input1.sockets["trg_int"].value = 10
        input2.sockets["trg_int"].value = 25
        
        # Add nodes to main graph
        main_graph.add_node(input1)
        main_graph.add_node(input2)
        main_graph.add_node(add_two_subgraph)
        
        # Connect inputs to sub-graph
        edges = [
            EdgeKey(
                source=SocketAddress(input1.id, "src_int", SocketRole.SOURCE),
                target=SocketAddress(add_two_subgraph.id, "first_number", SocketRole.TARGET)
            ),
            EdgeKey(
                source=SocketAddress(input2.id, "src_int", SocketRole.SOURCE),
                target=SocketAddress(add_two_subgraph.id, "second_number", SocketRole.TARGET)
            ),
        ]
        
        for edge in edges:
            success, reason = main_graph.link_sockets(edge)
            assert success, f"Failed to link {edge}: {reason}"
        
        # Execute the main graph
        execution_engine.execute_graph(main_graph)
        
        # Verify the result
        result = add_two_subgraph.sockets["sum"].value
        assert result == 35, f"Expected 35, got {result}"
        
        logger.info(f"Reusable math component result: {result}")

    def test_parameterized_subgraph(self, execution_engine):
        """Example: Create a sub-graph with configurable parameters."""
        # Create internal graph with a configurable multiplier
        internal_graph = EntityGraph()
        
        multiplier_node = FloatNode()
        input_node = IntegerNode()
        multiply_node = MultiplyNode()
        
        # Set default multiplier value
        multiplier_node.sockets["trg_float"].value = 1.0
        
        internal_graph.add_node(multiplier_node)
        internal_graph.add_node(input_node)
        internal_graph.add_node(multiply_node)
        
        # Connect internal nodes
        internal_edges = [
            EdgeKey(
                source=SocketAddress(multiplier_node.id, "src_float", SocketRole.SOURCE),
                target=SocketAddress(multiply_node.id, "a", SocketRole.TARGET)
            ),
            EdgeKey(
                source=SocketAddress(input_node.id, "src_int", SocketRole.SOURCE),
                target=SocketAddress(multiply_node.id, "b", SocketRole.TARGET)
            ),
        ]
        
        for edge in internal_edges:
            internal_graph.link_sockets(edge)
        
        # Create sub-graph with parameter exposure
        scaling_subgraph = SubGraphNode(
            name="ScalingComponent",
            internal_graph=internal_graph,
            proxy_target_mappings={
                "input_value": SocketAddress(input_node.id, "trg_int", SocketRole.TARGET)
            },
            proxy_source_mappings={
                "scaled_output": SocketAddress(multiply_node.id, "result", SocketRole.SOURCE)
            }
        )
        
        # Expose the multiplier as a parameter
        scaling_subgraph.expose_socket_as_parameter(
            SocketAddress(multiplier_node.id, "trg_float", SocketRole.TARGET),
            "scale_factor"
        )
        
        # Configure the parameter
        scaling_subgraph.set_parameter_value("scale_factor", 3.5)
        
        # Use in main graph
        main_graph = EntityGraph()
        input_source = IntegerNode()
        input_source.sockets["trg_int"].value = 10
        
        main_graph.add_node(input_source)
        main_graph.add_node(scaling_subgraph)
        
        # Connect input
        edge = EdgeKey(
            source=SocketAddress(input_source.id, "src_int", SocketRole.SOURCE),
            target=SocketAddress(scaling_subgraph.id, "input_value", SocketRole.TARGET)
        )
        main_graph.link_sockets(edge)
        
        # Execute
        execution_engine.execute_graph(main_graph)
        
        # Verify: 10 * 3.5 = 35.0
        result = scaling_subgraph.sockets["scaled_output"].value
        assert result == 35.0, f"Expected 35.0, got {result}"
        
        logger.info(f"Parameterized sub-graph result: {result}")

    def test_nested_subgraphs_workflow(self, execution_engine):
        """Example: Create nested sub-graphs for complex workflows."""
        # This test demonstrates the power of hierarchical composition
        
        # Level 1: Create a simple "AddTwo" sub-graph
        add_internal = EntityGraph()
        add_node = AddNode()
        add_internal.add_node(add_node)
        
        add_two_subgraph = SubGraphNode(
            name="AddTwo",
            internal_graph=add_internal,
            proxy_target_mappings={
                "a": SocketAddress(add_node.id, "a", SocketRole.TARGET),
                "b": SocketAddress(add_node.id, "b", SocketRole.TARGET)
            },
            proxy_source_mappings={
                "result": SocketAddress(add_node.id, "result", SocketRole.SOURCE)
            }
        )
        
        # Level 2: Create a "DoubleAdd" sub-graph that uses AddTwo
        double_add_internal = EntityGraph()
        add_two_instance = SubGraphNode(
            name="InnerAddTwo",
            internal_graph=add_internal.copy() if hasattr(add_internal, 'copy') else EntityGraph(),
            proxy_target_mappings=add_two_subgraph.proxy_target_mappings.copy(),
            proxy_source_mappings=add_two_subgraph.proxy_source_mappings.copy()
        )
        # For simplicity, create a fresh AddNode for the inner sub-graph
        inner_add = AddNode()
        double_add_internal.add_node(inner_add)
        add_two_instance.internal_graph = EntityGraph()
        add_two_instance.internal_graph.add_node(inner_add)
        add_two_instance.proxy_target_mappings = {
            "a": SocketAddress(inner_add.id, "a", SocketRole.TARGET),
            "b": SocketAddress(inner_add.id, "b", SocketRole.TARGET)
        }
        add_two_instance.proxy_source_mappings = {
            "result": SocketAddress(inner_add.id, "result", SocketRole.SOURCE)
        }
        add_two_instance._create_proxy_sockets()
        
        multiply_node = MultiplyNode()
        double_add_internal.add_node(add_two_instance)
        double_add_internal.add_node(multiply_node)
        
        # Connect the add result to multiply (double it)
        double_edge = EdgeKey(
            source=SocketAddress(add_two_instance.id, "result", SocketRole.SOURCE),
            target=SocketAddress(multiply_node.id, "b", SocketRole.TARGET)
        )
        double_add_internal.link_sockets(double_edge)
        
        # Create the outer sub-graph
        double_add_subgraph = SubGraphNode(
            name="DoubleAdd",
            internal_graph=double_add_internal,
            proxy_target_mappings={
                "input_a": SocketAddress(add_two_instance.id, "a", SocketRole.TARGET),
                "input_b": SocketAddress(add_two_instance.id, "b", SocketRole.TARGET),
                "multiplier": SocketAddress(multiply_node.id, "a", SocketRole.TARGET)
            },
            proxy_source_mappings={
                "doubled_sum": SocketAddress(multiply_node.id, "result", SocketRole.SOURCE)
            }
        )
        
        # Use in main graph
        main_graph = EntityGraph()
        
        # Create inputs
        input1 = IntegerNode()
        input2 = IntegerNode()
        multiplier = FloatNode()
        
        input1.sockets["trg_int"].value = 7
        input2.sockets["trg_int"].value = 13
        multiplier.sockets["trg_float"].value = 2.0
        
        main_graph.add_node(input1)
        main_graph.add_node(input2)
        main_graph.add_node(multiplier)
        main_graph.add_node(double_add_subgraph)
        
        # Connect inputs
        main_edges = [
            EdgeKey(
                source=SocketAddress(input1.id, "src_int", SocketRole.SOURCE),
                target=SocketAddress(double_add_subgraph.id, "input_a", SocketRole.TARGET)
            ),
            EdgeKey(
                source=SocketAddress(input2.id, "src_int", SocketRole.SOURCE),
                target=SocketAddress(double_add_subgraph.id, "input_b", SocketRole.TARGET)
            ),
            EdgeKey(
                source=SocketAddress(multiplier.id, "src_float", SocketRole.SOURCE),
                target=SocketAddress(double_add_subgraph.id, "multiplier", SocketRole.TARGET)
            ),
        ]
        
        for edge in main_edges:
            success, reason = main_graph.link_sockets(edge)
            assert success, f"Failed to link {edge}: {reason}"
        
        # Execute with nested sub-graphs
        execution_engine.execute_graph(main_graph)
        
        # Verify: (7 + 13) * 2.0 = 40.0
        result = double_add_subgraph.sockets["doubled_sum"].value
        assert result == 40.0, f"Expected 40.0, got {result}"
        
        logger.info(f"Nested sub-graphs result: {result}")


if __name__ == "__main__":
    """Run example workflows as a demonstration."""
    import sys
    from edon.logging import setup_logging
    
    # Setup logging for the demo
    setup_logging("INFO")
    
    # Create test instances
    engine = ExecutionEngine()
    basic_tests = TestBasicWorkflows()
    subgraph_tests = TestSubGraphWorkflows()
    
    print("🚀 Running Edon Example Workflows")
    print("=" * 50)
    
    try:
        print("\n📊 Basic Math Workflow...")
        basic_tests.test_simple_math_workflow(engine)
        print("✅ Math workflow completed successfully!")
        
        print("\n📝 String Processing Workflow...")
        basic_tests.test_string_processing_workflow(engine)
        print("✅ String workflow completed successfully!")
        
        print("\n🔧 Reusable Math Component...")
        subgraph_tests.test_reusable_math_component(engine)
        print("✅ Reusable component workflow completed successfully!")
        
        print("\n⚙️  Parameterized Sub-graph...")
        subgraph_tests.test_parameterized_subgraph(engine)
        print("✅ Parameterized sub-graph workflow completed successfully!")
        
        print("\n🏗️  Nested Sub-graphs...")
        subgraph_tests.test_nested_subgraphs_workflow(engine)
        print("✅ Nested sub-graphs workflow completed successfully!")
        
        print("\n🎉 All example workflows completed successfully!")
        print("   Sub-graph functionality is working as expected.")
        
    except Exception as e:
        print(f"\n❌ Workflow failed: {e}")
        logger.exception("Example workflow failed")
        sys.exit(1)
