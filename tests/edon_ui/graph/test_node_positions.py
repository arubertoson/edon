"""Node model positions and their UI synchronization."""

from PySide6.QtCore import QPointF
from pytestqt.qtbot import QtBot

from edon.graph import EntityGraph
from edon_ui.graph.controller import WorkspaceController
from edon_ui.items.node import NodeItem
from tests.fixtures.nodes import AddNode


def test_model_position_is_loaded_and_tracks_ui_moves(qtbot: QtBot) -> None:
    node = AddNode(name="Positioned", position=(125.0, 275.0))
    graph = EntityGraph()
    graph.add_node(node)
    controller = WorkspaceController()
    qtbot.addWidget(controller.view)

    controller.load_graph(graph)

    node_item: NodeItem = controller.registry.node_item_for_id(node.id)
    assert node_item.pos() == QPointF(125.0, 275.0)

    node_item.setPos(400.0, 500.0)
    assert node.position == (400.0, 500.0)
