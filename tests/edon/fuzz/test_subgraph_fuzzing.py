"""Stateful graph edits and dynamic subgraph interfaces with an independent model."""

import hypothesis.strategies as st
from hypothesis.stateful import invariant, precondition, rule

from edon.graph import EntitySubGraphNode
from edon.socket import EntitySocket
from edon.types import SocketAddress
from tests.edon.fuzz.test_graph_fuzzing import GraphFuzzer
from tests.fixtures.nodes import IntegerNode


class SubGraphFuzzer(GraphFuzzer):
    def __init__(self) -> None:
        super().__init__()
        self.proxy_model: dict[str, dict[str, SocketAddress]] = {}
        self.proxy_sequence: int = 0

    def subgraphs(self) -> list[EntitySubGraphNode]:
        return [node for node in self.graph.nodes.values() if isinstance(node, EntitySubGraphNode)]

    @rule(
        target=GraphFuzzer.active_nodes, internal_node_count=st.integers(min_value=1, max_value=2)
    )
    def add_subgraph_node(self, internal_node_count: int) -> str:
        subgraph: EntitySubGraphNode = EntitySubGraphNode()
        first: IntegerNode = IntegerNode(name="Internal_0")
        subgraph.internal_graph.add_node(first)
        for index in range(1, internal_node_count):
            internal: IntegerNode = IntegerNode(name=f"Internal_{index}")
            subgraph.internal_graph.add_node(internal)
        mappings: dict[str, SocketAddress] = {
            "input": first.sockets["trg_int"].address,
            "output": first.sockets["src_int"].address,
        }
        for name, address in mappings.items():
            subgraph.add_proxy_socket(name, address)
        self.graph.add_node(subgraph)
        self.proxy_model[subgraph.id] = mappings
        return subgraph.id

    @precondition(lambda self: bool(self.subgraphs()))
    @rule(data=st.data())
    def add_proxy_socket_to_subgraph(self, data: st.DataObject) -> None:
        subgraph: EntitySubGraphNode = data.draw(st.sampled_from(self.subgraphs()))
        sockets: list[EntitySocket] = [
            socket
            for node in subgraph.internal_graph.nodes.values()
            for socket in node.sockets.values()
        ]
        internal: EntitySocket = data.draw(st.sampled_from(sockets))
        name: str = f"dynamic_{self.proxy_sequence}"
        self.proxy_sequence += 1
        subgraph.add_proxy_socket(name, internal.address)
        self.proxy_model[subgraph.id][name] = internal.address

    @precondition(lambda self: any(node.sockets for node in self.subgraphs()))
    @rule(data=st.data())
    def remove_proxy_socket_from_subgraph(self, data: st.DataObject) -> None:
        candidates: list[EntitySubGraphNode] = [node for node in self.subgraphs() if node.sockets]
        subgraph: EntitySubGraphNode = data.draw(st.sampled_from(candidates))
        name: str = data.draw(st.sampled_from(sorted(subgraph.sockets)))
        address: SocketAddress = subgraph.sockets[name].address
        # EntitySubGraphNode does not own its parent graph. Unlink there before
        # removing the interface socket, as required to preserve graph validity.
        for edge in list(self.graph.edges):
            if address in (edge.source, edge.target):
                self.graph.unlink_sockets(edge)
        subgraph.remove_proxy_socket(name)
        del self.proxy_model[subgraph.id][name]

    @invariant()
    def check_subgraph_proxy_sockets_valid(self) -> None:
        for subgraph in self.subgraphs():
            mappings: dict[str, SocketAddress] = self.proxy_model[subgraph.id]
            assert set(subgraph.sockets) == set(mappings)
            for name, address in mappings.items():
                internal: EntitySocket = subgraph.internal_graph.get_node(address.node_id).sockets[
                    address.name
                ]
                external: EntitySocket = subgraph.sockets[name]
                assert external.role == internal.role == address.role
                assert external.type_info == internal.type_info
                assert internal.exposed


TestSubGraphFuzzing = SubGraphFuzzer.TestCase
