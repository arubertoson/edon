"""Subgraph navigation through the same command context used by the view."""

import pytest
from pytestqt.qtbot import QtBot
from PySide6.QtCore import QPointF

from edon.executor import ExecutionEngine
from edon.graph import EntityGraph, EntitySubGraphNode
from edon.nodes.utility import SubgraphPromoterNode
from edon.types import SocketDisplayState, SocketRole
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


def test_loaded_subgraph_output_has_no_value_editor(
    workspace_controller: WorkspaceController,
) -> None:
    internal = AddNode(name="Internal")
    subgraph = EntitySubGraphNode(name="Subgraph")
    subgraph.internal_graph.add_node(internal)
    subgraph.add_proxy_socket("input", internal.sockets["a"].address)
    subgraph.add_proxy_socket("output", internal.sockets["result"].address)
    root = EntityGraph()
    root.add_node(subgraph)

    workspace_controller.load_graph(root)

    input_item = workspace_controller.registry.socket_item_for_address(
        subgraph.sockets["input"].address
    )
    output_item = workspace_controller.registry.socket_item_for_address(
        subgraph.sockets["output"].address
    )
    assert input_item.components.display_state is SocketDisplayState.ALL
    assert input_item.components.widget.isVisible()
    assert output_item.components.display_state is SocketDisplayState.LINK_LABEL
    assert not output_item.components.widget.isVisible()


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
    # Repeated promotion must not remove the existing interface socket.
    original_proxy = subgraph.sockets["a"]
    for _ in range(3):
        controller.handle_ui_edge_link_request(
            promoter.sockets["src_promoter"].address,
            first.sockets["a"].address,
        )

    assert subgraph.sockets["a"] is original_proxy
    assert len(controller.registry.promotion_links) == 5
    assert not controller.registry.edges
    assert not subgraph.internal_graph.edges
    for item in controller.registry.promotion_links.values():
        assert item.scene() is controller.scene
        source, target = item.edge_key.source, item.edge_key.target
        assert target in controller.partition_socket_drop_targets(source)[0]
        assert source in controller.partition_socket_drop_targets(target)[0]
    assert set(subgraph.sockets) == {"a", "a_2", "result", "result_2", "trg_int"}
    assert {socket.name for socket in subgraph.target_sockets} == {"a", "a_2", "trg_int"}
    assert {socket.name for socket in subgraph.source_sockets} == {"result", "result_2"}

    parent_state = controller.context_stack.parent
    assert parent_state is not None
    for socket in subgraph.sockets.values():
        socket_item = parent_state.registry.socket_item_for_address(socket.address)
        assert socket_item.role is socket.role
        expected_state = (
            SocketDisplayState.LINK_LABEL
            if socket.role is SocketRole.SOURCE
            else SocketDisplayState.ALL
        )
        assert socket_item.components.display_state is expected_state
        assert socket_item.components.widget.isVisible() is (socket.role is SocketRole.TARGET)


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
    assert not subgraph.promotion_links
    assert not controller.registry.promotion_links
    assert not parent_state.graph.edges
    assert proxy_address not in {item.address for item in parent_state.registry.sockets}


@pytest.mark.parametrize("remove", ["proxy", "line", "internal", "promoter"])
def test_promotion_link_lifecycle(workspace_controller: WorkspaceController, remove: str) -> None:
    controller = workspace_controller
    internal = IntegerNode()
    promoter = SubgraphPromoterNode()
    other_promoter = SubgraphPromoterNode()
    subgraph = EntitySubGraphNode()
    for node in (internal, other_promoter, promoter):
        subgraph.internal_graph.add_node(node)
    root = EntityGraph()
    root.add_node(subgraph)
    controller.load_graph(root)
    controller.enter_subgraph(controller.registry.node_item_for_id(subgraph.id))
    for source, target in (
        (promoter.sockets["src_promoter"], internal.sockets["trg_int"]),
        (internal.sockets["src_int"], promoter.sockets["trg_promoter"]),
    ):
        controller.handle_ui_edge_link_request(source.address, target.address)

    # Domain mappings survive both navigation and a root UI reload.
    expected_links = subgraph.promotion_links
    controller.exit_subgraph()
    controller.load_graph(root)
    controller.enter_subgraph(controller.registry.node_item_for_id(subgraph.id))
    assert {
        name: item.edge_key for name, item in controller.registry.promotion_links.items()
    } == expected_links
    assert not controller.registry.edges
    assert not subgraph.internal_graph.edges

    for node in (internal, promoter):
        item = controller.registry.promotion_links["trg_int"]
        old_path = item.path()
        controller.registry.node_item_for_id(node.id).moveBy(120, 70)
        assert item.path() != old_path
        assert item.path().pointAtPercent(0) == item.source_socket_item.link_item.scenePos()
        assert item.path().pointAtPercent(1) == item.target_socket_item.link_item.scenePos()

    subgraph.sockets["trg_int"].value = 42
    ExecutionEngine().execute_graph(root)
    assert subgraph.sockets["src_int"].value == 42

    removed_items = list(controller.registry.promotion_links.values())
    if remove == "proxy":
        for name in list(subgraph.sockets):
            controller.request_remove_socket_from_subgraph(name)
    elif remove == "line":
        controller.handle_ui_edge_deletion_request(removed_items)
    else:
        controller.request_remove_node(internal.id if remove == "internal" else promoter.id)
    assert not subgraph.sockets
    assert not subgraph.promotion_links
    assert not controller.registry.promotion_links
    assert all(item.scene() is None for item in removed_items)
    controller.exit_subgraph()
    controller.enter_subgraph(controller.registry.node_item_for_id(subgraph.id))
    assert not controller.registry.promotion_links


def test_promotion_does_not_replace_data_edges(
    workspace_controller: WorkspaceController,
) -> None:
    controller = workspace_controller
    internal = IntegerNode()
    upstream = IntegerNode()
    promoter = SubgraphPromoterNode()
    subgraph = EntitySubGraphNode()
    for node in (internal, upstream, promoter):
        subgraph.internal_graph.add_node(node)
    root = EntityGraph()
    root.add_node(subgraph)
    controller.load_graph(root)
    controller.enter_subgraph(controller.registry.node_item_for_id(subgraph.id))
    source = upstream.sockets["src_int"].address
    target = internal.sockets["trg_int"].address
    interface = promoter.sockets["src_promoter"].address
    controller.handle_ui_edge_link_request(source, target)
    data_edges = set(controller.graph.edges)
    assert target in controller.partition_socket_drop_targets(interface)[0]
    assert interface in controller.partition_socket_drop_targets(target)[0]
    controller.handle_ui_edge_link_request(interface, target)
    assert controller.graph.edges == data_edges
    assert len(controller.registry.edges) == 1
    assert len(controller.registry.promotion_links) == 1
    # A promoter drag never lifts an interface line as though it were a data edge.
    controller.handle_ui_init_edge_drag_action(interface, QPointF(), controller.scene)
    assert len(controller.registry.promotion_links) == 1
    assert controller.graph.edges == data_edges


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
