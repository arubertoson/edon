"""Tests for core EntityGraph logic, such as reachability and link validation."""

import pytest

from edon.graph import EntityGraph
from edon.types import EdgeKey, SocketAddress, SocketRole
from edon.errors import SocketLinkErrorReason

from tests.fixtures.nodes import IntegerNode, FloatNode, AddNode


@pytest.fixture
def graph() -> EntityGraph:
    """Provides a new EntityGraph instance for each test."""
    return EntityGraph()


class TestGraphIsReachable:
    """Tests for EntityGraph._is_reachable() method."""

    def test_direct_path(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        node_b = IntegerNode(name="B")
        graph.add_node(node_a)
        graph.add_node(node_b)
        edge = EdgeKey(
            SocketAddress(node_a.id, "src_int", SocketRole.SOURCE),
            SocketAddress(node_b.id, "trg_int", SocketRole.TARGET),
        )
        graph.link_sockets(edge)

        assert graph._is_reachable(node_a.id, node_b.id)

    def test_indirect_path(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        node_b = IntegerNode(name="B")
        node_c = IntegerNode(name="C")
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        edge1 = EdgeKey(
            SocketAddress(node_a.id, "src_int", SocketRole.SOURCE),
            SocketAddress(node_b.id, "trg_int", SocketRole.TARGET),
        )
        edge2 = EdgeKey(
            SocketAddress(node_b.id, "src_int", SocketRole.SOURCE),
            SocketAddress(node_c.id, "trg_int", SocketRole.TARGET),
        )
        graph.link_sockets(edge1)
        graph.link_sockets(edge2)
        assert graph._is_reachable(node_a.id, node_c.id)

    def test_no_path_disconnected(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        node_b = IntegerNode(name="B")
        graph.add_node(node_a)
        graph.add_node(node_b)
        assert not graph._is_reachable(node_a.id, node_b.id)

    def test_no_path_reverse_direction(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        node_b = IntegerNode(name="B")
        graph.add_node(node_a)
        graph.add_node(node_b)
        edge = EdgeKey(
            SocketAddress(node_a.id, "src_int", SocketRole.SOURCE),
            SocketAddress(node_b.id, "trg_int", SocketRole.TARGET),
        )
        graph.link_sockets(edge)
        assert not graph._is_reachable(node_b.id, node_a.id)

    def test_path_to_self(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        graph.add_node(node_a)
        assert graph._is_reachable(node_a.id, node_a.id)

    def test_cycle_present_path_exists(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        node_b = IntegerNode(name="B")
        node_c = IntegerNode(name="C")
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_c)
        graph.link_sockets(
            EdgeKey(
                SocketAddress(node_a.id, "src_int", SocketRole.SOURCE),
                SocketAddress(node_b.id, "trg_int", SocketRole.TARGET),
            )
        )
        graph.link_sockets(
            EdgeKey(
                SocketAddress(node_b.id, "src_int", SocketRole.SOURCE),
                SocketAddress(node_c.id, "trg_int", SocketRole.TARGET),
            )
        )
        # --- Test Setup: Manually create a cycle ---
        # To test `_is_reachable` in a graph that *already* contains a cycle,
        # we must bypass the `graph.link_sockets()` method for the edge that
        # forms the cycle. This is because `link_sockets()` itself calls
        # `_is_reachable` for cycle detection and would prevent the cycle's formation.
        # By directly adding the edge to `graph.edges`, we can construct the specific
        # graph state (with a cycle) that `_is_reachable` needs to be tested against.
        # This is a common technique for testing internal graph algorithms that operate
        # on states which the public API might otherwise restrict or validate against.
        cycle_forming_edge = EdgeKey(
            SocketAddress(node_c.id, "src_int", SocketRole.SOURCE),  # Edge from C
            SocketAddress(
                node_a.id, "trg_int", SocketRole.TARGET
            ),  # back to A, forming A->B->C->A
        )
        graph.edges.add(cycle_forming_edge)
        # --- End Test Setup ---

        assert graph._is_reachable(node_a.id, node_c.id)
        assert graph._is_reachable(node_a.id, node_a.id)

    def test_cycle_present_no_path_to_external_node(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        node_b = IntegerNode(name="B")
        node_d = IntegerNode(name="D")  # External node
        graph.add_node(node_a)
        graph.add_node(node_b)
        graph.add_node(node_d)
        graph.link_sockets(
            EdgeKey(
                SocketAddress(node_a.id, "src_int", SocketRole.SOURCE),
                SocketAddress(node_b.id, "trg_int", SocketRole.TARGET),
            )
        )
        # --- Test Setup: Manually create a cycle ---
        # As in `test_cycle_present_path_exists`, we manually add the cycle-forming edge
        # to `graph.edges`. This allows us to test `_is_reachable` on a graph
        # that already has a cycle (A -> B -> A), without `link_sockets()` preventing it.
        # We are interested in whether `_is_reachable` correctly determines that
        # an external node `D` is not reachable from `A`, even with the cycle present.
        cycle_forming_edge = EdgeKey(
            SocketAddress(node_b.id, "src_int", SocketRole.SOURCE),  # Edge from B
            SocketAddress(node_a.id, "trg_int", SocketRole.TARGET),  # back to A, forming A->B->A
        )
        graph.edges.add(cycle_forming_edge)
        # --- End Test Setup ---
        assert graph._is_reachable(node_a.id, node_d.id) is False

    def test_single_node_graph_is_reachable(self, graph: EntityGraph):
        node_a = IntegerNode(name="A")
        graph.add_node(node_a)
        assert graph._is_reachable(node_a.id, node_a.id) is True

    def test_is_reachable_nodes_not_in_graph(self, graph: EntityGraph):
        # _is_reachable expects nodes to be in the graph, get_node will raise KeyError
        with pytest.raises(KeyError):
            graph._is_reachable("non_existent_start", "non_existent_end")

        node_a = IntegerNode(name="A")
        graph.add_node(node_a)
        # If start_node exists but end_node does not, _is_reachable should return False
        # as the end_node will never be found. No KeyError is raised for end_node_id itself.
        assert graph._is_reachable(node_a.id, "non_existent_end") is False
        with pytest.raises(KeyError):
            graph._is_reachable("non_existent_start", node_a.id)


class TestGraphCanFormLink:
    """Tests for EntityGraph.can_form_link() method."""

    def test_can_form_link_valid(self, graph: EntityGraph):
        source_node = IntegerNode(name="SourceInt")
        target_node = AddNode(name="TargetAdd")
        graph.add_node(source_node)
        graph.add_node(target_node)

        source_addr = SocketAddress(source_node.id, "src_int", SocketRole.SOURCE)
        target_addr = SocketAddress(target_node.id, "a", SocketRole.TARGET)

        can_link, reason = graph.can_form_link(source_addr, target_addr)
        assert can_link is True
        assert reason is None

    def test_can_form_link_cycle_detected(self, graph: EntityGraph):
        # For this test, let's use IntegerNode which has 'src_int' and 'trg_int'
        n1 = IntegerNode(name="N1")
        n2 = IntegerNode(name="N2")
        graph.add_node(n1)
        graph.add_node(n2)

        # Path N2 -> N1
        graph.link_sockets(
            EdgeKey(
                SocketAddress(n2.id, "src_int", SocketRole.SOURCE),  # N2 output
                SocketAddress(n1.id, "trg_int", SocketRole.TARGET),  # N1 input
            )
        )

        # Attempt to link N1 -> N2 (would form N1 -> N2 -> N1 cycle)
        source_addr = SocketAddress(n1.id, "src_int", SocketRole.SOURCE)  # N1 output
        target_addr = SocketAddress(n2.id, "trg_int", SocketRole.TARGET)  # N2 input

        can_link, reason = graph.can_form_link(source_addr, target_addr)
        assert can_link is False
        assert reason == SocketLinkErrorReason.CYCLE_DETECTED

    def test_can_form_link_type_mismatch(self, graph: EntityGraph):
        source_node = IntegerNode(name="SourceInt")  # src_int is int
        target_node = FloatNode(name="TargetFloat")  # trg_float is float
        graph.add_node(source_node)
        graph.add_node(target_node)

        source_addr = SocketAddress(source_node.id, "src_int", SocketRole.SOURCE)
        # FloatNode's target socket is 'trg_float'
        target_addr = SocketAddress(target_node.id, "trg_float", SocketRole.TARGET)

        can_link, reason = graph.can_form_link(source_addr, target_addr)
        assert can_link is False
        assert reason == SocketLinkErrorReason.TYPE_MISMATCH

    def test_can_form_link_same_parent_node(self, graph: EntityGraph):
        node = AddNode(name="MyAddNode")
        graph.add_node(node)

        source_addr = SocketAddress(node.id, "result", SocketRole.SOURCE)
        target_addr = SocketAddress(node.id, "a", SocketRole.TARGET)

        can_link, reason = graph.can_form_link(source_addr, target_addr)
        assert can_link is False
        assert reason == SocketLinkErrorReason.SAME_PARENT_NODE

    def test_can_form_link_directions_not_opposite_source_to_source(self, graph: EntityGraph):
        node1 = IntegerNode(name="N1")
        node2 = IntegerNode(name="N2")  # Using IntegerNode for its src_int
        graph.add_node(node1)
        graph.add_node(node2)

        source_addr = SocketAddress(node1.id, "src_int", SocketRole.SOURCE)
        target_addr = SocketAddress(
            node2.id, "src_int", SocketRole.SOURCE
        )  # Linking source to source

        can_link, reason = graph.can_form_link(source_addr, target_addr)
        assert can_link is False
        assert reason == SocketLinkErrorReason.DIRECTIONS_NOT_OPPOSITE

    def test_can_form_link_directions_not_opposite_target_to_target(self, graph: EntityGraph):
        node1 = IntegerNode(name="N1")  # Using IntegerNode for its trg_int
        node2 = AddNode(name="N2")  # Using AddNode for its 'a' target socket
        graph.add_node(node1)
        graph.add_node(node2)

        source_addr = SocketAddress(node1.id, "trg_int", SocketRole.TARGET)  # This is a target
        target_addr = SocketAddress(node2.id, "a", SocketRole.TARGET)  # This is also a target

        can_link, reason = graph.can_form_link(source_addr, target_addr)
        assert can_link is False
        assert reason == SocketLinkErrorReason.DIRECTIONS_NOT_OPPOSITE

    def test_can_form_link_rejects_same_socket(self, graph: EntityGraph) -> None:
        node = AddNode(name="Add")
        graph.add_node(node)
        address = node.sockets["result"].address

        can_link, reason = graph.can_form_link(address, address)

        assert can_link is False
        assert reason == SocketLinkErrorReason.CANNOT_LINK_TO_SELF

    @pytest.mark.parametrize("socket_name", ["a", "result"])
    def test_can_form_link_rejects_matching_roles(
        self, graph: EntityGraph, socket_name: str
    ) -> None:
        first = AddNode(name="First")
        second = AddNode(name="Second")
        graph.add_node(first)
        graph.add_node(second)

        can_link, reason = graph.can_form_link(
            first.sockets[socket_name].address,
            second.sockets[socket_name].address,
        )

        assert can_link is False
        assert reason == SocketLinkErrorReason.DIRECTIONS_NOT_OPPOSITE

    def test_can_form_link_already_linked_via_internal_check(self, graph: EntityGraph):
        source_node = IntegerNode(name="SourceInt")
        target_node = AddNode(name="TargetAdd")
        graph.add_node(source_node)
        graph.add_node(target_node)

        source_addr = SocketAddress(source_node.id, "src_int", SocketRole.SOURCE)
        target_addr = SocketAddress(target_node.id, "a", SocketRole.TARGET)

        # First, successfully link them
        edge = EdgeKey(source_addr, target_addr)
        link_success, _ = graph.link_sockets(edge)
        assert link_success is True

        # Now, try to form the same link again
        can_link, reason = graph.can_form_link(source_addr, target_addr)
        assert can_link is False
        # This specific ALREADY_LINKED comes from can_link_sockets_internal
        assert reason == SocketLinkErrorReason.ALREADY_LINKED

    def test_can_form_link_rejects_second_source_for_target(self, graph: EntityGraph) -> None:
        first = IntegerNode(name="First")
        second = IntegerNode(name="Second")
        addition = AddNode(name="Addition")
        for node in (first, second, addition):
            graph.add_node(node)
        target = addition.sockets["a"].address
        existing_edge = EdgeKey(first.sockets["src_int"].address, target)
        assert graph.link_sockets(existing_edge) == (True, None)

        can_link, reason = graph.can_form_link(second.sockets["src_int"].address, target)

        assert can_link is False
        assert reason == SocketLinkErrorReason.INPUT_SOCKET_FULL
        second_edge = EdgeKey(second.sockets["src_int"].address, target)
        assert graph.link_sockets(second_edge) == (
            False,
            SocketLinkErrorReason.INPUT_SOCKET_FULL,
        )
        assert graph.edges == {existing_edge}


class TestGraphLinkSockets:
    """Tests for EntityGraph.link_sockets() method, focusing on high-level behaviors."""

    def test_link_sockets_cycle_rejected(self, graph: EntityGraph):
        """Tests that link_sockets correctly identifies and rejects a cycle."""
        n1 = IntegerNode(name="N1")
        n2 = IntegerNode(name="N2")
        graph.add_node(n1)
        graph.add_node(n2)

        # Link N1 -> N2
        edge1 = EdgeKey(
            SocketAddress(n1.id, "src_int", SocketRole.SOURCE),
            SocketAddress(n2.id, "trg_int", SocketRole.TARGET),
        )
        link_success1, reason1 = graph.link_sockets(edge1)
        assert link_success1 is True, f"Initial link failed: {reason1}"
        assert edge1 in graph.edges, "Initial edge not added to graph.edges"

        # Attempt to link N2 -> N1 (which would form a cycle N1 -> N2 -> N1)
        edge2_cycle = EdgeKey(
            SocketAddress(n2.id, "src_int", SocketRole.SOURCE),
            SocketAddress(n1.id, "trg_int", SocketRole.TARGET),
        )
        link_success2, reason2 = graph.link_sockets(edge2_cycle)

        assert link_success2 is False, "Cycle-forming link was not rejected."
        assert reason2 == SocketLinkErrorReason.CYCLE_DETECTED, (
            f"Incorrect reason for cycle rejection: expected CYCLE_DETECTED, got {reason2}"
        )
        assert edge2_cycle not in graph.edges, (
            "Cycle-forming edge was added to graph.edges despite rejection."
        )

    def test_remove_node_removes_only_its_edges(self, graph: EntityGraph) -> None:
        first = IntegerNode(name="First")
        second = IntegerNode(name="Second")
        addition = AddNode(name="Addition")
        for node in (first, second, addition):
            graph.add_node(node)
        first_edge = EdgeKey(first.sockets["src_int"].address, addition.sockets["a"].address)
        second_edge = EdgeKey(second.sockets["src_int"].address, addition.sockets["b"].address)
        assert graph.link_sockets(first_edge) == (True, None)
        assert graph.link_sockets(second_edge) == (True, None)

        graph.remove_node(first.id)

        assert first.id not in graph.nodes
        assert graph.edges == {second_edge}
        assert graph.get_socket_links(addition.sockets["a"].address) == []
        assert graph.get_socket_links(addition.sockets["b"].address) == [
            second.sockets["src_int"].address
        ]
