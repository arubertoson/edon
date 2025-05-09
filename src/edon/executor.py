from collections import deque

from .node import Node  # Assuming Node is in the same package
from .graph import Graph  # For type hinting the graph parameter


class ExecutionEngine:
    """
    Handles the execution of a node graph, including topological sorting
    and node processing.
    """

    def _topological_sort(self, graph: Graph) -> list[Node]:
        """
        Performs a topological sort of the nodes in the graph.
        Returns a list of nodes in execution order.
        Raises RuntimeError if a cycle is detected.
        """
        in_degree: dict[str, int] = {node_id: 0 for node_id in graph.nodes}

        # Calculate in-degrees by looking at established connections
        for u_node_id, u_node in graph.nodes.items():
            for output_socket in u_node.output_sockets.values():
                for connected_input_socket in output_socket.connections:
                    v_node = connected_input_socket.parent_node
                    if v_node and v_node.id in in_degree:  # Check if target node is in graph
                        in_degree[v_node.id] += 1

        # Initialize queue with all nodes having an in-degree of 0
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])

        execution_order: list[Node] = []

        while queue:
            u_node_id = queue.popleft()
            # Ensure the node ID from the queue is actually in the graph before accessing
            if u_node_id not in graph.nodes:
                # This might happen if graph was modified during sort, though unlikely here.
                # Or if in_degree was somehow miscalculated for nodes not in graph.nodes.
                # For robustness, skip or log.
                continue

            u_node = graph.nodes[u_node_id]
            execution_order.append(u_node)

            for output_socket in u_node.output_sockets.values():
                for connected_input_socket in output_socket.connections:
                    v_node = connected_input_socket.parent_node
                    if v_node and v_node.id in in_degree:  # Check if target node is in graph
                        in_degree[v_node.id] -= 1
                        if in_degree[v_node.id] == 0:
                            queue.append(v_node.id)

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

    def execute_graph(self, graph: Graph):
        """
        Executes the provided graph.
        1. Performs a topological sort.
        2. Processes nodes in the determined order.
        """
        if not graph.nodes:
            print("Graph is empty. Nothing to execute.")
            return

        print("Starting graph execution...")
        try:
            execution_order = self._topological_sort(graph)
        except RuntimeError as e:
            print(f"Failed to prepare graph for execution: {e}")
            # Re-raise or handle as appropriate for the application
            raise

        print(f"Execution order: {[node.name for node in execution_order]}")

        for node in execution_order:
            # print(f"Processing node: {node.name} (ID: {node.id})") # Verbose
            node.process()

        print("Graph execution complete.")
