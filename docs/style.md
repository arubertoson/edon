# Code style

Configuration in `pyproject.toml` and automated checks are authoritative for formatting, linting,
and typing. This document covers design rules that tools cannot fully enforce.

## Python and typing

- Target Python 3.13 and use modern syntax such as `list[str]`, `X | None`, and `type Alias = ...`.
- Type all function and method parameters and returns, class attributes, and significant local
  variables.
- Import abstract interfaces such as `Callable`, `Iterable`, and `Mapping` from
  `collections.abc`.
- Use `TYPE_CHECKING` for imports needed only by static analysis.
- Prefer protocols or narrow interfaces over broad concrete dependencies.
- Do not silence Pyrefly without documenting why the checker cannot express a valid contract.

## Design and organization

- Use descriptive names; include units or qualifiers where relevant, such as `timeout_ms`.
- Keep functions focused and normally below 70 lines. Split responsibilities rather than gaming
  the line limit.
- Put high-level control flow before implementation helpers.
- Prefer guard clauses over deep nesting and keep variables near their use.
- Keep public interfaces small and return contracts explicit.
- Use absolute imports grouped as standard library, third-party, local, then type-only imports.
- Avoid unrelated formatting or refactoring in behavior changes.

## Errors and invariants

Use `assert` for programmer errors: violated internal preconditions, impossible states, and broken
invariants. Assertions are not user-facing validation and must not be required for safe handling
of external data.

Use explicit exceptions for expected runtime failures such as invalid user input, malformed files,
permissions, or unavailable external resources. Catch specific exceptions at a layer that can add
context or recover; never use `except: pass`.

## Resources and performance

- Use context managers or explicit `try/finally` cleanup for owned resources.
- Avoid unnecessary copies and repeated disk or network operations.
- For performance-sensitive designs, estimate scale first and measure before micro-optimizing.
- Optimize in this general order: network, disk, memory, CPU.
- Add dependencies only when their maintenance and runtime cost is justified.

## Qt

- Keep all Qt dependencies in `edon_ui`.
- Make QObject and QGraphicsItem ownership explicit.
- Prefer signals and slots across UI components when direct calls would create lifecycle coupling.
- Do not start a second Qt event loop or construct a second `QApplication` when hosted.

## Logging and documentation

Use Loguru with severity proportional to operational impact. Never log credentials, secrets, or
personal data.

Docstrings and comments should explain contracts, constraints, and non-obvious intent—not narrate
the implementation. Public modules and interfaces should have concise docstrings. Keep comments
accurate when behavior changes.
