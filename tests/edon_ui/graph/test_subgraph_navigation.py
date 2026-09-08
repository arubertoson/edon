"""Subgraph navigation through the same command context used by the view."""

import pytest
from pytestqt.qtbot import QtBot

from edon.graph import EntityGraph, EntitySubGraphNode
from edon_ui.commands.actions.basic_actions import action_enter_subgraph, action_exit_subgraph
from edon_ui.graph.controller import WorkspaceController
from edon_ui.items.node import NodeItem
from edon_ui.views.scene import GraphicsScene
from tests.fixtures.nodes import IntegerNode


@pytest.fixture
def workspace_controller(qtbot: QtBot) -> WorkspaceController:
    controller: WorkspaceController = WorkspaceController()
    qtbot.addWidget(controller.view)
    return controller


def test_full_enter_and_exit_subgraph_workflow(
    workspace_controller: WorkspaceController,
) -> None:
    controller: WorkspaceController = workspace_controller
    internal: IntegerNode = IntegerNode(name="Internal")
    subgraph: EntitySubGraphNode = EntitySubGraphNode(name="Subgraph")
    subgraph.internal_graph.add_node(internal)
    root: EntityGraph = EntityGraph()
    root.add_node(subgraph)
    controller.load_graph(root)
    # Loading copies graph data into a fresh root; navigation must restore that root.
    loaded_root: EntityGraph = controller.graph
    assert loaded_root.get_node(subgraph.id) is subgraph
    original_scene: GraphicsScene = controller.scene
    subgraph_item: NodeItem = controller.registry.node_item_for_id(subgraph.id)
    subgraph_item.setSelected(True)

    assert action_enter_subgraph(controller.view.provide_context())
    assert controller.context_stack.depth == 2
    assert not controller.context_stack.is_at_root()
    assert controller.graph is subgraph.internal_graph
    assert controller.scene is not original_scene
    assert controller.view.scene() is controller.scene
    assert controller.context_stack.current.origin_subgraph_node is subgraph
    assert controller.registry.node_item_for_id(internal.id).entity_id == internal.id

    assert action_exit_subgraph(controller.view.provide_context())
    assert controller.context_stack.is_at_root()
    assert controller.context_stack.depth == 1
    assert controller.graph is loaded_root
    assert controller.scene is original_scene
    assert controller.view.scene() is original_scene
    assert controller.registry.node_item_for_id(subgraph.id) is subgraph_item


@pytest.mark.parametrize("selection", ["none", "regular", "multiple"])
def test_enter_subgraph_conditions(
    workspace_controller: WorkspaceController,
    selection: str,
) -> None:
    controller: WorkspaceController = workspace_controller
    subgraph: EntitySubGraphNode = EntitySubGraphNode()
    regular: IntegerNode = IntegerNode()
    root: EntityGraph = EntityGraph()
    root.add_node(subgraph)
    root.add_node(regular)
    controller.load_graph(root)
    loaded_root: EntityGraph = controller.graph
    if selection in ("regular", "multiple"):
        controller.registry.node_item_for_id(regular.id).setSelected(True)
    if selection == "multiple":
        controller.registry.node_item_for_id(subgraph.id).setSelected(True)

    assert not action_enter_subgraph(controller.view.provide_context())
    assert controller.context_stack.depth == 1
    assert controller.graph is loaded_root


def test_exit_subgraph_at_root(workspace_controller: WorkspaceController) -> None:
    assert not action_exit_subgraph(workspace_controller.view.provide_context())
    assert workspace_controller.context_stack.is_at_root()
    assert workspace_controller.context_stack.depth == 1
