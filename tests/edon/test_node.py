import uuid
import pytest
from typing import Any

from edon.node import EntityNode
from edon.socket import EntitySocket, SocketRole
from edon.types import SocketDef, SocketType


# --- Test Fixtures and Helper Classes ---


@pytest.fixture
def basic_socket_def_output() -> SocketDef:
    """Provides a basic SocketDef for an output socket."""
    return SocketDef(name="output1", socket_type=SocketType.STRING, default="hello")


@pytest.fixture
def basic_socket_def_input() -> SocketDef:
    """Provides a basic SocketDef for an input socket."""
    return SocketDef(name="input1", socket_type=SocketType.INTEGER, default=0)


class DeclarativeNode(EntityNode):
    """A subclass of EntityNode for testing declarative features."""

    name: str | None = "DeclarativeTestNode"
    node_type: str | None = "test.declarative"
    source_socket_definitions = [
        SocketDef(name="class_in", socket_type=SocketType.FLOAT, default=1.0)
    ]
    target_socket_definitions = [
        SocketDef(name="class_out", socket_type=SocketType.INTEGER, default=100)
    ]

    def process(self) -> None:
        # A concrete implementation for testing purposes if needed,
        # though base class tests focus on NotImplementedError.
        pass


class MinimalNode(EntityNode):
    """A node with no class-level definitions to test defaults."""

    def process(self) -> None:
        pass


# --- Test Cases ---


def test_entity_node_default_initialization():
    node = EntityNode()
    assert (
        node.name is None
    )
    assert node.node_type is None
    assert isinstance(node.id, str)
    assert len(node.id) == 36  # Standard UUID4 length
    assert node.sockets == {}
    assert node.source_sockets == []
    assert node.target_sockets == []


def test_entity_node_minimal_subclass_initialization():
    node = MinimalNode()
    assert node.name == "Minimal"
    assert node.node_type == "minimal"
    assert isinstance(node.id, str)
    assert node.sockets == {}
    assert node.source_sockets == []
    assert node.target_sockets == []


def test_entity_node_initialization_with_instance_params(
    basic_socket_def_input: SocketDef, basic_socket_def_output: SocketDef
):
    node_name = "MyInstanceNode"
    node_type_str = "custom.instance.node"
    source_defs = [basic_socket_def_input]
    target_defs = [basic_socket_def_output]

    node = EntityNode(
        name=node_name,
        node_type=node_type_str,
        source_socket_definitions=source_defs,
        target_socket_definitions=target_defs,
    )

    assert node.name == node_name
    assert node.node_type == node_type_str
    assert isinstance(node.id, str)

    assert len(node.sockets) == 2
    assert "input1" in node.sockets
    assert "output1" in node.sockets

    input_socket = node.sockets["input1"]
    assert isinstance(input_socket, EntitySocket)
    assert input_socket.name == "input1"
    assert input_socket.role == SocketRole.SOURCE
    assert input_socket.node == node
    assert input_socket.type_info == SocketType.INTEGER
    assert input_socket.value == 0

    output_socket = node.sockets["output1"]
    assert isinstance(output_socket, EntitySocket)
    assert output_socket.name == "output1"
    assert output_socket.role == SocketRole.TARGET
    assert output_socket.type_info == SocketType.STRING
    assert output_socket.value == "hello"

    assert len(node.source_sockets) == 1
    assert node.source_sockets[0] == input_socket
    assert len(node.target_sockets) == 1
    assert node.target_sockets[0] == output_socket


def test_entity_node_declarative_subclass_initialization():
    """Test EntityNode initialization using a declarative subclass."""
    node = DeclarativeNode()

    assert node.name == "DeclarativeTestNode"
    assert node.node_type == "test.declarative"
    assert isinstance(node.id, str)

    assert len(node.sockets) == 2
    assert "class_in" in node.sockets
    assert "class_out" in node.sockets

    class_in_socket = node.sockets["class_in"]
    assert class_in_socket.role == SocketRole.SOURCE
    assert class_in_socket.type_info == SocketType.FLOAT
    assert class_in_socket.value == 1.0

    class_out_socket = node.sockets["class_out"]
    assert class_out_socket.role == SocketRole.TARGET
    assert class_out_socket.type_info == SocketType.INTEGER
    assert class_out_socket.value == 100

    assert len(node.source_sockets) == 1
    assert node.source_sockets[0] == class_in_socket
    assert len(node.target_sockets) == 1
    assert node.target_sockets[0] == class_out_socket


def test_entity_node_instance_overrides_declarative_subclass(
    basic_socket_def_input: SocketDef,
):
    """Test instance parameters override declarative class attributes."""
    instance_name = "OverriddenNode"
    instance_type = "override.type"
    instance_source_defs = [basic_socket_def_input]  # input1, INTEGER
    # target_socket_definitions will use class attribute (class_out, INTEGER)

    node = DeclarativeNode(
        name=instance_name,
        node_type=instance_type,
        source_socket_definitions=instance_source_defs,
        # target_socket_definitions not provided, should use class's
    )

    assert node.name == instance_name
    assert node.node_type == instance_type

    assert len(node.sockets) == 2  # input1 (instance) + class_out (class)
    assert "input1" in node.sockets
    assert "class_out" in node.sockets
    assert "class_in" not in node.sockets  # class_in should be overridden

    instance_input_socket = node.sockets["input1"]
    assert instance_input_socket.role == SocketRole.SOURCE
    assert instance_input_socket.type_info == SocketType.INTEGER

    class_output_socket = node.sockets["class_out"]
    assert class_output_socket.role == SocketRole.TARGET
    assert class_output_socket.type_info == SocketType.INTEGER


def test_entity_node_empty_list_overrides_class_sockets():
    """Test providing an empty list for socket definitions overrides class definitions."""
    node = DeclarativeNode(source_socket_definitions=[], target_socket_definitions=[])
    assert node.name == "DeclarativeTestNode"  # From class
    assert node.sockets == {}
    assert node.source_sockets == []
    assert node.target_sockets == []


def test_entity_node_add_duplicate_socket_name_raises_value_error(
    basic_socket_def_input: SocketDef,
):
    """Test that adding a socket with a duplicate name raises ValueError."""
    duplicate_name_def = SocketDef(name="input1", socket_type=SocketType.FLOAT)
    with pytest.raises(ValueError) as excinfo:
        EntityNode(source_socket_definitions=[basic_socket_def_input, duplicate_name_def])
    assert "Socket with name 'input1' already exists" in str(excinfo.value)

    with pytest.raises(ValueError) as excinfo:
        EntityNode(
            source_socket_definitions=[basic_socket_def_input],
            target_socket_definitions=[duplicate_name_def],  # Name clash with source
        )
    assert "Socket with name 'input1' already exists" in str(excinfo.value)


def test_entity_node_socket_properties_caching(basic_socket_def_input: SocketDef):
    """Test that source_sockets and target_sockets properties cache their results."""
    node = EntityNode(source_socket_definitions=[basic_socket_def_input])

    # Initial access
    source_sockets_list1 = node.source_sockets
    target_sockets_list1 = node.target_sockets

    assert node._source_sockets is not None  # Internal cache should be populated
    assert node._target_sockets is not None

    # Second access
    source_sockets_list2 = node.source_sockets
    target_sockets_list2 = node.target_sockets

    assert source_sockets_list1 is source_sockets_list2  # Should be the same list object
    assert target_sockets_list1 is target_sockets_list2

    # Verify content just in case
    assert len(source_sockets_list1) == 1
    assert source_sockets_list1[0].name == "input1"
    assert len(target_sockets_list1) == 0


def test_entity_node_process_method_raises_not_implemented_error():
    """Test that the base EntityNode.process() method raises NotImplementedError."""
    node = EntityNode()
    with pytest.raises(NotImplementedError) as excinfo:
        node.process()
    assert "must implement the process() method" in str(excinfo.value)


def test_entity_node_repr_method(
    basic_socket_def_input: SocketDef, basic_socket_def_output: SocketDef
):
    """Test the __repr__ method of EntityNode."""
    node = EntityNode(
        name="ReprNode",
        node_type="test.repr",
        source_socket_definitions=[basic_socket_def_input],
        target_socket_definitions=[basic_socket_def_output],
    )
    node_id = node.id  # Get the generated ID for comparison

    expected_repr = (
        f"Node(name='ReprNode', type='test.repr', id='{node_id}', "
        f"sources=['input1'], targets=['output1'])"
    )
    assert repr(node) == expected_repr

    # Test with no sockets
    minimal_node = MinimalNode(name="MinimalRepr", node_type="test.minirepr")
    minimal_node_id = minimal_node.id
    expected_minimal_repr = (
        f"Node(name='MinimalRepr', type='test.minirepr', id='{minimal_node_id}', "
        f"sources=[], targets=[])"
    )
    assert repr(minimal_node) == expected_minimal_repr


def test_entity_node_id_is_unique():
    """Test that IDs generated for different nodes are unique."""
    node1 = EntityNode()
    node2 = EntityNode()
    assert node1.id != node2.id
    # Check if it looks like a UUID
    try:
        uuid.UUID(node1.id, version=4)
        uuid.UUID(node2.id, version=4)
    except ValueError:
        pytest.fail("Node ID is not a valid UUID v4 string")
