"""Actions related to node arrangement and graph layout algorithms."""

from collections import deque
from loguru import logger

from edon_ui.graphics.view import EditorContext  # Assuming EditorContext is here
from edon_ui.items.node import NodeItem
from edon_ui.items.edge import EdgeItem
from edon_ui.items.socket import SocketRowItem

# Spacing constants for arrangement algorithms
V_SPACING_ARRANGE = 10.0  # For stacking inputs to an external parent
H_SPACING_ARRANGE = 50.0  # For stacking inputs to an external parent

H_SPACING_HIERARCHICAL = 100.0  # Horizontal space between ranks
V_SPACING_HIERARCHICAL_WITHIN_RANK = 20.0  # Vertical space between nodes in the same rank
RANK_START_X = 0.0
RANK_START_Y = 0.0


def determine_node_selection_topology(
    selected_nodes: list[NodeItem], all_edges_in_scene: list[EdgeItem]
) -> list[list[NodeItem]]:
    # ... (Implementation of determine_node_selection_topology - already provided in previous steps)
    if not selected_nodes:
        return []
    adj: dict[str, list[str]] = {node.node_entity_id: [] for node in selected_nodes}
    selected_node_ids_set = {node.node_entity_id for node in selected_nodes}
    node_map_by_id: dict[str, NodeItem] = {node.node_entity_id: node for node in selected_nodes}
    for edge in all_edges_in_scene:
        if not (edge.source_socket_item and edge.source_socket_item.parentItem()):
            continue
        if not (edge.target_socket_item and edge.target_socket_item.parentItem()):
            continue
        source_id = edge.source_socket_item.parent_node_entity_id
        target_id = edge.target_socket_item.parent_node_entity_id
        if source_id in selected_node_ids_set and target_id in selected_node_ids_set:
            adj[source_id].append(target_id)
            adj[target_id].append(source_id)
    visited_ids: set[str] = set()
    subgraphs: list[list[NodeItem]] = []
    for node in selected_nodes:
        if node.node_entity_id not in visited_ids:
            current_subgraph_nodes: list[NodeItem] = []
            q = deque()
            q.append(node)
            visited_ids.add(node.node_entity_id)
            while q:
                curr_node = q.popleft()
                current_subgraph_nodes.append(curr_node)
                for neighbor_id in adj[curr_node.node_entity_id]:
                    if neighbor_id not in visited_ids:
                        visited_ids.add(neighbor_id)
                        q.append(node_map_by_id[neighbor_id])
            if current_subgraph_nodes:
                subgraphs.append(current_subgraph_nodes)
    component_titles_list = []
    for i, sg in enumerate(subgraphs):
        titles = [n.title if hasattr(n, "title") else n.node_entity_id for n in sg]
        component_titles_list.append(titles)
    logger.debug(f"Determined selection topology: {len(subgraphs)} subgraph(s): {component_titles_list}")
    return subgraphs


def get_directed_graph_of_component(
    component_nodes: list[NodeItem], all_edges_in_scene: list[EdgeItem]
) -> dict[str, list[str]]:
    # ... (Implementation of get_directed_graph_of_component - already provided)
    if not component_nodes:
        return {}
    directed_adj: dict[str, list[str]] = {node.node_entity_id: [] for node in component_nodes}
    component_node_ids_set = {node.node_entity_id for node in component_nodes}
    for edge in all_edges_in_scene:
        if not edge.source_socket_item or not edge.target_socket_item:
            logger.trace("DirectedGraph: Edge missing source or target socket item. Skipping.")
            continue
        source_node_id = edge.source_socket_item.parent_node_entity_id
        target_node_id = edge.target_socket_item.parent_node_entity_id
        if source_node_id in component_node_ids_set and target_node_id in component_node_ids_set:
            if target_node_id not in directed_adj[source_node_id]:
                directed_adj[source_node_id].append(target_node_id)
    component_titles = [n.title if hasattr(n, "title") else n.node_entity_id for n in component_nodes]
    logger.debug(f"Directed graph for component {component_titles}: {directed_adj}")
    return directed_adj


def topological_sort_ui_component(
    directed_adj: dict[str, list[str]],
    nodes_in_component_map: dict[str, NodeItem],
) -> list[list[NodeItem]]:
    # ... (Implementation of topological_sort_ui_component - already provided)
    if not directed_adj or not nodes_in_component_map:
        return []
    in_degree: dict[str, int] = {node_id: 0 for node_id in directed_adj}
    for node_id in directed_adj:
        for child_id in directed_adj[node_id]:
            if child_id in in_degree:
                in_degree[child_id] += 1
            else:
                logger.warning(f"TopologicalSort: Node '{child_id}' (child of '{node_id}') not in component map.")
    queue = deque()
    for node_id in directed_adj:
        if in_degree[node_id] == 0:
            queue.append(node_id)
    ranked_nodes: list[list[NodeItem]] = []
    processed_nodes_count = 0
    while queue:
        current_rank_node_ids = list(queue)
        queue.clear()
        current_rank_node_items: list[NodeItem] = []
        if not current_rank_node_ids:
            break
        for node_id in current_rank_node_ids:
            if node_id in nodes_in_component_map:
                current_rank_node_items.append(nodes_in_component_map[node_id])
                processed_nodes_count += 1
            else:
                logger.error(f"TopologicalSort: Node ID '{node_id}' from queue not found in component map.")
                continue
            for child_id in directed_adj.get(node_id, []):
                if child_id in in_degree:
                    in_degree[child_id] -= 1
                    if in_degree[child_id] == 0:
                        queue.append(child_id)
        if current_rank_node_items:
            ranked_nodes.append(current_rank_node_items)
    if processed_nodes_count != len(nodes_in_component_map):
        problematic_nodes = [
            nodes_in_component_map[nid].title
            for nid, deg in in_degree.items()
            if deg > 0 and nid in nodes_in_component_map
        ]
        logger.warning(
            f"TopologicalSort: Cycle detected. Processed {processed_nodes_count}/{len(nodes_in_component_map)}. Problematic: {problematic_nodes}"
        )
        return []
    logger.debug(f"Topological sort of UI component resulted in {len(ranked_nodes)} ranks.")
    return ranked_nodes


def _arrange_component_inputs_to_parent(
    nodes_in_component: list[NodeItem],
    all_edges_in_scene: list[EdgeItem],
    graph_manager,  # GraphController, has 'node_map'
) -> bool:
    # ... (Implementation of _arrange_component_inputs_to_parent - already provided)
    if not nodes_in_component:
        return False
    logger.debug(f"Arranging component (stack inputs): {[n.title for n in nodes_in_component]}")
    potential_parents_connections: dict[str, list[tuple[NodeItem, SocketRowItem, SocketRowItem]]] = {}
    component_node_ids = {n.node_entity_id for n in nodes_in_component}
    for edge in all_edges_in_scene:
        if not (edge.source_socket_item and edge.source_socket_item.parentItem()):
            continue
        if not (edge.target_socket_item and edge.target_socket_item.parentItem()):
            continue
        source_node_id = edge.source_socket_item.parent_node_entity_id
        target_node_id = edge.target_socket_item.parent_node_entity_id
        if source_node_id not in component_node_ids:
            continue
        if target_node_id in component_node_ids:
            continue
        selected_source_node_item = next((n for n in nodes_in_component if n.node_entity_id == source_node_id), None)
        if not selected_source_node_item:
            continue
        source_socket_row = edge.source_socket_item.parentItem()
        target_socket_row = edge.target_socket_item.parentItem()
        if not (isinstance(source_socket_row, SocketRowItem) and isinstance(target_socket_row, SocketRowItem)):
            continue
        if not target_socket_row.is_input:
            continue
        potential_parents_connections.setdefault(target_node_id, []).append(
            (selected_source_node_item, source_socket_row, target_socket_row)
        )
    if not potential_parents_connections:
        return False
    common_parent_id = None
    connections_to_common_parent = []
    for parent_id, conns in potential_parents_connections.items():
        if {c[0].node_entity_id for c in conns} == component_node_ids:
            common_parent_id = parent_id
            connections_to_common_parent = conns
            break
    if not common_parent_id:
        return False
    parent_node_item: NodeItem = graph_manager.node_map.get(common_parent_id)
    if not parent_node_item:
        return False

    def get_socket_order_key(conn_tuple):
        try:
            return parent_node_item._input_sockets.index(conn_tuple[2])
        except ValueError:
            return float("inf")

    connections_to_common_parent.sort(key=get_socket_order_key)
    sorted_input_nodes_to_stack = [c[0] for c in connections_to_common_parent]
    if not sorted_input_nodes_to_stack:
        return False
    max_input_node_width = max(n._width for n in sorted_input_nodes_to_stack) if sorted_input_nodes_to_stack else 0
    stack_x = parent_node_item.x() - max_input_node_width - H_SPACING_ARRANGE
    calculated_initial_y_for_stack = parent_node_item.y()
    if connections_to_common_parent:
        out_s_row = connections_to_common_parent[0][1]
        in_s_row = connections_to_common_parent[0][2]
        parent_input_center_y = parent_node_item.y() + in_s_row.y() + in_s_row.get_required_height() / 2.0
        stacked_node_output_center_y = out_s_row.y() + out_s_row.get_required_height() / 2.0
        calculated_initial_y_for_stack = parent_input_center_y - stacked_node_output_center_y
    current_y = calculated_initial_y_for_stack
    for node_to_stack in sorted_input_nodes_to_stack:
        node_to_stack.setPos(stack_x, current_y)
        current_y += node_to_stack._height + V_SPACING_ARRANGE
    logger.info(
        f"Arranged {len(sorted_input_nodes_to_stack)} nodes (stack inputs) for parent '{parent_node_item.title}'."
    )
    return True


def arrange_nodes_action(context: EditorContext) -> bool:  # This is the "Stack Inputs" command
    # ... (Implementation of arrange_nodes_action using _arrange_component_inputs_to_parent - already provided)
    if (
        not context
        or not hasattr(context, "view")
        or not context.view
        or not hasattr(context.view, "scene")
        or not context.view.scene()
        or not hasattr(context, "manager")
        or not context.manager
    ):
        logger.warning("Arrange (Stack Inputs): Invalid context.")
        return False
    scene = context.view.scene()
    graph_manager = context.manager
    selected_nodes = [item for item in context.selected_items if isinstance(item, NodeItem)]
    if not selected_nodes:
        return False
    all_edges: list[EdgeItem] = scene.edge_items
    subgraphs = determine_node_selection_topology(selected_nodes, all_edges)
    if not subgraphs:
        return False
    arranged_once = False
    for component_nodes in subgraphs:
        if _arrange_component_inputs_to_parent(component_nodes, all_edges, graph_manager):
            arranged_once = True
    if not arranged_once:
        logger.info("Arrange (Stack Inputs): No components suitable.")
    return arranged_once


def arrange_component_hierarchically_action(context: EditorContext) -> bool:
    # ... (Implementation of arrange_component_hierarchically_action - already provided, including the fix for ranking)
    if (
        not context
        or not hasattr(context, "view")
        or not context.view
        or not hasattr(context.view, "scene")
        or not context.view.scene()
    ):
        logger.warning("Arrange Hierarchical: Invalid context.")
        return False
    scene = context.view.scene()
    selected_nodes: list[NodeItem] = [item for item in context.selected_items if isinstance(item, NodeItem)]
    if not selected_nodes:
        return False
    all_edges: list[EdgeItem] = scene.edge_items
    subgraphs = determine_node_selection_topology(selected_nodes, all_edges)
    if not subgraphs:
        return False
    arrangement_performed = False
    current_layout_start_x = RANK_START_X
    for component_nodes_list in subgraphs:
        if not component_nodes_list:
            continue
        component_node_map: dict[str, NodeItem] = {node.node_entity_id: node for node in component_nodes_list}
        directed_adj = get_directed_graph_of_component(component_nodes_list, all_edges)
        if not directed_adj:
            continue
        ranked_node_groups = topological_sort_ui_component(directed_adj, component_node_map)
        if not ranked_node_groups:
            continue
        logger.debug(f"Arranging component hierarchically: {[n.title for n in component_nodes_list]}")
        component_origin_x = current_layout_start_x
        current_rank_x = component_origin_x
        max_x_reached_in_component = component_origin_x
        for rank_idx, nodes_in_rank in enumerate(ranked_node_groups):
            current_y_in_rank = RANK_START_Y
            max_width_this_rank = max(n._width for n in nodes_in_rank) if nodes_in_rank else 0.0
            sorted_nodes_for_this_rank = list(nodes_in_rank)
            if rank_idx < len(ranked_node_groups) - 1:
                next_rank_nodes = ranked_node_groups[rank_idx + 1]
                common_target_in_next_rank: NodeItem | None = None
                if sorted_nodes_for_this_rank:
                    first_node_target_ids = {
                        edge.target_socket_item.parent_node_entity_id
                        for edge in all_edges
                        if edge.source_socket_item.parent_node_entity_id
                        == sorted_nodes_for_this_rank[0].node_entity_id
                        and edge.target_socket_item.parent_node_entity_id
                        in [n.node_entity_id for n in next_rank_nodes]
                    }
                    if len(first_node_target_ids) == 1:
                        potential_common_target_id = list(first_node_target_ids)[0]
                        all_connect_to_this = all(
                            (
                                {
                                    edge.target_socket_item.parent_node_entity_id
                                    for edge in all_edges
                                    if edge.source_socket_item.parent_node_entity_id == other_node.node_entity_id
                                    and edge.target_socket_item.parent_node_entity_id
                                    in [n.node_entity_id for n in next_rank_nodes]
                                }
                            )
                            == {potential_common_target_id}
                            for other_node in sorted_nodes_for_this_rank[1:]
                        )
                        if all_connect_to_this:
                            common_target_in_next_rank = next(
                                (n for n in next_rank_nodes if n.node_entity_id == potential_common_target_id), None
                            )
                if common_target_in_next_rank:
                    logger.debug(
                        f"Rank {rank_idx} nodes sorted by common target '{common_target_in_next_rank.title}' inputs."
                    )
                    source_to_target_socket_map: dict[str, SocketRowItem] = {}
                    for node_in_curr_rank in sorted_nodes_for_this_rank:
                        for edge in all_edges:
                            if (
                                edge.source_socket_item.parent_node_entity_id == node_in_curr_rank.node_entity_id
                                and edge.target_socket_item.parent_node_entity_id
                                == common_target_in_next_rank.node_entity_id
                            ):
                                target_s_r = edge.target_socket_item.parentItem()
                                if isinstance(target_s_r, SocketRowItem):
                                    source_to_target_socket_map[node_in_curr_rank.node_entity_id] = target_s_r
                                    break

                    def get_hier_sort_key(node_item: NodeItem):
                        tsr = source_to_target_socket_map.get(node_item.node_entity_id)
                        try:
                            return (
                                common_target_in_next_rank._input_sockets.index(tsr)
                                if tsr and common_target_in_next_rank
                                else float("inf")
                            )
                        except ValueError:
                            return float("inf")

                    sorted_nodes_for_this_rank.sort(key=get_hier_sort_key)
            for node_item in sorted_nodes_for_this_rank:
                node_item.setPos(current_rank_x, current_y_in_rank)
                current_y_in_rank += node_item._height + V_SPACING_HIERARCHICAL_WITHIN_RANK
            if nodes_in_rank:
                current_rank_x += max_width_this_rank + H_SPACING_HIERARCHICAL
                max_x_reached_in_component = max(max_x_reached_in_component, current_rank_x)
        arrangement_performed = True
        if max_x_reached_in_component > component_origin_x:
            current_layout_start_x = max_x_reached_in_component  # Advance X for next component to start after this one
    if not arrangement_performed:
        return False
    return True
