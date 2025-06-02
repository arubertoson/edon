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

Enhanced to support recursive execution of sub-graphs with depth tracking
and context management.
"""

from collections import deque
from loguru import logger

from edon.node import EntityNode
from edon.graph import EntityGraph
from edon.types import current_graph_context, current_execution_engine_context


class ExecutionEngine:
    """
    Handles the execution of a node graph, including topological sorting
    and node processing.

    Supports recursive execution of sub-graphs with configurable depth limits
    to prevent infinite recursion.
    """

    def __init__(self, max_depth: int = 10):
        """Initialize the execution engine.

        Args:
            max_depth: Maximum allowed nesting depth for sub-graph execution.
                      Prevents infinite recursion in malformed sub-graphs.
        """
        self.max_depth = max_depth
        self._current_depth = 0

    def _topological_sort(self, graph: EntityGraph) -> list[EntityNode]:
        """
        Performs a topological sort of the nodes in the graph using Kahn's algorithm.
        """
        # Initialize in-degree count for all nodes in the graph.
        # The in-degree of a node is the number of incoming edges.
        in_degree: dict[str, int] = {node_id: 0 for node_id in graph.nodes}

        # Calculate initial in-degrees for all nodes.
        # Use graph edges to determine dependencies instead of socket.links
        for edge in graph.edges:
            # In a directed edge from source to target, target depends on source
            # So target has incoming degree from source
            target_node_id = edge.target.node_id
            if target_node_id in in_degree:
                in_degree[target_node_id] += 1

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
                logger.warning(
                    f"Node ID '{u_node_id}' from sort queue not in graph.nodes. Skipping."
                )
                continue

            u_node = graph.nodes[u_node_id]
            execution_order.append(u_node)

            # For each outgoing connection from the processed node (u_node):
            # Decrement the in-degree of the connected (dependent) node (v_node).
            for edge in graph.edges:
                if edge.source.node_id == u_node_id:
                    v_node_id = edge.target.node_id
                    if v_node_id in in_degree:
                        in_degree[v_node_id] -= 1
                        # If a dependent node's in-degree drops to 0, it means all its
                        # prerequisites are met, so it can be added to the queue for processing.
                        if in_degree[v_node_id] == 0:
                            queue.append(v_node_id)

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
            all_problem_ids = problematic_nodes_ids + list(
                unprocessed_nodes_ids - set(problematic_nodes_ids)
            )
            problem_node_names = [
                graph.nodes[nid].name for nid in all_problem_ids if nid in graph.nodes
            ]

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

    def execute_graph(self, graph: EntityGraph, context: str = "root") -> None:
        """
        Executes the provided graph by processing its nodes in topological order.

        The execution involves:
        1. Performing a topological sort of the graph nodes.
        2. Iterating through the sorted nodes and calling their `process()` method.

        Supports recursive execution of sub-graphs with depth tracking.

        Args:
            graph: The EntityGraph to execute
            context: Description of the execution context for logging

        Raises:
            RuntimeError: If maximum nesting depth is exceeded or graph has cycles
        """
        if self._current_depth >= self.max_depth:
            raise RuntimeError(
                f"Maximum sub-graph nesting depth ({self.max_depth}) exceeded. "
                f"Current context: {context}"
            )

        if not graph.nodes:
            logger.info(
                f"Graph is empty at depth {self._current_depth} ({context}). Nothing to execute."
            )
            return

        logger.info(f"Starting graph execution at depth {self._current_depth} ({context})...")

        # Set the active engine context
        engine_token = current_execution_engine_context.set(self)
        graph_token = current_graph_context.set(graph)

        try:
            execution_order = self._topological_sort(graph)
            logger.info(f"Execution order at {context}: {[node.name for node in execution_order]}")

            for node in execution_order:
                logger.debug(
                    f"Processing node: {node.name} (ID: {node.id}) at depth {self._current_depth}"
                )

                # Check if this is a SubGraphNode and handle recursion
                if self._is_subgraph_node(node):
                    self._execute_subgraph_node(node)
                else:
                    node.process()
        # Ensure this catch is broad enough or specific to critical execution errors
        # For now, catching RuntimeError from _topological_sort or other unexpected issues
        # Re-raising to allow higher-level handling if necessary
        except RuntimeError as e:
            logger.error(f"Failed to execute graph at {context}: {e}")
            raise
        finally:
            current_graph_context.reset(graph_token)
            current_execution_engine_context.reset(engine_token)

        logger.info(f"Graph execution complete at depth {self._current_depth} ({context}).")

    def _is_subgraph_node(self, node: EntityNode) -> bool:
        """Check if a node is a SubGraphNode without importing to avoid circular imports."""
        return node.__class__.__name__ == "SubGraphNode"

    def _execute_subgraph_node(self, subgraph_node: EntityNode) -> None:
        """Execute a sub-graph node with proper context management.

        This method manages the execution depth and delegates to the SubGraphNode's
        process method, which will call back into this engine for the internal graph.
        """
        self._current_depth += 1
        try:
            logger.debug(
                f"Entering sub-graph '{subgraph_node.name}' at depth {self._current_depth}"
            )
            subgraph_node.process()
            logger.debug(
                f"Exiting sub-graph '{subgraph_node.name}' at depth {self._current_depth}"
            )
        except Exception as e:
            logger.error(
                f"Error in sub-graph '{subgraph_node.name}' at depth {self._current_depth}: {e}"
            )
            raise
        finally:
            self._current_depth -= 1
