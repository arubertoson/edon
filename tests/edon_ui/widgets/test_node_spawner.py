import pytest
from PySide6.QtCore import QPointF

from src.edon.node import EntityNode
from src.edon_ui.graph.controller import WorkspaceController
from src.edon_ui.widgets.node_spawner import NodeSpawningPanel


# Minimal mock node classes for testing the spawner's listing and filtering.
# Aligned with src.edon.node.EntityNode structure.
class SpawnerTestIntNode(EntityNode):
    node_type = "TestInt"
    source_socket_definitions = []
    target_socket_definitions = []

    def process(self) -> None:
        pass


class SpawnerTestStrNode(EntityNode):
    node_type = "TestStr"
    source_socket_definitions = []
    target_socket_definitions = []

    def process(self) -> None:
        pass


class SpawnerTestAnotherNode(EntityNode):
    node_type = "TestAnother"
    source_socket_definitions = []
    target_socket_definitions = []

    def process(self) -> None:
        pass


@pytest.fixture
def spawner_graph_controller(qtbot):
    """
    Provides a GraphController fixture with a predefined node_registry
    for testing the NodeSpawningPanel.
    """
    # GraphController might take graph in constructor or have a setter
    # Assuming constructor for now, or that it can be set.
    # If GraphController is a QObject and has signals/slots relevant here,
    # it might need to be managed by qtbot too.
    controller = WorkspaceController(
        {
            SpawnerTestIntNode.__name__: SpawnerTestIntNode,
            SpawnerTestStrNode.__name__: SpawnerTestStrNode,
            SpawnerTestAnotherNode.__name__: SpawnerTestAnotherNode,
        }
    )
    # Populate the node registry. The keys are what the spawner lists.
    return controller


def test_node_spawner_filtering_and_selection(qtbot, spawner_graph_controller):
    """
    Tests the NodeSpawningPanel's filtering logic, list population,
    and default item selection.
    """
    panel = NodeSpawningPanel(
        controller=spawner_graph_controller,
        spawn_position=QPointF(0, 0),  # Position not critical for this test
    )
    qtbot.addWidget(panel)
    panel.show()  # Panel must be shown for interactions and visibility

    # Initial state: All registered node types, sorted alphabetically by key.
    # Expected order of keys: "TestAnother", "TestInt", "TestStr"
    list_widget = panel.node_list_widget
    assert list_widget.count() == 3
    assert list_widget.item(0).text() == SpawnerTestAnotherNode.__name__
    assert list_widget.item(1).text() == SpawnerTestIntNode.__name__
    assert list_widget.item(2).text() == SpawnerTestStrNode.__name__
    assert list_widget.currentItem().text() == SpawnerTestAnotherNode.__name__

    # Test filtering for "Int" - exact part of "TestInt"
    panel.search_bar.setText("Int")
    assert list_widget.item(0).text() == SpawnerTestIntNode.__name__
    assert list_widget.currentItem().text() == SpawnerTestIntNode.__name__

    # Test filtering for "Test" - common prefix, fuzzy match
    # All three nodes have "Test" in their node_type.
    # Fuzzy matching should find all. Order should be stable (initial alphabetical).
    panel.search_bar.setText("Test")
    qtbot.waitUntil(lambda: list_widget.count() == 3)

    assert list_widget.count() == 3
    assert list_widget.item(0).text() == SpawnerTestAnotherNode.__name__
    assert list_widget.item(1).text() == SpawnerTestIntNode.__name__
    assert list_widget.item(2).text() == SpawnerTestStrNode.__name__
    assert list_widget.currentItem().text() == SpawnerTestAnotherNode.__name__

    # Test filtering for "Str"
    panel.search_bar.setText("Str")
    assert list_widget.item(0).text() == SpawnerTestStrNode.__name__
    assert list_widget.currentItem().text() == SpawnerTestStrNode.__name__

    # Test clearing the search bar
    panel.search_bar.setText("")
    qtbot.waitUntil(lambda: list_widget.count() == 3)

    assert list_widget.count() == 3
    assert list_widget.item(0).text() == SpawnerTestAnotherNode.__name__
    assert list_widget.currentItem().text() == SpawnerTestAnotherNode.__name__

    # Test filtering with no results
    panel.search_bar.setText("#")
    qtbot.waitUntil(lambda: list_widget.count() == 0)

    assert list_widget.count() == 0
    assert list_widget.currentItem() is None

    panel.close()
