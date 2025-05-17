"""Provides the `ExecutionEngine` for processing and running `EntityGraph` instances.

This module defines the `ExecutionEngine`, which is responsible for the orderly
execution of an `EntityGraph`. The core functionality involves:
1.  Topologically sorting the nodes within the graph to determine a valid
    execution sequence that respects data dependencies. This is achieved
    using Kahn's algorithm.
2.  Iterating through the sorted nodes and invoking their `process()` method,
    allowing each node to perform its defined computation or action.

The engine ensures that graphs with cycles are not executed and provides
logging for the execution flow and any errors encountered.
"""

from collections import deque
from loguru import logger

from edon.node import EntityNode
from edon.graph import EntityGraph


class ExecutionEngine:
    """
    Handles the execution of a node graph, including topological sorting
    and node processing.
    """

    def _topological_sort(self, graph: EntityGraph) -> list[EntityNode]:
        """
        Performs a topological sort of the nodes in the graph using Kahn's algorithm.

        Args:
            graph: The EntityGraph instance to sort.

        Returns:
            A list of EntityNode objects in a valid execution order.

        Raises:
            RuntimeError: If a cycle is detected in the graph or if the graph is
                          inconsistent (e.g., not all nodes processed).
        """
        # Initialize in-degree count for all nodes in the graph.
        # The in-degree of a node is the number of incoming edges.
        in_degree: dict[str, int] = {node_id: 0 for node_id in graph.nodes}

        # Calculate initial in-degrees for all nodes.
        # Iterate through each node and its output connections to identify dependencies.
        for u_node_id, u_node in graph.nodes.items():
            for output_socket in u_node.output_sockets.values():
                for connected_input_socket in output_socket.connections:
                    v_node = connected_input_socket.parent_node
                    # If the connected node (v_node) is part of the current graph, increment its in-degree.
                    if v_node and v_node.id in in_degree:
                        in_degree[v_node.id] += 1

        # Initialize a queue with all nodes that have an in-degree of 0.
        # These are the source nodes of the graph (nodes with no incoming dependencies).
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])

        execution_order: list[EntityNode] = []

        while queue:
            # Dequeue a node. This node is now processed and added to the execution order.
            u_node_id = queue.popleft()

            # Ensure the node ID from the queue is actually in the graph before accessing.
            # This is a robustness check, though unlikely to fail in a stable graph state.
            if u_node_id not in graph.nodes:
                logger.warning(f"Node ID '{u_node_id}' from sort queue not in graph.nodes. Skipping.")
                continue

            u_node = graph.nodes[u_node_id]
            execution_order.append(u_node)

            # For each outgoing connection from the processed node (u_node):
            # Decrement the in-degree of the connected (dependent) node (v_node).
            for output_socket in u_node.output_sockets.values():
                for connected_input_socket in output_socket.connections:
                    v_node = connected_input_socket.parent_node
                    if v_node and v_node.id in in_degree:
                        in_degree[v_node.id] -= 1
                        # If a dependent node's in-degree drops to 0, it means all its
                        # prerequisites are met, so it can be added to the queue for processing.
                        if in_degree[v_node.id] == 0:
                            queue.append(v_node.id)

        # After the loop, if the number of nodes in the execution order
        # does not match the total number of nodes in the graph, it indicates a cycle
        # or disconnected components that weren't processed.
        if len(execution_order) != len(graph.nodes):
            # Identify nodes that might be part of a cycle or are otherwise unreachable
            # through this specific sort (nodes with in_degree > 0 after the loop).
            # This condition also catches cases where some nodes might not have been
            # included in the initial in_degree calculation if the graph is inconsistent.
            problematic_nodes_ids = [nid for nid, deg in in_degree.items() if deg > 0]
            # Also consider nodes not in execution_order but were in graph.nodes
            unprocessed_nodes_ids = set(graph.nodes.keys()) - set(n.id for n in execution_order)

            # Combine and get names for a more informative message
            all_problem_ids = problematic_nodes_ids + list(unprocessed_nodes_ids - set(problematic_nodes_ids))
            problem_node_names = [graph.nodes[nid].name for nid in all_problem_ids if nid in graph.nodes]

            if not problem_node_names and len(execution_order) < len(graph.nodes):
                # This case might indicate nodes that were never dependencies and had no outputs,
                # or some other graph inconsistency.
                raise RuntimeError(
                    f"Graph execution error: Not all nodes were processed. "
                    f"Processed {len(execution_order)} of {len(graph.nodes)}. "
                    f"Possible disconnected graph segments or other issues."
                )

            raise RuntimeError(
                f"Graph has a cycle or is disconnected. "
                f"Problematic nodes might include: {problem_node_names}. Cannot execute."
            )

        return execution_order

    def execute_graph(self, graph: EntityGraph):
        """
        Executes the provided graph by processing its nodes in topological order.

        The execution involves:
        1. Performing a topological sort of the graph nodes.
        2. Iterating through the sorted nodes and calling their `process()` method.

        Logs information about the execution flow and errors.

        Args:
            graph: The EntityGraph instance to execute.

        Raises:
            RuntimeError: If the graph cannot be topologically sorted (e.g., due to cycles),
                          re-raised from `_topological_sort`.
        """
        if not graph.nodes:
            logger.info("Graph is empty. Nothing to execute.")
            return

        logger.info("Starting graph execution...")
        try:
            execution_order = self._topological_sort(graph)
        except RuntimeError as e:
            logger.error(f"Failed to prepare graph for execution: {e}")
            raise

        logger.info(f"Execution order: {[node.name for node in execution_order]}")

        for node in execution_order:
            logger.debug(f"Processing node: {node.name} (ID: {node.id})")
            node.process()

        logger.info("Graph execution complete.")
