"""Layout topology must use actual UI node and edge identities."""

from pytestqt.qtbot import QtBot

from edon.graph import EntityGraph
from edon.types import EdgeKey
from edon_ui.commands.layout_algorithms import (
    determine_node_selection_topology,
    get_directed_graph_of_component,
    topological_sort_ui_component,
)
from edon_ui.graph.controller import WorkspaceController
from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem
from tests.fixtures.nodes import AddNode


def test_layout_topology_with_connected_and_unselected_nodes(qtbot: QtBot) -> None:
    graph: EntityGraph = EntityGraph()
    nodes: list[AddNode] = [AddNode(name=f"Node_{index}") for index in range(4)]
    for node in nodes:
        graph.add_node(node)
    for source, target in ((nodes[0], nodes[1]), (nodes[1], nodes[2])):
        edge: EdgeKey = EdgeKey(source.sockets["result"].address, target.sockets["a"].address)
        success, reason = graph.link_sockets(edge)
        assert success, reason
    controller: WorkspaceController = WorkspaceController()
    qtbot.addWidget(controller.view)
    controller.load_graph(graph)
    items: list[NodeItem] = [controller.registry.node_item_for_id(node.id) for node in nodes]
    edges: list[EdgeItem] = list(controller.registry.edges)

    components: list[list[NodeItem]] = determine_node_selection_topology(items, edges)
    assert [{item.entity_id for item in group} for group in components] == [
        {node.id for node in nodes[:3]},
        {nodes[3].id},
    ]
    selected: list[NodeItem] = [items[0], items[1], items[3]]
    adjacency: dict[str, list[str]] = get_directed_graph_of_component(selected, edges)
    assert adjacency == {nodes[0].id: [nodes[1].id], nodes[1].id: [], nodes[3].id: []}
    assert determine_node_selection_topology([], edges) == []
    assert get_directed_graph_of_component([], edges) == {}
    disconnected: list[list[NodeItem]] = determine_node_selection_topology(
        [items[0], items[2]], edges
    )
    assert [[item.entity_id for item in group] for group in disconnected] == [
        [nodes[0].id],
        [nodes[2].id],
    ]
    ranks: list[list[NodeItem]] = topological_sort_ui_component(
        get_directed_graph_of_component(items[:3], edges),
        {item.entity_id: item for item in items[:3]},
    )
    assert [[item.entity_id for item in rank] for rank in ranks] == [
        [node.id] for node in nodes[:3]
    ]
