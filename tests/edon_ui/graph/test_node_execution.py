"""UI integration tests for executing and inspecting a selected node."""

from typing import cast

from PySide6.QtWidgets import QLineEdit

from edon.graph import EntityGraph
from edon.node import EntityNode
from edon.types import EdgeKey
from edon_ui.commands.actions.basic_actions import action_execute_node
from edon_ui.graph.controller import WorkspaceController
from tests.fixtures.nodes import AddNode, IntegerNode


class FailingNode(AddNode):
    def process(self) -> None:
        raise ValueError("cannot calculate")


def link(graph: EntityGraph, source: EntityNode, target: EntityNode) -> None:
    linked, reason = graph.link_sockets(
        EdgeKey(source.sockets["src_int"].address, target.sockets["a"].address)
    )
    assert linked, reason


def test_execute_node_shows_authoritative_output(qtbot) -> None:
    graph = EntityGraph()
    source = IntegerNode()
    target = AddNode()
    graph.add_node(source)
    graph.add_node(target)
    graph.set_input_value(source.sockets["trg_int"].address, 6)
    link(graph, source, target)
    controller = WorkspaceController()
    qtbot.addWidget(controller.view)
    controller.load_graph(graph)

    controller.registry.node_item_for_id(target.id).setSelected(True)
    assert action_execute_node(controller.view.provide_context())
    qtbot.waitUntil(lambda: controller._execution_thread is None)

    assert target.sockets["result"].value == 6
    assert controller._node_inspector is not None
    assert controller._node_inspector.parentItem() is controller.registry.node_item_for_id(
        target.id
    )

    input_item = controller.registry.socket_item_for_address(source.sockets["trg_int"].address)
    editor = cast(QLineEdit, input_item.components.widget.proxy.widget())
    editor.setText("8")
    editor.editingFinished.emit()

    assert source.sockets["trg_int"].value == 8
    assert all(node.execution_dirty for node in controller.graph.nodes.values())


def test_execute_node_marks_and_inspects_failure(qtbot) -> None:
    graph = EntityGraph()
    node = FailingNode()
    graph.add_node(node)
    controller = WorkspaceController()
    qtbot.addWidget(controller.view)
    controller.load_graph(graph)

    controller.execute_node(node.id)
    qtbot.waitUntil(lambda: controller._execution_thread is None)

    assert isinstance(node.execution_error, ValueError)
    assert controller._node_inspector is not None
    assert controller._node_inspector.parentItem() is controller.registry.node_item_for_id(node.id)
