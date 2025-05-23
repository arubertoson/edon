# Edon Python Style and Quality Guide

## 1. Purpose

This guide ensures all Python code in the Edon project is readable, maintainable, and consistent, following modern Python best practices and the project's architectural philosophy. Adherence to these guidelines is mandatory for all contributions.

## 2. General Principles

-   **Readability ("Read Like a Book")**: Structure code modules, classes, and functions to tell a clear story. The flow of logic should be easy to follow.
-   **Coherent Blocks ("Paragraphs")**: Group related statements into logical blocks, often separated by blank lines. Locality is important!
-   **Top-Down Readability**: Higher-level orchestrating logic should appear before detailed implementation specifics.
-   **Clear and Descriptive Naming**: Use precise names that clearly convey purpose. Follow [Google Python Style Guide naming conventions](https://google.github.io/styleguide/pyguide.html#316-naming):
    -   `module_name`
    -   `ClassName`
    -   `method_name`
    -   `function_name`
    -   `CONSTANT_NAME`
    -   `_internal_variable_or_method`
    -   `__private_attribute_or_method` (use with caution)

## 3. Language and Libraries

-   **Python Version**: Code must be compatible with **Python 3.13**. Utilize features from this version where appropriate.
-   **Qt Bindings**: Use **PySide6** for all Qt-related development.
-   **Imports**: Always use **absolute imports**. Example: `from edon_ui.widgets import MyWidget` instead of `from .widgets import MyWidget`.
-   **Formatting**: No automated code formatters are enforced, but consistency with the existing codebase style is expected. *Never make purely stylistic changes to existing, unrelated code in a PR focused on features or bug fixes.*

## 4. Type Hinting

Comprehensive type hinting is mandatory to improve code clarity and enable static analysis.

-   **Completeness**: All function/method parameters and return values, class attributes, and significant variables MUST have type hints.
-   **Built-in Generics (PEP 585)**: Prefer built-in generic types for collections (e.g., `list[str]`, `dict[str, int]`) as per Python 3.9+.
-   **Abstract Collection Types (`collections.abc`)**: For abstract collection types (interfaces) or when defining generic functions/classes, use the abstract base classes (ABCs) from the `collections.abc` module (e.g., `from collections.abc import Iterable, Sequence, Mapping, Set, Callable`). Annotate as `Iterable[int]`, `Mapping[str, float]`. This is preferred over `typing` module equivalents for forward compatibility.
-   **Union Types (PEP 604)**: Use the `X | Y` syntax for union types (e.g., `str | None` instead of `Optional[str]`), as per Python 3.10+.
-   **Callables**: Annotate callables using `from collections.abc import Callable` (e.g., `Callable[[int], str]`).
-   **Type Aliases**:
    -   Use the `type` statement for creating simple type aliases in Python 3.12+ (e.g., `type UserID = int`).
    -   For creating distinct types that are not interchangeable with their base type (for stronger type safety), use `NewType` from the `typing` module (e.g., `from typing import NewType; UserID = NewType('UserID', int)`).
-   **Forward References**: When a type hint refers to a class name that has not yet been defined, specify the type hint as a string literal (e.g., `def set_parent(self, parent: "MyClass | None") -> None:`).
-   **`TYPE_CHECKING`**: To avoid circular imports or unnecessary runtime imports solely for type annotations, use `from typing import TYPE_CHECKING`. Import modules needed only for type hints within an `if TYPE_CHECKING:` block.
-   **Protocols (`typing.Protocol`)**: Use `from typing import Protocol` to define structural interfaces (i.e., specifying what methods and attributes a class must have, without requiring inheritance). This is useful for static duck typing and preferred over ABCs when you only need to specify a contract without enforcing inheritance.

## 5. Docstrings

All public modules, functions, classes, and methods MUST have a docstring.

-   **Module Docstrings**: Each module MUST have a module docstring describing its purpose and contents.
-   **Structure**:
    -   A concise summary line (one line only), followed by a blank line, then a more detailed explanation if needed.
    -   The summary line should not merely repeat the function/method signature.
    -   DO NOT include Args/Returns/Raises or other direct attributes. Focus on why the function exists and what it tries to accomplish.
-   **Function/Method Docstrings**:
    -   **Summary**: Brief overview of behavior.
    -   do *not* repeat type information within the docstring.
    -   **Conciseness:**: For simple functions or methods (e.g., getters) where the return value and its type are obvious from the signature and the summary line, docstring may be omitted if it would only reiterate this information.
-   **Class Docstrings**:
    -   **Summary**: The summary should provide a clear, high-level understanding of the class's role and responsibilities. Avoid including extensive lists of public attributes or methods if these are self-documenting through their own names and docstrings. Detailed examples of usage are often better placed in module-level docstrings or separate usage documentation unless they are very concise and critical to understanding the class's primary purpose.
    -   If the class is intended to be subclassed and has an additional interface for subclasses, this interface should be listed separately.
-   **`__init__` Methods should not have docstring**
- Where docstring is NOT necessary:
    -   @property or other short functions where the purpose is clear from the name *and the getter docstring guideline above is met*.
    -   private methods/functions do not require docstrings, focus on inline comments if elaboration is necessary. *However, if a private method is complex or its purpose is not immediately obvious from its name and context, a docstring is encouraged.*
    -   Try to reduce direct references to classes and functions in docstrings, only include them where necessary.

## 6. Comments (Inline)

While docstrings explain *what* a public interface does and *how* to use it, inline comments are crucial for explaining the *why* behind the implementation.

-   **Intent and Rationale**: Use comments to clarify the reasoning behind non-obvious design choices, complex algorithms, or specific implementations.
-   **Contextual Background**: Provide comments that offer background or context not immediately apparent from the code.
-   **High-Level Overviews**: For intricate functions or logical blocks, a brief comment at the beginning can summarize the strategy.
-   **Avoid Redundancy**: Do not comment on what is already clear from well-written code (e.g., avoid `x = x + 1  # Increment x`).
-   **Maintain Accuracy**: Ensure comments are kept meticulously up-to-date. Outdated comments are worse than no comments.

## 7. Dependency Management

-   Dependencies are managed via `pyproject.toml` and `uv` (as indicated by `uv.lock`).
-   Keep dependencies updated and justify additions.

## 8. Logging

-   `loguru` is the standard logging library for Edon.
-   Use appropriate log levels consistently to aid in debugging and monitoring. The standard levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) plus TRACE are available.
-   Ensure sensitive information (passwords, private keys, personal user data) is NEVER logged, especially in INFO level and above.

### Logging Level Guidance:

-   **`TRACE`**: Extremely fine-grained information, more detailed than DEBUG.
    -   **Use when**: You need to follow the execution path within a complex function step-by-step, log variable values at many intermediate points, or understand the lowest-level details of an algorithm or interaction.
    -   **Example**: `logger.trace("Loop iteration {i}, current value: {val}")`, `logger.trace("Calling internal helper _process_item with: {item_details}")`.
    -   **Note**: TRACE logs are usually disabled in production and even development unless actively debugging a very specific, intricate part of the code. They can be very verbose.

-   **`DEBUG`**: Detailed information, typically of interest only when diagnosing problems.
    -   **Use when**: Logging entry and exit points of significant functions/methods, important state changes relevant for debugging, successful completion of internal steps, or detailed context for a specific operation.
    -   **Example**: `logger.debug("User {user_id} initiated node creation.")`, `logger.debug("Graph loaded successfully from {file_path}.")`, `logger.debug("Socket link validation passed for {socket_a} and {socket_b}.")`.
    -   **Note**: DEBUG logs are often enabled during development but usually disabled in production unless a specific issue is being investigated.

-   **`INFO`**: Coarse-grained information that highlights the progress or state of the application at a high level. Confirmation that things are working as expected.
    -   **Use when**: Logging major lifecycle events (application start/stop, service initialization), significant user-driven actions (e.g., file open/save, project creation), successful completion of major operations, or important milestones.
    -   **Example**: `logger.info("Edon application started.")`, `logger.info("Project '{project_name}' saved successfully.")`, `logger.info("New node '{node_name}' ({node_type}) created by user.")`.
    -   **Note**: INFO logs are often enabled in production to provide an overview of the application's activity.

-   **`WARNING`**: Indicates an unexpected or potentially harmful situation occurred, but the application can still continue. It's not a critical error, but it's something that should be investigated.
    -   **Use when**: Deprecated feature usage, minor errors that have fallbacks, recoverable issues, or unusual conditions that might lead to problems later.
    -   **Example**: `logger.warning("Configuration file not found at {path}, using default settings.")`, `logger.warning("Node type '{node_type}' is deprecated and will be removed in a future version.")`.

-   **`ERROR`**: A serious problem occurred, and the application was unable to perform a specific operation or function as intended. However, the application as a whole might still continue to run (perhaps in a degraded state).
    -   **Use when**: Failed operations that impact functionality (e.g., failed to save a file due to permissions), exceptions that are caught but indicate a significant failure in a subsystem, inability to connect to a required service.
    -   **Example**: `logger.error("Failed to save project to {path}: {exception_details}")`, `logger.error("Could not execute graph: {error_message}")`.

-   **`CRITICAL`**: A very severe error occurred, indicating that the application itself may be unable to continue running or is in an unstable state. This often precedes application termination.
    -   **Use when**: Unrecoverable errors, corruption of critical data, situations where the application cannot fulfill its primary purpose.
    -   **Example**: `logger.critical("Application database is corrupted and cannot be loaded. Shutting down.")`, `logger.critical("Essential configuration missing, cannot start application.")`.
