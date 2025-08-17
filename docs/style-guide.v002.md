# Edon Python Style and Quality Guide (Condensed)

## Version 1.0-draft

### Purpose

This guide defines standards for Python code within Edon, aiming for robust, efficient, and maintainable software through disciplined engineering. Adherence is mandatory.

### Core Principles (Inspired by "Tiger Style")

*   **Safety**: Code works correctly and reduces error risk. Foundation of reliability.
*   **Performance**: Efficient resource use for fast, responsive software. Prioritize early.
*   **Developer Experience**: Readable, understandable, enjoyable codebase. Improves quality and collaboration.
*   **Zero Technical Debt**: Design and implement correctly from the start. Proactively address issues for lasting, reliable progress.

### 1. General Principles

*   **Readability ("Read Like a Book")**: Structure code for clear, logical flow.
*   **Coherent Blocks ("Paragraphs")**: Group related statements, use blank lines for separation. Locality matters.
*   **Top-Down Readability**: High-level logic before implementation details.
*   **Clear and Descriptive Naming**: Precise names conveying purpose. Follow [Google Python Style Guide naming conventions](https://google.github.io/styleguide/pyguide.html#316-naming) (`module_name`, `ClassName`, `method_name`, `CONSTANT_NAME`, `_internal_variable_or_method`). Avoid `__private` where possible.
*   **Consistency**: Maintain consistent patterns, idioms, and style throughout.

### 2. Design Goals: Safe, Fast, Maintainable

#### 2.1. Safety: Prevent errors, strengthen codebase.

##### Control and Limits
*   **Simple Control Flow**: Favor straightforward structures. Avoid complex `if/elif/else` or deep nesting; extract helpers or use guard clauses.
*   **Set Fixed Limits**: Define upper bounds for iterations/data structures to prevent infinite loops/resource exhaustion (fail-fast).
*   **Limit Function Length**: Keep functions concise (< 70 lines) for single responsibility.
*   **Centralize Control Flow**: Parent functions manage `if/match` and state; helpers perform non-branching logic/calculations.

##### Memory and Types
*   **Minimize Variable Scope**: Declare variables in the smallest possible scope.
*   **Avoid Unnecessary Runtime Allocations**: Prefer generators, reuse objects, be mindful of object sizes in long-running processes.

##### Error Handling
*   **Use Assertions (Programmer Errors)**: Use `assert` to fail *immediately* on conditions that indicate bugs in *our code*.
    *   Check function arguments/returns, validate invariants, use pair assertions.
    *   Distinguish from exceptions (`raise ValueError`) used for *runtime errors* (external factors, invalid input).
*   **Handle All Runtime Errors**: Check and handle every expected runtime error with specific `try...except` blocks.
*   **Avoid Implicit Defaults**: Explicitly specify options for library calls/object construction.

#### 2.2. Performance: Efficient resource use.

##### Design for Performance
*   **Design Early**: Consider performance in initial design.
*   **Napkin Math**: Use quick estimates for performance/resource costs (see Addendum). Aim for order-of-magnitude accuracy.
*   **Batch Operations**: Amortize costs by processing items together (esp. I/O).

##### Efficient Resource Use (Optimize in this order)
1.  **Network**: Minimize data transfer, latency, round trips.
2.  **Disk**: Improve I/O (buffering, avoid redundant writes).
3.  **Memory**: Efficient data structures, avoid unnecessary large object copies, use generators.
4.  **CPU**: Efficient algorithms, use built-ins.

##### Predictability
*   **Ensure Predictable Code**: Choose data structures matching usage patterns. Avoid highly variable execution times. Leverage optimized built-ins.
*   **Write Clear, Efficient Python**: Don't rely on micro-optimizations. Be explicit in critical sections.

#### 2.3. Developer Experience: Maintainable, collaborative codebase.

##### Naming and Documentation
*   **Clear, Consistent Naming**: Descriptive full-word names (e.g., `latency_ms_max`).
*   **Document the 'Why'**: Comments/docstrings explain intent, complex decisions, constraints.
*   **Proper Comment Style**: Complete sentences, correct grammar.

##### Organization and Simplicity
*   **Organize Code Logically**: Group related elements. High-level before low-level.
*   **Simplify Function Signatures**: Limit parameters; prefer simple or well-defined return types.
*   **Manage Resources Cleanly**: Use `with` statements or explicit `close()` for files, connections, etc.
*   **Minimize Variable Scope**: Declare variables near usage, in smallest scope.
*   **Avoid Duplicates/Aliases**: Maintain a single source of truth for data. Be explicit about copies (`list.copy()`, `copy.deepcopy()`).
*   **Minimize Dimensionality**: Simple function signatures/return types (e.g., `None` for side-effect success, `bool` for flags).
*   **Clean Buffer/Collection Management**: Ensure creation, modification, cleanup are in same logical block or clear patterns.

##### Error Prevention
*   **Indexes, Counts, Sizes**: Treat as distinct. Use clear names (e.g., `item_count`, `buffer_size_bytes`, `start_index`).
*   **Handle Division Intentionally**: Specify rounding/division type (`/` vs `//`).

##### Code Consistency and Tooling
*   **Clear Code Blocks**: Separate logical blocks with blank lines. Avoid multiple statements per line.
*   **Minimize External Dependencies**: Justify every new dependency.
*   **Standardize Tooling**: Use a small, cross-platform toolset.

### 3. Language and Libraries

*   **Python Version**: **Python 3.13**.
*   **Qt Bindings**: **PySide6**.
*   **Imports**: **Absolute imports** (`from edon_ui.widgets import MyWidget`). Grouped and ordered (PEP 8): stdlib, third-party, local. Separate groups with blank lines.
*   **Formatting**: Consistency with existing codebase. **No purely stylistic changes in feature/bugfix PRs**; use dedicated refactoring PRs.

### 4. Type Hinting (Mandatory & Comprehensive)

*   **Completeness**: All function/method parameters, return values, class attributes, significant variables MUST be hinted.
*   **Use `collections.abc` for Abstract Types**: E.g., `from collections.abc import Iterable, Mapping; items: Iterable[int]`.
*   **Use PEP 585 Built-in Generics**: E.g., `list[str]`, `dict[str, int]` (Python 3.9+).
*   **Use PEP 604 Union Syntax**: E.g., `str | None` (Python 3.10+).
*   **Callables**: `from collections.abc import Callable; cb: Callable[[int], str]`.
*   **Type Aliases**:
    *   `type UserID = int` (Python 3.12+ for simple aliases).
    *   `from typing import NewType; UserID = NewType('UserID', int)` (for distinct, non-interchangeable types).
*   **Forward References**: Use string literals: `parent: "MyClass | None"`.
*   **`TYPE_CHECKING`**: For type-only imports: `from typing import TYPE_CHECKING; if TYPE_CHECKING: ...`.
*   **Protocols (`typing.Protocol`)**: For structural interfaces (static duck typing).

### 5. Dependency Management

*   Managed via `pyproject.toml` and `uv` (`uv.lock`).
*   Keep dependencies updated; justify additions. Minimize new dependencies.

### 6. Logging (`loguru`)

Ensure sensitive information (passwords, PII) is NEVER logged, especially at INFO and above.

*   **`TRACE`**: Extremely fine-grained, step-by-step internal details. (Dev debug only)
*   **`DEBUG`**: Detailed diagnostic info, function entry/exit, state changes. (Dev, temp prod debug)
*   **`INFO`**: Coarse-grained progress, major lifecycle events, successful operations. (Prod overview)
*   **`WARNING`**: Unexpected/potential issues, recoverable errors, deprecated features. App continues.
*   **`ERROR`**: Serious problem, operation failed. App might continue degraded.
*   **`CRITICAL`**: Severe error, app may be unstable or unable to continue.

### Addendum: Zero Technical Debt

*   **Do It Right First Time**: Design and implement solutions correctly.
*   **Proactive Problem-Solving**: Fix potential issues early.
*   **Build Momentum**: Solid, reliable code enables faster, innovative development.

### Addendum: Performance Estimation (Napkin Math)

Quickly estimate system performance/resource needs with simple calculations.
*   **Purpose**: Gain quick insights, inform early design, sanity check ideas.
*   **Example (Log Storage)**:
    1.  Estimate: 1k RPS, 1KB/log.
    2.  Daily: 1k * 86400s * 1KB ≈ 86.4 GB/day.
    3.  Monthly: 86.4 GB * 30 ≈ 2.6 TB/month.
    4.  Cost (@ $0.02/GB): 2600 GB * $0.02 ≈ $52/month.
    *Aim for 10x accuracy.* More: [Simon Eskildsen's napkin math](https://www.google.com/search?q=Simon+Eskildsen%27s+napkin+math+project).
