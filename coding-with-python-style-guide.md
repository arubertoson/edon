# Edon Python Style and Quality Guide

## Version 1.0-draft

### Purpose

This guide defines the standards for all Python code within the Edon project. Our primary objective is to build robust, efficient, and maintainable software by instilling a culture of disciplined engineering. Adherence to these guidelines is mandatory for all contributions.

### Core Principles

The Edon Python Style is not just a set of coding standards; it's a practical approach to software development deeply inspired by the "Tiger Style" philosophy. By prioritizing these core principles, we create code that is reliable, efficient, and enjoyable to work with.

*   **Safety**: Writing code that works correctly in all situations and reduces the risk of errors. Safety is the foundation of reliability and trustworthiness.
*   **Performance**: Using resources efficiently to deliver fast, responsive software. Prioritizing performance early ensures systems meet or exceed user expectations without unnecessary overhead.
*   **Developer Experience**: Creating a codebase that is readable, easy to understand, and enjoyable to work with. A good developer experience improves code quality, encourages collaboration, and reduces errors, leading to a healthier codebase that stands the test of time.
*   **Zero Technical Debt**: A foundational commitment. We take the time to design and implement solutions correctly from the start, address potential issues proactively, and build robust solutions that avoid accruing debt. True progress is solid, reliable, and built to last.

### 1. General Principles

*   **Readability ("Read Like a Book")**: Structure code modules, classes, and functions to tell a clear story. The flow of logic should be easy to follow.
*   **Coherent Blocks ("Paragraphs")**: Group related statements into logical blocks, often separated by blank lines. Locality is important!
*   **Top-Down Readability**: Higher-level orchestrating logic should appear before detailed implementation specifics.
*   **Clear and Descriptive Naming**: Use precise names that clearly convey purpose. Follow [Google Python Style Guide naming conventions](https://google.github.io/styleguide/pyguide.html#316-naming):
    *   `module_name`
    *   `ClassName`
    *   `method_name`
    *   `function_name`
    *   `CONSTANT_NAME`
    *   `_internal_variable_or_method`
    *   `__private_attribute_or_method` (use with caution, avoid where possible)
*   **Consistency**: Maintain consistent patterns, idioms, and style across the codebase. Consistency reduces cognitive load and makes code easier to navigate and understand.

### 2. Design Goals

Our design goals focus on building software that is safe, fast, and easy to maintain.

#### 2.1. Safety

Safety in coding relies on clear, structured practices that prevent errors and strengthen the codebase. It's about writing code that works in all situations and catches problems early.

##### Control and Limits

Predictable control flow and bounded system resources are essential for safe execution.

*   **Simple and Explicit Control Flow**: Favor straightforward control structures over complex logic. Simple control flow makes code easier to understand and reduces the risk of bugs. Avoid overly complex `if/elif/else` chains or deep nesting; instead, extract helper functions or use guard clauses.
*   **Set Fixed Limits**: For iterative processes or data structures where unbounded growth could lead to issues, set explicit upper bounds. This prevents infinite loops and uncontrolled resource use, following the **fail-fast principle**. For example, when processing a known number of items, ensure loops iterate exactly that many times.
*   **Limit Function Length**: Keep functions concise, ideally under 70 lines. Shorter functions are easier to understand, test, and debug. They promote single responsibility, where each function does one thing well, leading to a more modular and maintainable codebase.
*   **Centralize Control Flow**: Keep `if` or `match` statements in the main parent function, and move non-branching logic to helper functions. Let the parent function manage state (or delegate state management clearly), using helpers to calculate changes without directly applying them. Keep "leaf" functions pure and focused on specific computations. This divides responsibility: one function controls flow, others handle specific logic.

##### Memory and Types

Clear and consistent handling of data and types is key to writing safe, portable code.

*   **Use Explicitly Sized Types (via Type Hinting)**: While Python's types are dynamic, use comprehensive type hints to convey explicit size/range intent where relevant (e.g., if a `bytes` object *must* be 16 bytes long, document it or use `NewType` for a specific ID type). This keeps behavior consistent and avoids size-related errors, improving reliability.
*   **Minimize Variable Scope**: Declare variables in the smallest possible scope. Limiting scope reduces the risk of unintended interactions and misuse. It also makes the code more readable and easier to maintain by keeping variables within their relevant context.
*   **Avoid Unnecessary Runtime Allocations**: Python is garbage collected, but the spirit of "static memory allocation" translates to *avoiding excessive or unpredictable memory growth*. This means:
    *   Prefer generators for large sequences instead of building full lists in memory.
    *   Reuse objects where appropriate instead of constantly creating new ones in loops.
    *   Be mindful of object sizes and their impact on memory footprint, especially in long-running processes.

##### Error Handling: The Corner Stone of Safety

Correct error handling keeps the system robust and reliable in all conditions. This is where "negative space assertions" shine: detecting and failing on programmer errors *before* they can propagate.

*   **Use Assertions (for Programmer Errors)**: Use Python's `assert` statement to verify that conditions hold true at specific points in the code. Assertions are internal checks that increase robustness and simplify debugging by failing *immediately* on conditions that should *never* happen in correct code (programmer errors).
    *   **Assert Function Arguments and Return Values**: Check that functions receive and return expected values and types.
    *   **Validate Invariants**: Keep critical conditions stable by asserting invariants during execution.
    *   **Use Pair Assertions**: Check critical data at multiple points to catch inconsistencies early.
    *   **Fail Fast on Programmer Errors**: Detect unexpected conditions immediately, stopping faulty code from continuing. If an `assert` fails, it indicates a bug in *our code*, not an external runtime error.
    *   **Distinction**: `assert` is for *programmer errors* (things that indicate a bug in the code itself, like "this list should never be empty here"). Use exceptions (`raise ValueError`, `raise TypeError`, etc.) for *runtime errors* (things that can happen due to external factors or invalid user input, like "file not found" or "invalid user ID").
*   **Handle All Runtime Errors**: Check and handle every expected runtime error. Ignoring errors can lead to undefined behavior, security issues, or crashes. Use specific `try...except` blocks and log appropriately. Write thorough tests for error-handling code to make sure your application works correctly in all cases.
*   **Avoid Implicit Defaults**: Explicitly specify options when calling library functions or constructing objects instead of relying solely on defaults. Implicit defaults can change between library versions or across environments, causing inconsistent behavior. Being explicit improves code clarity and stability.

#### 2.2. Performance

Performance is about using resources efficiently to deliver fast, responsive software. Prioritizing performance early helps design systems that meet or exceed user expectations.

##### Design for Performance

Early design decisions have a significant impact on performance. Thoughtful planning helps avoid bottlenecks later.

*   **Design for Performance Early**: Consider performance during the initial design phase. Early architectural decisions have a big impact on overall performance, and planning ahead ensures you can avoid bottlenecks and improve resource efficiency. Don't wait until the end to optimize.
*   **Napkin Math**: Use quick, back-of-the-envelope calculations to estimate system performance and resource costs. For example, estimate how long it takes to process a certain amount of data, or what the expected memory footprint will be for a new data structure. This helps set practical expectations early and identify potential bottlenecks before they occur. Aim to be within an order of magnitude of the correct answer.
*   **Batch Operations**: Amortize expensive operations by processing multiple items together. Batching reduces overhead per item, increases throughput, and is especially useful for I/O-bound operations (e.g., database writes, network calls, file operations).

##### Efficient Resource Use

Focus on optimizing the slowest resources, typically in this order:

1.  **Network**: Optimize data transfer, reduce latency, and minimize round trips.
2.  **Disk**: Improve I/O operations and manage storage efficiently (e.g., correct file buffering, avoiding redundant writes).
3.  **Memory**: Use memory effectively to prevent leaks and overuse. This includes using efficient data structures, avoiding unnecessary copies of large objects, and leveraging generators.
4.  **CPU**: Increase computational efficiency and reduce processing time. This involves choosing efficient algorithms, using built-in functions where possible, and understanding the performance characteristics of standard library components.

##### Predictability

Writing predictable code improves performance by reducing overhead related to dynamic behavior.

*   **Ensure Predictability**: Write code with predictable execution paths and consistent performance characteristics. For Python, this means:
    *   Choosing data structures whose performance characteristics match usage patterns (e.g., `dict` for fast lookups, `list` for ordered sequences).
    *   Avoiding patterns that lead to highly variable execution times (e.g., excessive recursive calls without memoization, repeated linear scans of large data).
    *   Leveraging Python's built-in functions and C-implemented types for common operations, as they are highly optimized.
*   **Reduce Interpreter/Library Dependence**: Don't rely solely on interpreter-specific micro-optimizations. Write clear, efficient, and idiomatic Python code. Be explicit in performance-critical sections to ensure consistent results across different Python versions or environments.

#### 2.3. Developer Experience

Improving the developer experience creates a more maintainable and collaborative codebase.

##### Name Things

Get the nouns and verbs right. Great names capture what something is or does and create a clear, intuitive model. They show you understand the domain. Take time to find good names, where nouns and verbs fit together, making the whole greater than the sum of its parts.

*   **Clear and Consistent Naming**: Use descriptive and meaningful names for variables, functions, classes, and files. Good naming improves code readability and helps others understand each component's purpose. Stick to a consistent style, like `snake_case` for functions/variables and `CamelCase` for classes, throughout the codebase.
*   **Avoid Abbreviations**: Use full words in names unless the abbreviation is widely accepted and clear (e.g., `ID`, `URL`, `IO`). Abbreviations can be confusing and make it harder for others, especially new contributors, to understand the code.
*   **Include Units or Qualifiers in Names**: Append units or qualifiers to variable names when applicable, placing them in descending order of significance (e.g., `latency_ms_max` instead of `max_latency_ms`). This clears up meaning, avoids confusion, and ensures related variables, like `latency_ms_min`, line up logically and group together.
*   **Document the 'Why'**: Use comments or docstrings to explain *why* decisions were made, not just *what* the code does. Knowing the intent helps others maintain and extend the code properly. Give context for complex algorithms, unusual approaches, or key constraints.
*   **Use Proper Comment Style**: Write comments and docstrings as complete sentences with correct punctuation and grammar. Clear, professional comments improve readability and show attention to detail. They help create a cleaner, more maintainable codebase.

##### Organize Things

Organizing code well makes it easy to navigate, maintain, and extend. A logical structure reduces cognitive load, letting developers focus on solving problems instead of figuring out the code. Group related elements, and simplify interfaces to keep the codebase clean, scalable, and manageable as complexity grows.

*   **Organize Code Logically**: Structure your code logically. Group related functions, classes, and modules together. Order code naturally, placing high-level abstractions before low-level details (top-down). Logical organization makes code easier to navigate and understand.
*   **Simplify Function Signatures**: Keep function interfaces simple. Limit parameters, and prefer returning simple types or well-defined data structures. Simple interfaces reduce cognitive load, making functions easier to understand and use correctly. Avoid functions with too many arguments.
*   **Manage Resources Cleanly**: While Python manages memory, ensure resources like file handles, network connections, or database cursors are managed cleanly using `with` statements (context managers) or explicit close calls. Group resource acquisition and release with clear newlines to make leaks easier to identify.
*   **Minimize Variable Scope**: Declare variables close to their usage and within the smallest necessary scope. This reduces the risk of misuse and makes code easier to read and maintain.

##### Ensure Consistency

Maintaining consistency in your code helps reduce errors and creates a stable foundation for the rest of the system.

*   **Avoid Duplicates and Aliases**: Prevent inconsistencies by avoiding duplicated data or unnecessary aliases. When two variables represent the same logical data, there's a higher chance they fall out of sync. Use references (which is Python's default for objects) to maintain a single source of truth. If a copy is truly needed, make it explicit.
*   **Pass Large Objects Thoughtfully**: In Python, objects are passed by reference by default, so large objects are not copied unnecessarily. The consistency here is about *avoiding unintended copies* when manipulating collections or complex objects, e.g., using `list.copy()` or `dict.copy()` when a mutable copy is truly desired, or `copy.deepcopy()` for nested structures, and understanding the implications.
*   **Minimize Dimensionality**: Keep function signatures and return types simple to reduce the number of cases a developer has to handle. For example, prefer `None` over `bool` when merely signaling success/failure of a side-effect, and `bool` over an `int` flag, when it suits the function's purpose. Reduce the number of distinct return types.
*   **Handle Buffer/Collection Management Cleanly**: When working with collections (lists, dicts, bytes buffers), ensure creation, modification, and (if applicable) cleanup happens in the same logical block or through clear patterns. This minimizes opportunities for errors.

##### Avoid Off-by-One Errors

Off-by-one errors often result from casual interactions between an index, a count, or a size. Treat these as distinct types, and apply clear rules when converting between them.

*   **Indexes, Counts, and Sizes**: Indexes are 0-based, counts are 1-based (number of items), and sizes represent total memory usage or capacity. When converting between them, add or multiply accordingly. Use meaningful names with units or qualifiers (e.g., `item_count`, `buffer_size_bytes`, `start_index`, `end_exclusive_index`) to avoid confusion.
*   **Handle Division Intentionally**: When dividing, make your intent clear by specifying how rounding should be handled in edge cases. Use functions or operators designed for exact division (`/` for float, `//` for floor division) or custom rounding logic. This avoids ambiguity and ensures the result behaves as expected.

##### Code Consistency and Tooling

Consistency in code style and tools improves readability, reduces mental load, and makes working together easier.

*   **Maintain Consistent Indentation**: Use a uniform indentation style across the codebase. **4 spaces** for indentation provides better visual clarity, especially in complex structures. Tabs are forbidden.
*   **Limit Line Lengths**: Keep lines within a reasonable length (e.g., **100-120 characters**) to ensure readability. This prevents horizontal scrolling and helps maintain an accessible code layout.
*   **Use Clear Code Blocks**: Structure code clearly by separating logical blocks (e.g., control structures, loops, function definitions) with blank lines to make it easy to follow. Avoid placing multiple statements on a single line, even if allowed. Consistent block structures prevent subtle logic errors and make code easier to maintain.
*   **Minimize External Dependencies**: Reducing external dependencies simplifies the build process, improves security management, and speeds up installation. Fewer dependencies lower the risk of supply chain attacks, minimize performance issues, and reduce maintenance burden. Justify every new dependency.
*   **Standardize Tooling**: Using a small, standardized set of tools simplifies the development environment and reduces accidental complexity. Choose cross-platform tools where possible to avoid platform-specific issues and improve portability across systems.

### 3. Language and Libraries

*   **Python Version**: Code must be compatible with **Python 3.13**. Utilize features from this version where appropriate.
*   **Qt Bindings**: Use **PySide6** for all Qt-related development.
*   **Imports**: Always use **absolute imports**. Example: `from edon_ui.widgets import MyWidget` instead of `from .widgets import MyWidget`. Imports should be grouped and ordered as follows (PEP 8):
    1.  Standard library imports.
    2.  Third-party library imports.
    3.  Local application/library specific imports.
    Separate each group with a blank line.
*   **Formatting**: While no single automated formatter is strictly enforced beyond linters, consistency with the existing codebase style is expected. **Never make purely stylistic changes to existing, unrelated code in a Pull Request focused on features or bug fixes.** Such changes should be in dedicated refactoring PRs.

### 4. Type Hinting

Comprehensive type hinting is mandatory to improve code clarity, enable static analysis, and facilitate robust development.

*   **Completeness**: All function/method parameters and return values, class attributes, and significant variables MUST have type hints.
*   **Built-in Generics (PEP 585)**: Prefer built-in generic types for collections (e.g., `list[str]`, `dict[str, int]`) as per Python 3.9+.
*   **Abstract Collection Types (`collections.abc`)**: For abstract collection types (interfaces) or when defining generic functions/classes, use the abstract base classes (ABCs) from the `collections.abc` module (e.g., `from collections.abc import Iterable, Sequence, Mapping, Set, Callable`). Annotate as `Iterable[int]`, `Mapping[str, float]`. This is preferred over `typing` module equivalents for forward compatibility and clarity.
*   **Union Types (PEP 604)**: Use the `X | Y` syntax for union types (e.g., `str | None` instead of `Optional[str]`), as per Python 3.10+.
*   **Callables**: Annotate callables using `from collections.abc import Callable` (e.g., `Callable[[int, str], bool]`).
*   **Type Aliases**:
    *   Use the `type` statement for creating simple type aliases in Python 3.12+ (e.g., `type UserID = int`).
    *   For creating distinct types that are not interchangeable with their base type (for stronger type safety and semantic clarity), use `NewType` from the `typing` module (e.g., `from typing import NewType; UserID = NewType('UserID', int)`). This helps enforce the "explicitly sized types" and "off-by-one errors" principles for conceptual types.
*   **Forward References**: When a type hint refers to a class name that has not yet been defined in the current file, specify the type hint as a string literal (e.g., `def set_parent(self, parent: "MyClass | None") -> None:`).
*   **`TYPE_CHECKING`**: To avoid circular imports or unnecessary runtime imports solely for type annotations, use `from typing import TYPE_CHECKING`. Import modules needed only for type hints within an `if TYPE_CHECKING:` block.
*   **Protocols (`typing.Protocol`)**: Use `from typing import Protocol` to define structural interfaces (i.e., specifying what methods and attributes a class must have, without requiring inheritance). This is useful for static duck typing and preferred over ABCs when you only need to specify a contract without enforcing inheritance.

### 5. Dependency Management

*   Dependencies are managed via `pyproject.toml` and `uv` (as indicated by `uv.lock`).
*   Keep dependencies updated and justify all additions to the `pyproject.toml`. Minimize new dependencies to reduce complexity and attack surface.

### 6. Logging

`loguru` is the standard logging library for Edon. Use appropriate log levels consistently to aid in debugging and monitoring. Ensure sensitive information (passwords, private keys, personal user data) is NEVER logged, especially in INFO level and above.

#### Logging Level Guidance:

*   **`TRACE`**: Extremely fine-grained information, more detailed than DEBUG.
    *   **Use when**: You need to follow the execution path within a complex function step-by-step, log variable values at many intermediate points, or understand the lowest-level details of an algorithm or interaction.
    *   **Example**: `logger.trace("Loop iteration {i}, current value: {val}")`, `logger.trace("Calling internal helper _process_item with: {item_details}")`.
    *   **Note**: TRACE logs are usually disabled in production and even development unless actively debugging a very specific, intricate part of the code. They can be extremely verbose.

*   **`DEBUG`**: Detailed information, typically of interest only when diagnosing problems.
    *   **Use when**: Logging entry and exit points of significant functions/methods, important state changes relevant for debugging, successful completion of internal steps, or detailed context for a specific operation.
    *   **Example**: `logger.debug("User {user_id} initiated node creation.")`, `logger.debug("Graph loaded successfully from {file_path}.")`, `logger.debug("Socket link validation passed for {socket_a} and {socket_b}.")`.
    *   **Note**: DEBUG logs are often enabled during development but usually disabled in production unless a specific issue is being investigated.

*   **`INFO`**: Coarse-grained information that highlights the progress or state of the application at a high level. Confirmation that things are working as expected.
    *   **Use when**: Logging major lifecycle events (application start/stop, service initialization), significant user-driven actions (e.g., file open/save, project creation), successful completion of major operations, or important milestones.
    *   **Example**: `logger.info("Edon application started.")`, `logger.info("Project '{project_name}' saved successfully.")`, `logger.info("New node '{node_name}' ({node_type}) created by user.")`.
    *   **Note**: INFO logs are often enabled in production to provide an overview of the application's activity.

*   **`WARNING`**: Indicates an unexpected or potentially harmful situation occurred, but the application can still continue. It's not a critical error, but it's something that should be investigated.
    *   **Use when**: Deprecated feature usage, minor errors that have fallbacks, recoverable issues, or unusual conditions that might lead to problems later.
    *   **Example**: `logger.warning("Configuration file not found at {path}, using default settings.")`, `logger.warning("Node type '{node_type}' is deprecated and will be removed in a future version.")`.

*   **`ERROR`**: A serious problem occurred, and the application was unable to perform a specific operation or function as intended. However, the application as a whole might still continue to run (perhaps in a degraded state).
    *   **Use when**: Failed operations that impact functionality (e.g., failed to save a file due to permissions), exceptions that are caught but indicate a significant failure in a subsystem, inability to connect to a required service.
    *   **Example**: `logger.error("Failed to save project to {path}: {exception_details}")`, `logger.error("Could not execute graph: {error_message}")`.

*   **`CRITICAL`**: A very severe error occurred, indicating that the application itself may be unable to continue running or is in an unstable state. This often precedes application termination.
    *   **Use when**: Unrecoverable errors, corruption of critical data, situations where the application cannot fulfill its primary purpose.
    *   **Example**: `logger.critical("Application database is corrupted and cannot be loaded. Shutting down.")`, `logger.critical("Essential configuration missing, cannot start application.")`.

### Addendum: Zero Technical Debt

A zero technical debt policy is key to maintaining a healthy codebase and ensuring long-term productivity. Addressing potential issues proactively and building robust solutions from the start helps avoid debt that would slow future development.

*   **Do It Right the First Time**: Take the time to design and implement solutions correctly from the start. Rushed features lead to technical debt that requires costly refactoring later. This doesn't mean perfect; it means "fit for purpose, well-designed, and maintainable."
*   **Be Proactive in Problem-Solving**: Anticipate potential issues and fix them before they escalate. Early detection saves time and resources, preventing performance bottlenecks and architectural flaws.
*   **Build Momentum**: Delivering solid, reliable code builds confidence and enables faster development cycles. High-quality work supports innovation and reduces the need for future rewrites.

Avoiding technical debt ensures that progress is true progress—solid, reliable, and built to last.

### Addendum: Performance Estimation (Napkin Math)

You should think about performance early in design. Napkin math is a helpful tool for this.

Napkin math uses simple calculations and rounded numbers to quickly estimate system performance and resource needs.

*   **Quick Insights**: Understand system behavior fast without deep analysis.
*   **Early Decisions**: Find potential bottlenecks early in design.
*   **Sanity Checks**: See if an idea works before you build it.

For example, if you're designing a system to store logs, you can estimate storage costs like this:

1.  **Estimate log volume**:
    Assume 1,000 requests per second (RPS)
    Each log entry is about 1 KB

2.  **Calculate daily log volume**:
    1,000 RPS * 86,400 seconds/day * 1 KB ≈ 86,400,000 KB/day ≈ 86.4 GB/day

3.  **Estimate monthly storage**:
    86.4 GB/day * 30 days ≈ 2,592 GB/month

4.  **Estimate cost (using $0.02 per GB for blob storage)**:
    2,592 GB * $0.02/GB ≈ $51 per month

This gives you a rough idea of monthly storage costs. It helps you check if your logging plan works. The idea is to get within 10x of the right answer.

For more, see Simon Eskildsen's [napkin math project](https://www.google.com/search?q=Simon+Eskildsen%27s+napkin+math+project).

