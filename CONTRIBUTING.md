# Contributing to Edon

First off, thank you for considering contributing to Edon! It's people like you that make Edon such a great tool. We welcome any form of contribution, from reporting bugs and suggesting features to writing code and improving documentation.

This document provides guidelines for contributing to Edon. Please read it carefully to ensure a smooth and effective collaboration process.

## Table of Contents

- [Contributing to Edon](#contributing-to-edon)
  - [Table of Contents](#table-of-contents)
  - [Code of Conduct](#code-of-conduct)
  - [How Can I Contribute?](#how-can-i-contribute)
    - [Reporting Bugs](#reporting-bugs)
    - [Suggesting Enhancements](#suggesting-enhancements)
    - [Asking Questions](#asking-questions)
    - [Your First Code Contribution](#your-first-code-contribution)
    - [Pull Requests](#pull-requests)
  - [Development Setup](#development-setup)
  - [Architectural Overview](#architectural-overview)
  - [Style Guides](#style-guides)
    - [Python Code Style](#python-code-style)
    - [Commit Messages](#commit-messages)
  - [Testing](#testing)
  - [License](#license)

## Code of Conduct

This project and everyone participating in it is governed by the [Edon Code of Conduct](CODE_OF_CONDUCT.md) (To be created: We recommend adopting a standard Code of Conduct, like the Contributor Covenant). Please adhere to this code in all your interactions with the project.

## How Can I Contribute?

### Reporting Bugs

If you encounter a bug, please help us by reporting it. Good bug reports are extremely helpful!

Before submitting a bug report, please:
1.  **Check the existing issues:** Search the issue tracker to see if the bug has already been reported.
2.  **Ensure you have the latest version:** Try to reproduce the bug with the latest version of Edon.
3.  **Isolate the problem:** Create a minimal, reproducible example if possible.

When submitting a bug report, please include:
-   A clear and descriptive title.
-   Steps to reproduce the bug.
-   What you expected to happen.
-   What actually happened.
-   Your Edon version, Python version, and operating system.
-   Any relevant error messages or screenshots.

Open a new issue [here](https://github.com/your-username/edon/issues) (replace with your actual issue tracker link).

### Suggesting Enhancements

We welcome suggestions for new features or improvements to existing functionality.

Before submitting an enhancement suggestion, please:
1.  **Check the existing issues/enhancement requests:** Search the issue tracker to see if your idea has already been discussed.
2.  **Consider the scope:** Think about whether your enhancement fits the general direction of Edon.

When submitting an enhancement suggestion, please include:
-   A clear and descriptive title.
-   A detailed description of the proposed enhancement.
-   Why this enhancement would be useful.
-   Any potential drawbacks or alternatives.

Open a new issue [here](https://github.com/your-username/edon/issues) (replace with your actual issue tracker link).

### Asking Questions

If you have questions about using Edon or its development, please feel free to ask. The issue tracker can be used for this, or if a dedicated discussion forum/channel exists, that would be preferred.

### Your First Code Contribution

Unsure where to begin contributing to Edon? You can start by looking through `good first issue` or `help wanted` issues: (Link to these labels in your issue tracker).

Working on your first Pull Request? Here are a few pointers:
-   Fork the repository and create your branch from `main` (or the current development branch).
-   Make sure your code adheres to the [Style Guides](#style-guides).
-   Include tests that cover your changes.
-   Ensure your commit messages are clear and follow our conventions.
-   Open a Pull Request, clearly describing the changes you've made.

### Pull Requests

When you're ready to contribute code, please follow these steps:
1.  Fork the repository.
2.  Create a new branch for your feature or bug fix: `git checkout -b feature/your-feature-name` or `git checkout -b fix/your-bug-fix-name`.
3.  Make your changes, adhering to the [Style Guides](#style-guides).
4.  Add tests for your changes.
5.  Ensure all tests pass.
6.  Commit your changes with a descriptive commit message.
7.  Push your branch to your fork: `git push origin feature/your-feature-name`.
8.  Open a Pull Request to the `main` branch of the Edon repository.
9.  Clearly describe the purpose of your Pull Request and the changes made. Reference any related issues.
10. Be prepared to discuss your changes and make adjustments as requested by the maintainers.

## Development Setup

To set up Edon for development:
1.  Clone your forked repository: `git clone https://github.com/your-username/edon.git`
2.  Navigate to the project directory: `cd edon`
3.  Set up the Python environment and install dependencies using `uv`:
    ```bash
    uv venv  # Create a virtual environment
    uv pip install -e .[dev] # Install in editable mode with dev dependencies
    ```
    (Adjust `.[dev]` if your `pyproject.toml` specifies development dependencies differently).

## Architectural Overview

Edon has a modular architecture designed for clarity and maintainability. Key principles include separation of concerns between the core engine and the user interface.

For a comprehensive understanding of Edon's architecture, core components, and design patterns, please refer to the **[Edon Project Architectural Guidelines](./docs/ARCHITECTURAL_GUIDELINES.md)**.

## Style Guides

### Python Code Style

All Python code must adhere to the **[Edon Python Style and Quality Guide](./docs/PYTHON_STYLE_GUIDE.md)**. This guide covers Python 3.13 usage, PySide6, comprehensive type hinting, Google-style docstrings, naming conventions, code structure, and more.

### Commit Messages

Please follow these conventions for commit messages:
-   Start with a verb in the imperative mood (e.g., `Add feature`, `Fix bug`, `Refactor code`).
-   Keep the subject line concise (max 50 characters).
-   Provide a more detailed explanation in the body if necessary.
-   Reference relevant issue numbers (e.g., `Fixes #123`).

Example:
```
Refactor node creation logic

- Simplify the node instantiation process in GraphController.
- Improve type hints for node factory functions.

Addresses issue #45.
```

## Testing

-   All new features and bug fixes should include corresponding tests.
-   Tests are located in the `tests/` directory.
-   Ensure all tests pass before submitting a Pull Request.
    ```bash
    # Command to run tests (e.g., using pytest)
    uv run pytest
    ```
    (Adjust if you use a different test runner).

## License

By contributing to Edon, you agree that your contributions will be licensed under its [LICENSE_FILENAME] (e.g., MIT License. Specify your project's license).

---

Thank you for contributing to Edon! 