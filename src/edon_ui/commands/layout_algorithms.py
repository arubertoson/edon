"""Provides algorithms for graph layout and topology analysis on UI items.

This module contains functions for determining connected subgraphs within selections,
constructing directed graph representations of UI components, and performing
topological sorting for layout ranking.
"""

from collections import deque
from loguru import logger

from edon_ui.items.edge import EdgeItem
from edon_ui.items.node import NodeItem

# XXX: Type Aliases for clarity if complex UI types are involved
# Example: NodeItemType = "NodeItem" # Replace with actual import if available

# XXX: Spacing constants for hierarchical layout (can be adjusted or moved if needed)
H_SPACING_HIERARCHICAL = 100.0  # Horizontal space between ranks
V_SPACING_HIERARCHICAL_WITHIN_RANK = 20.0  # Vertical space between nodes in the same rank
RANK_START_X = 0.0  # Initial X for the first rank
RANK_START_Y = 0.0  # Initial Y for the first node in any rank


def determine_node_selection_topology(
    selected_nodes: list[NodeItem], all_edges_in_scene: list[EdgeItem]
) -> list[list[NodeItem]]:
    """
    Determines the connected subgraphs within a list of selected UI nodes.

    This is useful for applying actions (like layout) independently to
    disconnected groups of selected nodes.

    Args:
        selected_nodes: A list of NodeItem instances that are currently selected.
        all_edges_in_scene: A list of all EdgeItem instances in the scene.

    Returns:
        A list of lists, where each inner list contains NodeItems forming a
        connected subgraph within the original selection.
    """
    if not selected_nodes:
        return []

    # Assuming NodeItem has a 'node_entity_id' string attribute
    adj: dict[str, list[str]] = {node.node_entity_id: [] for node in selected_nodes}
    selected_node_ids_set = {node.node_entity_id for node in selected_nodes}
    node_map_by_id: dict[str, NodeItem] = {node.node_entity_id: node for node in selected_nodes}

    for edge in all_edges_in_scene:
        # Assuming EdgeItem has 'source_socket_item.parent_node_entity_id' and
        # 'target_socket_item.parent_node_entity_id'
        source_id = edge.source_socket_item.parent_node_entity_id  # type: ignore
        target_id = edge.target_socket_item.parent_node_entity_id  # type: ignore

        # Consider only edges between nodes in the current selection
        if source_id in selected_node_ids_set and target_id in selected_node_ids_set:
            adj[source_id].append(target_id)
            adj[target_id].append(source_id)

    visited_ids: set[str] = set()
    subgraphs: list[list[NodeItem]] = []

    for node in selected_nodes:
        if node.node_entity_id not in visited_ids:
            current_subgraph_nodes: list[NodeItem] = []
            q = deque()  # Use collections.deque for efficient queue operations in BFS

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

    logger.debug(f"Determined selection topology: {len(subgraphs)} subgraph(s).")
    for i, sg in enumerate(subgraphs):
        # Assuming NodeItem has a 'title' attribute or fallback to 'node_entity_id'
        titles = [getattr(n, "title", n.node_entity_id) for n in sg]
        logger.debug(f"  Subgraph {i + 1}: {titles}")

    return subgraphs


def get_directed_graph_of_component(
    component_nodes: list[NodeItem], all_edges_in_scene: list[EdgeItem]
) -> dict[str, list[str]]:
    """
    Constructs a directed graph (adjacency list) for connections
    strictly within the given component of UI nodes.

    This is useful for preparing a component for operations like hierarchical layout.

    Args:
        component_nodes: A list of NodeItems forming a connected component.
        all_edges_in_scene: All EdgeItems in the scene.

    Returns:
        A dictionary where keys are node_entity_ids from the component,
        and values are lists of node_entity_ids of their direct children
        also within the component.
    """
    if not component_nodes:
        return {}

    directed_adj: dict[str, list[str]] = {node.node_entity_id: [] for node in component_nodes}
    component_node_ids_set = {node.node_entity_id for node in component_nodes}

    for edge in all_edges_in_scene:
        if not edge.source_socket_item or not edge.target_socket_item:
            logger.trace("get_directed_graph_of_component: Edge missing source/target socket item. Skipping.")
            continue

        source_node_id = edge.source_socket_item.parent_node_entity_id  # type: ignore
        target_node_id = edge.target_socket_item.parent_node_entity_id  # type: ignore

        if source_node_id in component_node_ids_set and target_node_id in component_node_ids_set:
            if target_node_id not in directed_adj[source_node_id]:
                directed_adj[source_node_id].append(target_node_id)

    component_titles = [getattr(n, "title", n.node_entity_id) for n in component_nodes]
    logger.debug(f"Directed graph for component {component_titles}: {directed_adj}")
    return directed_adj


def topological_sort_ui_component(
    directed_adj: dict[str, list[str]],
    nodes_in_component_map: dict[str, NodeItem],
) -> list[list[NodeItem]]:
    """
    Performs a topological sort on a directed graph component of UI nodes.

    The result is a list of ranks (levels), where each rank is a list of nodes.
    This is suitable for hierarchical layout algorithms.

    Args:
        directed_adj: An adjacency list for the component (node_id -> list_of_child_ids).
        nodes_in_component_map: A map from node_id to NodeItem for nodes in this component.

    Returns:
        A list of lists of NodeItems, where each inner list is a rank/level
        in the topological sort. Returns an empty list if a cycle is detected
        or the graph is empty, indicating layout cannot proceed this way.
    """
    if not directed_adj or not nodes_in_component_map:
        return []

    in_degree: dict[str, int] = {node_id: 0 for node_id in directed_adj}
    for node_id in directed_adj:
        for child_id in directed_adj[node_id]:
            if child_id in in_degree:
                in_degree[child_id] += 1
            else:
                logger.warning(
                    f"TopologicalSort: Node '{child_id}' (child of '{node_id}') not in component map. In-degree might be skewed for external nodes."
                )

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
            getattr(nodes_in_component_map[nid], "title", nid)
            for nid, deg in in_degree.items()
            if deg > 0 and nid in nodes_in_component_map
        ]
        logger.warning(
            f"TopologicalSort: Cycle detected in UI component or graph was disconnected. "
            f"Processed {processed_nodes_count}/{len(nodes_in_component_map)} nodes. "
            f"Nodes possibly in cycle: {problematic_nodes}"
        )
        return []

    logger.debug(f"Topological sort of UI component resulted in {len(ranked_nodes)} ranks.")
    return ranked_nodes


# Constants that were in builtins.py, related to arrangement actions that might use these algos.
# Consider if these should live here, or be passed into specific layout functions that use them,
# or live closer to the actions that call these layout functions. For now, co-locating here.
V_SPACING_ARRANGE = 10.0  # General vertical spacing, might be for a different algo
H_SPACING_ARRANGE = 50.0  # General horizontal spacing, might be for a different algo
