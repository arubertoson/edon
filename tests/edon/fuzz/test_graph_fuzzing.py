from __future__ import annotations

import os
from collections.abc import Callable
from typing import TYPE_CHECKING

import hypothesis.strategies as st
from hypothesis import HealthCheck, Phase, assume, settings
from hypothesis.stateful import Bundle, RuleBasedStateMachine, consumes, invariant, rule

from edon.graph import EntityGraph
from edon.types import EdgeKey, SocketRole
from tests.fixtures.nodes import (
    AddNode,
    ConcatNode,
    FloatNode,
    IntegerNode,
    MultiplyNode,
    StringNode,
)

if TYPE_CHECKING:
    from edon.node import EntityNode

# XXX: Available node types for the fuzzer to pick from, this should come from our
# builtin node registry later.
NODE_TYPES = [IntegerNode, AddNode, FloatNode, MultiplyNode, StringNode, ConcatNode]


class GraphFuzzer(RuleBasedStateMachine):
    # A bundle tracks the node ids currently in the graph, when we add
    # nodes the id should be added, when we remove the id should be removed.
    active_nodes = Bundle("nodes")
    active_edges = Bundle("edges")

    def __init__(self) -> None:
        super().__init__()
        # The system under test is the EntityGraph, each test will operate on this graph
        self.graph = EntityGraph()

    @rule(target=active_nodes, node_type_strategy=st.sampled_from(NODE_TYPES))
    def add_node(self, node_type_strategy: Callable[[], EntityNode]) -> str:
        # The node_type strategy is a callable that returns a node from our NODE_TYPES,
        node_instance = node_type_strategy()

        # we should have a node class now, which we want to add to the graph.
        self.graph.add_node(node_instance)
        # We then return the node_id which will be added to the `active_node_ids` bundle, which
        # other rules can draw from.
        return node_instance.id

    @rule(node_id_to_remove=consumes(active_nodes))
    def remove_node(self, node_id_to_remove: str) -> None:
        assert node_id_to_remove in self.graph.nodes, (
            f"Fuzzer model/graph inconsistency: Node ID '{node_id_to_remove}' from bundle not in self.graph.nodes."
        )

        self.graph.remove_node(node_id_to_remove)

    @rule(
        target=active_edges,
        source_node_id=active_nodes,
        target_node_id=active_nodes,
        data=st.data(),
    )
    def link_sockets(
        self, source_node_id: str, target_node_id: str, data: st.DataObject
    ) -> EdgeKey:
        # To run this rule we need a precondition, without any nodes there are not sockets that can
        # be linked, meaning it would be a useless operation to run.
        # XXX: We should not do prefiltering here imo, as there is a good case for just keeping
        # everything intact. We will have sockets that are "unlinkable", but this business logic
        # should be handled by the graph.

        src_node = self.graph.get_node(source_node_id)
        trg_node = self.graph.get_node(target_node_id)

        # Ensure nodes have connectable sockets before proceeding
        assume(len(src_node.source_sockets) > 0)
        assume(len(trg_node.target_sockets) > 0)

        # choose sockets
        src_socket_addr = data.draw(st.sampled_from([s.address for s in src_node.source_sockets]))
        trg_socket_addr = data.draw(st.sampled_from([s.address for s in trg_node.target_sockets]))

        edge_key = EdgeKey(source=src_socket_addr, target=trg_socket_addr)

        # Attempt to link the sockets. We don't need to check the result here,
        # as invariants will verify the graph's state.
        success, _ = self.graph.link_sockets(edge_key)

        assume(success)
        return edge_key

    @rule(edge=consumes(active_edges))
    def unlink_sockets(self, edge: EdgeKey) -> None:
        # When we remove a node, all edges related to that node goes with it. We simply
        # put up this guard to filter the already deleted edges, proper asserting
        # is happening in graph.remove_node.
        assume(edge in self.graph.edges)

        self.graph.unlink_sockets(edge)

    @invariant()
    def check_edge_consistency(self) -> None:
        """
        Check that all edges in the graph are valid:
        - They link existing nodes.
        - They link existing sockets on those nodes.
        - Source sockets have the SOURCE role, and target sockets have the TARGET role.
        """

        for edge in self.graph.edges:
            src = edge.source
            assert src.node_id in self.graph.nodes, (
                f"INVARIANT FAILED: Source node ID '{src.node_id} for edge {edge} not in graph.nodes.'"
            )
            src_node = self.graph.get_node(src.node_id)
            assert src.name in src_node.sockets, (
                f"INVARIANT FAILED: Source socket '{src.name}' for edge {edge} not in sockets of node '{src_node.id}'"
            )
            src_socket = src_node.sockets[src.name]
            assert src_socket.address.role == SocketRole.SOURCE, (
                f"INVARIANT FAILED: Source socket '{src_socket.address}' does not have SocketRole.SOURCE."
            )

            trg = edge.target
            assert trg.node_id in self.graph.nodes, (
                f"INVARIANT FAILED: Target node ID '{trg.node_id} for edge {edge} not in graph.nodes.'"
            )
            trg_node = self.graph.get_node(trg.node_id)
            assert trg.name in trg_node.sockets, (
                f"INVARIANT FAILED: Target socket '{trg.name}' for edge {edge} not in sockets of node '{trg_node.id}'"
            )
            trg_socket = trg_node.sockets[trg.name]
            assert trg_socket.address.role == SocketRole.TARGET, (
                f"INVARIANT FAILED: Target socket '{trg_socket.address}' does not have SocketRole.target."
            )

    @invariant()
    def check_get_socket_links_consistency(self) -> None:
        """
        Ensures that get_socket_links() is consistent with self.graph.edges.
        """
        # Part 1: Check that all links reported by get_socket_links correspond to actual edges.
        for node_id, node in self.graph.nodes.items():
            for socket_name, socket in node.sockets.items():
                socket_addr = socket.address
                reported_links = self.graph.get_socket_links(socket_addr)
                for linked_addr in reported_links:
                    # Determine the expected edge based on roles
                    if socket_addr.role == SocketRole.SOURCE:
                        expected_edge = EdgeKey(source=socket_addr, target=linked_addr)
                        assert linked_addr.role == SocketRole.TARGET, (
                            f"INVARIANT FAILED: Source socket {socket_addr} linked by get_socket_links "
                            f"to non-target socket {linked_addr}."
                        )
                    else:  # socket_addr.role == SocketRole.TARGET
                        expected_edge = EdgeKey(source=linked_addr, target=socket_addr)
                        assert linked_addr.role == SocketRole.SOURCE, (
                            f"INVARIANT FAILED: Target socket {socket_addr} linked by get_socket_links "
                            f"to non-source socket {linked_addr}."
                        )

                    assert expected_edge in self.graph.edges, (
                        f"INVARIANT FAILED: get_socket_links for {socket_addr} reported link to {linked_addr}, "
                        f"but edge {expected_edge} not in self.graph.edges."
                    )

        # Part 2: Check that all actual edges are reported by get_socket_links.
        for edge in self.graph.edges:
            source_addr = edge.source
            target_addr = edge.target

            source_links = self.graph.get_socket_links(source_addr)
            assert target_addr in source_links, (
                f"INVARIANT FAILED: Edge {edge} exists, but target {target_addr} "
                f"not in get_socket_links for source {source_addr}."
            )

            target_links = self.graph.get_socket_links(target_addr)
            assert source_addr in target_links, (
                f"INVARIANT FAILED: Edge {edge} exists, but source {source_addr} "
                f"not in get_socket_links for target {target_addr}."
            )


settings.register_profile(
    "fuzzing_dev",
    max_examples=200,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.filter_too_much,
        HealthCheck.data_too_large,
    ],
    deadline=None,
)

settings.register_profile(
    "fuzzing_ci",
    max_examples=1000,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.filter_too_much,
        HealthCheck.data_too_large,
    ],
    phases=[Phase.explicit, Phase.reuse, Phase.generate, Phase.target],
    deadline=2000,
)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "fuzzing_dev"))

# Make state machine runnable as a test through PyTest
TestGraphFuzzing = GraphFuzzer.TestCase
