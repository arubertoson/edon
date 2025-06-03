from __future__ import annotations

import os
from typing import TYPE_CHECKING

import hypothesis.strategies as st
from hypothesis import HealthCheck, Phase, assume, settings
from hypothesis.stateful import Bundle, RuleBasedStateMachine, consumes, invariant, rule

from edon.graph import EntityGraph
from edon.subgraph import SubGraphNode
from edon.types import EdgeKey, SocketAddress, SocketRole, SocketDef

# Assuming NODE_TYPES and GraphFuzzer are correctly imported from your existing fuzzer setup
from tests.edon.fuzz.test_graph_fuzzing import GraphFuzzer, NODE_TYPES
from tests.fixtures.nodes import IntegerNode  # For simple internal node creation

if TYPE_CHECKING:
    from edon.node import EntityNode


class SubGraphFuzzer(GraphFuzzer):  # Inherits rules from GraphFuzzer
    # Bundle for SubGraphNode instances specifically
    # While we define it, the current rules consume from active_nodes and then check type.
    # This bundle could be used more directly in future refinements.
    subgraph_nodes_bundle = Bundle("subgraph_nodes_bundle")

    def __init__(self):
        super().__init__()
        self.max_subgraph_depth = 2  # Limit nesting for fuzzing to keep it manageable
        # self.current_depth_map = {} # For more complex depth tracking if needed

    @rule(
        target=GraphFuzzer.active_nodes,  # Add to the general active_nodes bundle
        name=st.text(min_size=1, max_size=10),
        internal_node_count=st.integers(min_value=1, max_value=2),
    )  # Keep internal graph simple
    def add_subgraph_node(self, name: str, internal_node_count: int) -> str:
        # Simplified depth management: assumes this rule adds to the main self.graph
        # For more complex scenarios, one might track depth of the graph being modified.
        # current_parent_depth = self.current_depth_map.get(self.graph.id, 0)
        # assume(current_parent_depth < self.max_subgraph_depth)

        internal_graph = EntityGraph()
        internal_nodes_map = {}

        for i in range(internal_node_count):
            # Use a simple, predictable node type for the internal graph
            internal_node = IntegerNode(name=f"InternalInt_{i}")
            internal_graph.add_node(internal_node)
            internal_nodes_map[internal_node.id] = internal_node

        assume(len(internal_nodes_map) > 0)  # Ensure internal graph is not empty

        # Simplified proxy mapping: expose first target of first node, first source of first node
        # This assumes IntegerNode has 'trg_int' (target) and 'src_int' (source)
        first_internal_node_id = list(internal_nodes_map.keys())[0]
        first_internal_node = internal_nodes_map[first_internal_node_id]

        proxy_targets = {}
        # IntegerNode has 'trg_int' defined in its target_socket_definitions
        if "trg_int" in first_internal_node.target_sockets:
            first_target_socket_def = first_internal_node.target_sockets["trg_int"]
            proxy_targets["proxy_in"] = first_target_socket_def.address

        proxy_sources = {}
        # IntegerNode has 'src_int' defined in its source_socket_definitions
        if "src_int" in first_internal_node.source_sockets:
            first_source_socket_def = first_internal_node.source_sockets["src_int"]
            proxy_sources["proxy_out"] = first_source_socket_def.address

        subgraph_node = SubGraphNode(
            name=name,
            internal_graph=internal_graph,
            proxy_target_mappings=proxy_targets,
            proxy_source_mappings=proxy_sources,
        )
        self.graph.add_node(subgraph_node)
        # self.current_depth_map[subgraph_node.id] = current_parent_depth + 1 # If tracking depth
        return subgraph_node.id

    @rule(subgraph_node_id=consumes(GraphFuzzer.active_nodes), data=st.data())
    def add_proxy_socket_to_subgraph(self, subgraph_node_id: str, data: st.DataObject):
        node = self.graph.get_node(subgraph_node_id)
        assume(isinstance(node, SubGraphNode))  # Ensure we're operating on a SubGraphNode
        subgraph_node: SubGraphNode = node

        internal_nodes_list = list(subgraph_node.internal_graph.nodes.values())
        assume(len(internal_nodes_list) > 0)  # Internal graph must have nodes

        internal_node_to_proxy = data.draw(st.sampled_from(internal_nodes_list))

        is_input_proxy = data.draw(
            st.booleans()
        )  # True for target (input), False for source (output)

        # Select a socket definition from the internal node to proxy
        if is_input_proxy:
            possible_internal_sockets = [
                s_def
                for s_def in internal_node_to_proxy.sockets.values()
                if s_def.role == SocketRole.TARGET
            ]
            assume(len(possible_internal_sockets) > 0)
            internal_socket_def = data.draw(st.sampled_from(possible_internal_sockets))
            proxy_name = f"dyn_in_{internal_socket_def.name}_{len(subgraph_node.sockets)}"  # Ensure unique name
        else:  # Output proxy
            possible_internal_sockets = [
                s_def
                for s_def in internal_node_to_proxy.sockets.values()
                if s_def.role == SocketRole.SOURCE
            ]
            assume(len(possible_internal_sockets) > 0)
            internal_socket_def = data.draw(st.sampled_from(possible_internal_sockets))
            proxy_name = f"dyn_out_{internal_socket_def.name}_{len(subgraph_node.sockets)}"  # Ensure unique name

        assume(
            proxy_name not in subgraph_node.sockets
        )  # Avoid duplicate proxy names on the SubGraphNode

        subgraph_node.add_proxy_socket(
            proxy_name=proxy_name,  # Corrected parameter name
            internal_addr=internal_socket_def.address,  # Corrected parameter name
            is_input=is_input_proxy,
        )

    @rule(subgraph_node_id=consumes(GraphFuzzer.active_nodes))
    def remove_proxy_socket_from_subgraph(self, subgraph_node_id: str):
        node = self.graph.get_node(subgraph_node_id)
        assume(isinstance(node, SubGraphNode))  # Ensure we're operating on a SubGraphNode
        subgraph_node: SubGraphNode = node

        # Get names of proxy sockets from their definitions on the SubGraphNode
        # A socket on SubGraphNode is a proxy if its definition was created via proxying.
        # SubGraphNode.socket_definitions should contain SocketDef instances.
        # We need a reliable way to identify if a SocketDef on SubGraphNode is a proxy.
        # Assuming SubGraphNode.remove_proxy_socket can identify them by name.
        # Or, if SocketDef had an `is_proxy` flag set by SubGraphNode.
        # For now, let's assume any socket on SubGraphNode might be a proxy if it's in mappings.

        proxy_socket_names = list(subgraph_node.proxy_target_mappings.keys()) + list(
            subgraph_node.proxy_source_mappings.keys()
        )

        assume(len(proxy_socket_names) > 0)  # Must have proxy sockets to remove

        proxy_name_to_remove = st.shared(
            st.sampled_from(proxy_socket_names), key="proxy_name_to_remove"
        ).example()

        # Ensure the socket actually exists on the subgraph node before trying to remove
        assume(proxy_name_to_remove in subgraph_node.sockets)

        subgraph_node.remove_proxy_socket(proxy_name_to_remove)

    @invariant()
    def check_subgraph_proxy_sockets_valid(self):
        """
        Ensures that for every SubGraphNode:
        1. Its proxy mappings point to valid sockets in its internal graph.
        2. The corresponding proxy sockets exist on the SubGraphNode itself.
        3. Roles of proxy sockets match roles of internal sockets.
        """
        for node_id, node in self.graph.nodes.items():
            if isinstance(node, SubGraphNode):
                subgraph_node: SubGraphNode = node

                # Check proxy_target_mappings (inputs to the SubGraphNode)
                for proxy_name, internal_addr in subgraph_node.proxy_target_mappings.items():
                    assert proxy_name in subgraph_node.sockets, (
                        f"Proxy target '{proxy_name}' on SubGraphNode '{node_id}' not found in its actual sockets."
                    )
                    assert subgraph_node.sockets[proxy_name].role == SocketRole.TARGET, (
                        f"Proxy target socket '{proxy_name}' on SubGraphNode '{node_id}' has incorrect role."
                    )

                    assert internal_addr.node_id in subgraph_node.internal_graph.nodes, (
                        f"Internal node '{internal_addr.node_id}' for proxy target '{proxy_name}' on SubGraphNode '{node_id}' not in internal graph."
                    )
                    internal_node = subgraph_node.internal_graph.get_node(internal_addr.node_id)
                    assert internal_addr.name in internal_node.sockets, (
                        f"Internal socket '{internal_addr.name}' for proxy target '{proxy_name}' on SubGraphNode '{node_id}' not in internal node '{internal_node.id}'."
                    )
                    assert internal_node.sockets[internal_addr.name].role == SocketRole.TARGET, (
                        f"Internal socket for proxy target '{proxy_name}' on SubGraphNode '{node_id}' has incorrect role."
                    )

                # Check proxy_source_mappings (outputs from the SubGraphNode)
                for proxy_name, internal_addr in subgraph_node.proxy_source_mappings.items():
                    assert proxy_name in subgraph_node.sockets, (
                        f"Proxy source '{proxy_name}' on SubGraphNode '{node_id}' not found in its actual sockets."
                    )
                    assert subgraph_node.sockets[proxy_name].role == SocketRole.SOURCE, (
                        f"Proxy source socket '{proxy_name}' on SubGraphNode '{node_id}' has incorrect role."
                    )

                    assert internal_addr.node_id in subgraph_node.internal_graph.nodes, (
                        f"Internal node '{internal_addr.node_id}' for proxy source '{proxy_name}' on SubGraphNode '{node_id}' not in internal graph."
                    )
                    internal_node = subgraph_node.internal_graph.get_node(internal_addr.node_id)
                    assert internal_addr.name in internal_node.sockets, (
                        f"Internal socket '{internal_addr.name}' for proxy source '{proxy_name}' on SubGraphNode '{node_id}' not in internal node '{internal_node.id}'."
                    )
                    assert internal_node.sockets[internal_addr.name].role == SocketRole.SOURCE, (
                        f"Internal socket for proxy source '{proxy_name}' on SubGraphNode '{node_id}' has incorrect role."
                    )


# Hypothesis settings
# Using a profile with fewer examples for development speed. CI can use a more thorough profile.
settings.register_profile(
    "subfuzz_dev",
    max_examples=30,  # Reduced for quicker local runs
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.filter_too_much,  # Common if rules have many 'assume'
        HealthCheck.data_too_large,
    ],
    deadline=None,  # Disable deadline for local debugging
)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "subfuzz_dev"))

# Make the state machine runnable as a PyTest test case
TestSubGraphFuzzing = SubGraphFuzzer.TestCase
