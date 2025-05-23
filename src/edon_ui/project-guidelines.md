# Edon Python Code Style & Quality Guide

## 1. Language & Libraries

- Use **Python 3.13** features.
- Use **PySide6** for Qt.
- Always use **absolute imports**.

## 2. Type Hints

- All functions, methods, and class attributes **must** have type hints.
- Use **built-in generics** for concrete collections (e.g., `list[str]`, `dict[str, int]`).
- Use **`collections.abc`** for abstract types (e.g., `Iterable`, `Mapping`, `Callable`).
- Use **`X | Y`** for unions (e.g., `str | None`).
- Use `type` for type aliases (Python 3.12+), and `NewType` for distinct types.
- Use string literals for forward references.
- Use `from typing import TYPE_CHECKING` for type-only imports.
- Use `Protocol` for structural typing.

## 3. Docstrings & Comments

- Every public module, class, function, and method must have a **Google-style docstring**.
- Docstrings should summarize purpose, why it exists, don't list arguments, return values, and exceptions.
- Use **inline comments** to explain *why* (not *what*) for non-obvious logic.
- Keep comments accurate and up-to-date.

## 4. Naming & Structure

- Follow **Google Python Style Guide** naming conventions.
- Organize code to "read like a book": logical flow, clear blocks, and top-down structure.
- sort methods in a class by their purpose, not by their name.
- Use descriptive names for all identifiers.

## 5. Architecture

- **Core logic** (`src/edon/`) is UI-agnostic.
- **UI logic** and Qt dependencies go in `src/edon_ui/`.
- Use `GraphController` to mediate between model and view.

## 6. Dependencies & Logging

- Manage dependencies with `pyproject.toml` and `uv`.
- Use `loguru` for logging; avoid logging sensitive data.

## 7. Testing

- Place all tests in a `tests/` directory.
- Write unit tests for core logic and UI tests as needed.

---

This guide summarizes the most important rules for writing Python code in the Edon project. For details, see the full project and Python style guides.
