from typing import Any
from unittest.mock import Mock

import pytest

from edon.socket import EntitySocket, SocketLinkErrorReason, SocketRole

# Assuming EntityNode is simple enough or we use a mock
# For testing purposes, a minimal class is sufficient if EntitySocket only accesses node.id and node.name
from edon.types import SocketAddress, SocketType


# Minimal test node class
class MockNode:
    def __init__(self, node_id: str):
        self.id = node_id
        self.name = f"Node {node_id}"  # Add name for repr


# Helper to create sockets easily
def create_socket(
    node_id: str, name: str, role: SocketRole, socket_type_member: SocketType
) -> EntitySocket:
    node = MockNode(node_id)
    # Directly use the passed-in enum member for type_info
    return EntitySocket(name=name, role=role, node=node, type_info=socket_type_member)


# --- Tests for can_link_to ---


def test_can_link_to_self_fails():
    sock = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    can_link, reason = sock.can_link_to(sock)
    assert can_link is False
    assert reason == SocketLinkErrorReason.CANNOT_LINK_TO_SELF


def test_can_link_to_same_role_fails():
    sock1 = create_socket("n1", "out1", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "out2", SocketRole.SOURCE, SocketType.INTEGER)
    can_link, reason = sock1.can_link_to(sock2)
    assert can_link is False
    assert reason == SocketLinkErrorReason.DIRECTIONS_NOT_OPPOSITE


def test_can_link_to_same_parent_node_fails():
    node = MockNode("n1")
    sock1 = EntitySocket(
        name="out", role=SocketRole.SOURCE, node=node, type_info=SocketType.INTEGER
    )
    sock2 = EntitySocket(
        name="in", role=SocketRole.TARGET, node=node, type_info=SocketType.INTEGER
    )
    can_link, reason = sock1.can_link_to(sock2)
    assert can_link is False
    assert reason == SocketLinkErrorReason.SAME_PARENT_NODE


def test_can_link_to_already_linked_returns_true_with_reason():
    sock1 = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.INTEGER)
    # Manually create the link state for this test
    sock1.links.append(sock2)
    sock2.links.append(sock1)

    can_link, reason = sock1.can_link_to(sock2)
    assert can_link is True
    assert reason == SocketLinkErrorReason.ALREADY_LINKED


def test_can_link_to_type_mismatch_fails():
    sock1 = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.STRING)
    can_link, reason = sock1.can_link_to(sock2)
    assert can_link is False
    assert reason == SocketLinkErrorReason.TYPE_MISMATCH


def test_can_link_to_type_compatible_success():
    sock1 = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.INTEGER)
    can_link, reason = sock1.can_link_to(sock2)
    assert can_link is True
    assert reason is None


def test_can_link_to_any_type_compatible_success():
    mock_socket_type_any = Mock(spec=SocketType)
    mock_socket_type_any.python_type = Any
    mock_socket_type_any.name = "ANY"  # For repr

    sock1 = create_socket("n1", "out", SocketRole.SOURCE, mock_socket_type_any)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.STRING)
    can_link, reason = sock1.can_link_to(sock2)
    assert can_link is True
    assert reason is None

    sock3 = create_socket("n3", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock4 = create_socket("n4", "in", SocketRole.TARGET, mock_socket_type_any)
    can_link, reason = sock3.can_link_to(sock4)
    assert can_link is True
    assert reason is None


def test_can_link_to_subclass_compatible_success():
    """
    Tests type compatibility where one type is a subclass of another.
    The can_link_to method's type check is:
    issubclass(actual_target_socket.data_type, actual_source_socket.data_type)
    """

    class Base:
        pass

    class Derived(Base):
        pass

    mock_socket_type_base = Mock(spec=SocketType)
    mock_socket_type_base.python_type = Base
    mock_socket_type_base.name = "BASE"  # For repr, if needed

    mock_socket_type_derived = Mock(spec=SocketType)
    mock_socket_type_derived.python_type = Derived
    mock_socket_type_derived.name = "DERIVED"  # For repr, if needed

    # Scenario 1: Source(Base) -> Target(Derived)
    # Check: issubclass(Derived, Base) which is True. Link should be allowed.
    sock_source_base = create_socket("n1", "out_base", SocketRole.SOURCE, mock_socket_type_base)
    sock_target_derived = create_socket(
        "n2", "in_derived", SocketRole.TARGET, mock_socket_type_derived
    )
    can_link, reason = sock_source_base.can_link_to(sock_target_derived)
    assert can_link is True, (
        f"Should allow link from Base to Derived. Reason: {reason}. "
        f"Source type: {sock_source_base.data_type}, Target type: {sock_target_derived.data_type}"
    )
    assert reason is None

    # Scenario 2: Source(Derived) -> Target(Base)
    # Check: issubclass(Base, Derived) which is False. Link should be disallowed.
    sock_source_derived = create_socket(
        "n3", "out_derived", SocketRole.SOURCE, mock_socket_type_derived
    )
    sock_target_base = create_socket("n4", "in_base", SocketRole.TARGET, mock_socket_type_base)
    can_link, reason = sock_source_derived.can_link_to(sock_target_base)
    assert can_link is False, (
        "Should not allow link from Derived to Base. "
        f"Source type: {sock_source_derived.data_type}, Target type: {sock_target_base.data_type}"
    )
    assert reason == SocketLinkErrorReason.TYPE_MISMATCH


# --- Tests for link_to ---


def test_link_to_success_and_is_linked_state():
    sock1 = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.INTEGER)
    assert sock1.is_linked() is False  # Check initial state
    assert sock2.is_linked() is False

    success, reason = sock1.link_to(sock2)
    assert success is True
    assert reason is None
    assert sock2 in sock1.links
    assert sock1 in sock2.links
    assert sock1.is_linked() is True
    assert sock2.is_linked() is True


def test_link_to_fails_if_can_link_to_fails():
    node = MockNode("n1")
    sock1 = EntitySocket(
        name="out", role=SocketRole.SOURCE, node=node, type_info=SocketType.INTEGER
    )
    sock2 = EntitySocket(
        name="in", role=SocketRole.TARGET, node=node, type_info=SocketType.INTEGER
    )  # Same node
    success, reason = sock1.link_to(sock2)
    assert success is False
    assert reason == SocketLinkErrorReason.SAME_PARENT_NODE
    assert not sock1.links
    assert not sock2.links
    assert sock1.is_linked() is False
    assert sock2.is_linked() is False


def test_link_to_already_linked_returns_false_with_reason():
    sock1 = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.INTEGER)
    sock1.link_to(sock2)  # Establish link first

    success, reason = sock1.link_to(sock2)
    assert success is False
    assert reason == SocketLinkErrorReason.ALREADY_LINKED
    assert len(sock1.links) == 1  # Links should not have duplicated
    assert len(sock2.links) == 1


# --- Tests for unlink_from ---


def test_unlink_from_success_and_is_linked_state():
    sock1 = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.INTEGER)
    sock1.link_to(sock2)
    assert sock1.is_linked() is True
    assert sock2.is_linked() is True

    sock1.unlink_from(sock2)
    assert not sock1.links
    assert not sock2.links
    assert sock1.is_linked() is False
    assert sock2.is_linked() is False

    # Test unlinking from the other side
    sock1.link_to(sock2)
    sock2.unlink_from(sock1)
    assert not sock1.links
    assert not sock2.links
    assert sock1.is_linked() is False
    assert sock2.is_linked() is False


def test_unlink_from_asserts_if_not_mutually_linked():
    sock1 = create_socket("n1", "out", SocketRole.SOURCE, SocketType.INTEGER)
    sock2 = create_socket("n2", "in", SocketRole.TARGET, SocketType.INTEGER)

    with pytest.raises(
        AssertionError, match="CORRUPTION: Trying to unlink sockets that doesn't have a link"
    ):
        sock1.unlink_from(sock2)

    # Simulate one-way link (corruption)
    sock1.links.append(sock2)
    with pytest.raises(
        AssertionError, match="CORRUPTION: Trying to unlink sockets that doesn't have a link"
    ):
        sock1.unlink_from(sock2)
    sock1.links.clear()


# --- Tests for State/Properties ---


def test_socket_address_property():
    sock = create_socket("node_abc", "my_socket", SocketRole.SOURCE, SocketType.FLOAT)
    addr = sock.address
    assert isinstance(addr, SocketAddress)
    assert addr.node_id == "node_abc"
    assert addr.name == "my_socket"
    assert addr.role == SocketRole.SOURCE


def test_socket_data_type_property():
    sock_int = create_socket("n1", "s1", SocketRole.SOURCE, SocketType.INTEGER)
    assert sock_int.data_type == int

    sock_str = create_socket("n2", "s2", SocketRole.TARGET, SocketType.STRING)
    assert sock_str.data_type == str

    mock_socket_type_any = Mock(spec=SocketType)
    mock_socket_type_any.python_type = Any
    mock_socket_type_any.name = "ANY"  # For repr
    sock_any = create_socket("n3", "s3", SocketRole.SOURCE, mock_socket_type_any)
    assert sock_any.data_type == Any


def test_is_linked_initial_state():
    sock = create_socket("n1", "s1", SocketRole.SOURCE, SocketType.INTEGER)
    assert sock.is_linked() is False
