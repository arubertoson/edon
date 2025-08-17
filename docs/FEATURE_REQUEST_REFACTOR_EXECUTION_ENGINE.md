# Feature Request: Refactor Execution Logic and Topological Sort

## 1. Problem Description

Currently, the `ExecutionEngine` class in `src/edon/executor.py` encapsulates two main responsibilities:
1.  Topological sorting of an `EntityGraph` via its private `_topological_sort` method.
2.  Orchestrating the execution of the graph by calling `process()` on nodes in the sorted order via its public `execute_graph` method.

The `_topological_sort` method is a general graph utility and its confinement as a private method within `ExecutionEngine` limits its reusability. Furthermore, the `ExecutionEngine` class itself is stateless, suggesting that its functionality might be better represented by standalone functions.

## 2. Proposed Solution

Refactor the graph execution logic as follows:

1.  **Move Topological Sort:**
    *   Extract the `_topological_sort` logic from `ExecutionEngine`.
    *   Implement it as a standalone function `topological_sort_graph(graph: EntityGraph) -> list[EntityNode]` within the `src/edon/graph.py` module. This places the graph algorithm alongside the `EntityGraph` definition.

2.  **Refactor Graph Execution:**
    *   Transform the `ExecutionEngine.execute_graph` method into a standalone function `execute_entity_graph(graph: EntityGraph) -> None`, also to be placed in `src/edon/graph.py`.
    *   This function will call the new `topological_sort_graph` utility.
    *   With these changes, the `ExecutionEngine` class would no longer be necessary, and the `src/edon/executor.py` file could potentially be removed.

## 3. Benefits

-   **Improved Modularity:** `topological_sort_graph` becomes a reusable utility function for any part of the system that needs to sort an `EntityGraph`.
-   **Simplified Structure:** Replacing the stateless `ExecutionEngine` class with standalone functions can lead to a simpler and more functional design for graph execution.
-   **Better Cohesion:** Consolidating graph algorithms (`topological_sort_graph`) and graph execution logic (`execute_entity_graph`) within the `src/edon/graph.py` module (or a dedicated `src/edon/graph_utils.py` if preferred later) improves the organization of graph-related functionalities.
-   **Reduced Boilerplate:** Eliminates the need for an `ExecutionEngine` class instance if its methods become static or standalone.

## 4. Affected Components & Implementation Notes

-   **`src/edon/executor.py`:**
    *   This file would likely be removed after its functionality is migrated.
-   **`src/edon/graph.py`:**
    *   Will host the new `topological_sort_graph` function.
    *   Will host the new `execute_entity_graph` function.
-   **Call Sites:**
    *   Any code that currently instantiates `ExecutionEngine` and calls `execute_graph` will need to be updated to call the new standalone `execute_entity_graph` function directly.
-   **Action Items:**
    1.  Define `topological_sort_graph` in `src/edon/graph.py` by adapting the current `_topological_sort` logic.
    2.  Define `execute_entity_graph` in `src/edon/graph.py` by adapting the current `ExecutionEngine.execute_graph` logic, ensuring it calls `topological_sort_graph`.
    3.  Update all call sites that previously used `ExecutionEngine`.
    4.  Remove `src/edon/executor.py`.
    5.  Ensure comprehensive testing of graph execution.

## 5. Justification

This refactoring aims to create a more modular, reusable, and functionally oriented design for core graph operations. It enhances the utility of the topological sort algorithm and simplifies the execution mechanism by removing an unnecessary class structure, aligning with principles of good software design. 