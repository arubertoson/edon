# Edon

Edon is an experimental node-graph engine and desktop editor built with Python 3.13 and PySide6.
The `edon` package provides the UI-independent graph model and execution engine; `edon_ui`
provides the Qt editor.

## Requirements

- Python 3.13 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A graphical environment supported by Qt

## Development setup

```bash
uv sync --locked
```

Run the empty editor:

```bash
uv run python -m edon_ui.app
```

Run the custom-node example:

```bash
uv run python examples/custom_nodes.py
```

## Development checks

```bash
uv run pyrefly check
uv run ruff check .
uv run ruff format --check .
QT_QPA_PLATFORM=offscreen uv run pytest
```

The offscreen platform is intended for headless Linux environments. On a desktop, plain
`uv run pytest` is sufficient.

## Documentation

- [Architecture](docs/architecture.md)
- [Code style](docs/style.md)
- [Testing strategy](docs/testing.md)
- [Contributing](CONTRIBUTING.md)

## Project status

Edon is under active development. APIs and saved graph formats are not yet stable.
