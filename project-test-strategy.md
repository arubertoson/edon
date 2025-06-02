# Edon Project Testing Strategy

## Guiding Principles

Our testing strategy prioritizes confidence in the overall system behavior and the correct interaction of its components. We aim for a pragmatic approach that maximizes value and bug detection efficiency. The core idea is to focus on how parts of the system work together, rather than testing them in complete isolation, unless absolutely necessary.

## Primary Approach: Integration Testing

**Why:** Integration tests are our primary tool because they validate the interactions between different components of the Edon system (e.g., `EntityGraph`, `EntityNode`, `SubGraphNode`, `ExecutionEngine`). This provides a higher level of confidence that the system functions correctly as a whole for its intended use cases. They naturally cover the "happy paths" and ensure that core workflows behave as expected from an end-to-end perspective (within the backend logic).

**What we hope to accomplish:**
*   Verify that fundamental workflows, such as graph creation, node processing, sub-graph execution, and data flow, are correct.
*   Ensure that changes in one component do not break its interaction with others.
*   Provide a clear, executable specification of how the system is intended to be used.

**Techniques:**
*   Develop test scenarios that mirror common or critical user workflows.
*   Utilize fixtures for setting up graph structures and node configurations.
*   Assert expected outcomes, such_as final values in output sockets or the state of the graph after execution.

## Secondary Approach: Fuzzing / Property-Based Testing for Dynamic Operations

**Why:** For highly dynamic and combinatorial operations, such as:
    *   Adding and removing nodes.
    *   Creating and deleting links between sockets.
    *   Complex sequences of graph modifications.
manually writing individual integration tests for every conceivable scenario is impractical and prone to missing edge cases. Fuzzing or property-based testing allows us to explore a much larger state space automatically.

**What we hope to accomplish:**
*   Uncover bugs related to unexpected sequences of operations or rare graph configurations.
*   Ensure the system remains robust and maintains its invariants even under stress or unusual inputs.
*   Reduce the burden of manually creating and maintaining a vast suite of specific, scenario-based tests for these dynamic aspects.

**Techniques:**
*   **Deterministic Fuzzing:** Generate sequences of valid graph operations (e.g., `add_node`, `link_sockets`, `remove_node`, `unlink_sockets`) in a deterministic manner. This allows for reproducible test failures.
*   **Property-Based Testing:** Define properties or invariants that should always hold true for the graph (e.g., "a linked target socket should always have a corresponding source socket," "no cycles should be formable if cycle detection is active"). The testing framework then generates inputs/sequences of operations to try and falsify these properties.
*   **Strong In-Code Assertions:** This approach heavily relies on the presence of robust assertions and checks within the core `EntityGraph` and `EntityNode` logic. The fuzzer's role is to drive the system into various states; the internal assertions are responsible for detecting if any of those states are invalid.

## Unit Tests: Use Sparingly

**Why:** While unit tests can be valuable for testing algorithms in isolation, an over-reliance on them can lead to:
    *   Brittle tests that break with minor refactoring.
    *   A false sense of security if the units work in isolation but fail when integrated.
    *   Significant time spent writing and maintaining tests that provide less overall system confidence compared to integration tests.

**When to use:**
*   **Extremely Complex, Isolated Algorithms:** If a specific function or method contains highly intricate logic that is difficult to exercise thoroughly through integration tests (e.g., a complex mathematical transformation, a very specific parsing routine).
*   **Critical Utility Functions:** For low-level utility functions that are widely used and whose correctness is paramount, and where their behavior can be clearly defined and tested without extensive setup.

**What we hope to accomplish by limiting unit tests:**
*   Focus testing effort on areas that provide the most value in terms of system correctness.
*   Avoid testing implementation details, favoring tests that verify observable behavior and interactions.

## Overall Goal

By combining comprehensive integration tests for core workflows with fuzzing/property-based testing for dynamic interactions, and using unit tests judiciously, we aim to build a robust and reliable system. This strategy is designed to efficiently catch a wide range of bugs, from simple functional errors to complex state-dependent issues, while keeping the test suite manageable and focused on real-world system behavior.
