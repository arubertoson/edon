# Contributing to Edon

## Setup

Edon requires Python 3.13 or newer and uses `uv` for dependency management.

```bash
git clone <repository-url>
cd edon
uv sync --locked
uv run pre-commit install
```

The commit hooks run Ruff linting and formatting on staged Python files. The push hooks run Pyrefly
and the normal pytest profile. Skip an individual push check for intentional WIP with, for example,
`SKIP=pytest git push`, or skip all push hooks with `git push --no-verify`. CI remains the
authoritative quality gate.

Do not edit `uv.lock` manually. Commit it when an intentional dependency change updates it.

## Before submitting a change

Run the checks relevant to the change. The complete local validation is:

```bash
uv run pyrefly check
uv run ruff check .
uv run ruff format --check .
QT_QPA_PLATFORM=offscreen uv run pytest
```

Use `uv run ruff format .` to format code. Do not suppress diagnostics or exclude tests merely
to make validation pass. If an unrelated existing failure remains, report it explicitly in the
pull request.

## Change expectations

- Keep changes focused; do not mix feature work with unrelated formatting or refactoring.
- Add tests for new behavior and fixed defects.
- Preserve the dependency direction described in [the architecture guide](docs/architecture.md).
- Follow [the code style guide](docs/style.md) and [testing strategy](docs/testing.md).
- Update durable documentation when behavior, architecture, or developer workflow changes.
- Put temporary plans and feature proposals in issues or pull requests, not permanent docs.

## Pull requests

A pull request should explain:

1. The problem being solved.
2. The chosen approach and important trade-offs.
3. The validation performed and its results.
4. Known limitations or follow-up work.

Use concise imperative commit subjects, such as `Add cycle regression test` or
`Fix hosted QApplication ownership`.

## Reporting defects

Include reproduction steps, expected and actual behavior, Edon and Python versions, operating
system, and relevant logs. Reduce the case when practical, but never include credentials or
other sensitive information.
