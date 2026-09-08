import pytest
from PySide6.QtCore import QPointF, Qt
from pytestqt.qtbot import QtBot

from edon.node import EntityNode
from edon_ui.graph.controller import WorkspaceController
from edon_ui.widgets.node_spawner import NodeSpawningPanel


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
def spawner_graph_controller(qtbot: QtBot) -> WorkspaceController:
    """Provide a controller with a small node registry."""
    controller = WorkspaceController(
        {
            SpawnerTestIntNode.__name__: SpawnerTestIntNode,
            SpawnerTestStrNode.__name__: SpawnerTestStrNode,
            SpawnerTestAnotherNode.__name__: SpawnerTestAnotherNode,
        }
    )
    # Populate the node registry. The keys are what the spawner lists.
    return controller


def test_node_spawner_filtering_and_selection(
    qtbot: QtBot, spawner_graph_controller: WorkspaceController
) -> None:
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


def test_clicking_result_spawns_node_in_graph_and_scene(
    qtbot: QtBot, spawner_graph_controller: WorkspaceController
) -> None:
    spawn_position = QPointF(240, 160)
    panel = NodeSpawningPanel(
        controller=spawner_graph_controller,
        spawn_position=spawn_position,
    )
    qtbot.addWidget(panel)
    panel.show()
    panel.search_bar.setText("Another")
    qtbot.waitUntil(lambda: panel.node_list_widget.count() == 1)
    item = panel.node_list_widget.item(0)

    qtbot.mouseClick(
        panel.node_list_widget.viewport(),
        Qt.MouseButton.LeftButton,
        pos=panel.node_list_widget.visualItemRect(item).center(),
    )

    qtbot.waitUntil(lambda: len(spawner_graph_controller.graph.nodes) == 1)
    spawned = next(iter(spawner_graph_controller.graph.nodes.values()))
    node_item = spawner_graph_controller.registry.node_item_for_id(spawned.id)
    assert isinstance(spawned, SpawnerTestAnotherNode)
    assert node_item.scene() is spawner_graph_controller.scene
    assert node_item.pos() != spawn_position
    assert not panel.isVisible()
