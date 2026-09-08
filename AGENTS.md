# Agent instructions

## Project

Edon is a Python 3.13 node-graph engine and PySide6 desktop editor.

- `src/edon/`: UI-independent graph model and execution logic.
- `src/edon_ui/`: Qt presentation, interaction, and model/UI coordination.
- `tests/`: integration, property, fuzz/stateful, UI, and focused unit tests.
- `examples/`: runnable integrations and custom nodes.

Read `docs/architecture.md`, `docs/style.md`, and `docs/testing.md` before making broad changes.

## Commands

```bash
uv sync --locked
uv run pyrefly check
uv run ruff check .
uv run ruff format --check .
QT_QPA_PLATFORM=offscreen uv run pytest
```

Pyrefly is the sole type checker. Ruff is the sole linter and formatter. Configuration in
`pyproject.toml` is authoritative.

## Required practices

- Type all function parameters and returns, class attributes, and significant variables.
- Use modern Python 3.13 syntax and abstract collection types from `collections.abc`.
- Keep `edon` independent of Qt and `edon_ui`.
- Use assertions for internal invariants and programmer errors.
- Use explicit exceptions for invalid external data and expected runtime failures.
- Prefer guard clauses, descriptive names, small scopes, and focused functions.
- Use Loguru and never log secrets or personal data.
- Add regression coverage for defects and behavior-focused tests for changes.
- Do not add dependencies or suppress diagnostics without a documented justification.
- Do not combine unrelated style changes with feature or bug-fix work.

## Documentation

Keep one authoritative location for each rule. Update durable docs with behavior changes.
Temporary plans, status reports, generated source dumps, and feature backlogs belong in issues
or pull requests rather than repository documentation.
