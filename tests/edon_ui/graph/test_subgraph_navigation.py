"""Subgraph navigation through the same command context used by the view."""

import pytest
from pytestqt.qtbot import QtBot

from edon.graph import EntityGraph, EntitySubGraphNode
from edon.nodes.utility import SubgraphPromoterNode
from edon.types import SocketDisplayState
from edon_ui.commands.actions.basic_actions import action_enter_subgraph, action_exit_subgraph
from edon_ui.graph.controller import WorkspaceController
from edon_ui.items.node import NodeItem
from edon_ui.views.scene import GraphicsScene
from tests.fixtures.nodes import AddNode, IntegerNode


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


def test_promoter_exposes_both_roles_without_internal_edges(
    workspace_controller: WorkspaceController,
) -> None:
    controller = workspace_controller
    first = AddNode(name="First")
    second = AddNode(name="Second")
    parameter = IntegerNode(name="Parameter")
    promoter = SubgraphPromoterNode()
    subgraph = EntitySubGraphNode(name="Subgraph")
    for node in (first, second, parameter, promoter):
        subgraph.internal_graph.add_node(node)

    root = EntityGraph()
    root.add_node(subgraph)
    controller.load_graph(root)
    controller.registry.node_item_for_id(subgraph.id).setSelected(True)
    assert action_enter_subgraph(controller.view.provide_context())

    for internal in (first, second):
        controller.handle_ui_edge_link_request(
            promoter.sockets["src_promoter"].address,
            internal.sockets["a"].address,
        )
        controller.handle_ui_edge_link_request(
            internal.sockets["result"].address,
            promoter.sockets["trg_promoter"].address,
        )

    controller.handle_ui_edge_link_request(
        promoter.sockets["src_promoter"].address,
        parameter.sockets["trg_int"].address,
    )
    # Re-promoting toggles the interface socket off; another promotion restores it.
    for _ in range(2):
        controller.handle_ui_edge_link_request(
            promoter.sockets["src_promoter"].address,
            first.sockets["a"].address,
        )

    assert not subgraph.internal_graph.edges
    assert set(subgraph.sockets) == {"a", "a_2", "result", "result_2", "trg_int"}
    assert {socket.name for socket in subgraph.target_sockets} == {"a", "a_2", "trg_int"}
    assert {socket.name for socket in subgraph.source_sockets} == {"result", "result_2"}

    parent_state = controller.context_stack.parent
    assert parent_state is not None
    for socket in subgraph.sockets.values():
        socket_item = parent_state.registry.socket_item_for_address(socket.address)
        assert socket_item.role is socket.role
        assert socket_item.components.display_state is SocketDisplayState.ALL


def test_deleting_internal_node_removes_proxy_and_parent_edges(
    workspace_controller: WorkspaceController,
) -> None:
    controller = workspace_controller
    internal = AddNode(name="Internal")
    promoter = SubgraphPromoterNode()
    subgraph = EntitySubGraphNode(name="Subgraph")
    subgraph.internal_graph.add_node(internal)
    subgraph.internal_graph.add_node(promoter)
    external = IntegerNode(name="External")
    root = EntityGraph()
    root.add_node(subgraph)
    root.add_node(external)
    controller.load_graph(root)

    controller.registry.node_item_for_id(subgraph.id).setSelected(True)
    assert action_enter_subgraph(controller.view.provide_context())
    controller.handle_ui_edge_link_request(
        promoter.sockets["src_promoter"].address,
        internal.sockets["a"].address,
    )
    proxy_address = subgraph.sockets["a"].address

    assert action_exit_subgraph(controller.view.provide_context())
    controller.handle_ui_edge_link_request(
        external.sockets["src_int"].address,
        proxy_address,
    )
    assert len(controller.graph.edges) == 1

    controller.registry.node_item_for_id(subgraph.id).setSelected(True)
    assert action_enter_subgraph(controller.view.provide_context())
    controller.request_remove_node(internal.id)

    parent_state = controller.context_stack.parent
    assert parent_state is not None
    assert internal.id not in subgraph.internal_graph.nodes
    assert "a" not in subgraph.sockets
    assert not parent_state.graph.edges
    assert proxy_address not in {item.address for item in parent_state.registry.sockets}


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
