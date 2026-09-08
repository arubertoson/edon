# Testing strategy

Edon uses risk-based testing. Choose the cheapest test level that gives confidence in observable
behavior; no test category is preferred categorically.

## Test levels

- **Focused unit tests** cover isolated algorithms, parsing, boundary calculations, and error
  contracts.
- **Integration tests** cover graph construction, linking, execution, subgraphs, and collaboration
  between controllers and Qt components.
- **Property and stateful tests** cover graph invariants and large spaces of operation sequences.
- **UI tests** cover Qt ownership, signals, rendering-related calculations, and critical user
  interactions. Prefer stable behavior over pixel-level implementation details.
- **Regression tests** preserve every significant defect reproduction at the lowest suitable
  level.

Use end-to-end tests sparingly for critical workflows that cannot be established at a lower level.

## Organization

Tests mirror their subject under `tests/`:

```text
tests/edon/             core and execution tests
tests/edon/property/    Hypothesis properties
tests/edon/fuzz/        Hypothesis state machines
tests/edon_ui/          Qt and UI tests
tests/fixtures/         shared test support
```

Keep fixtures narrow and explicit. A test should own or clearly borrow every graph, temporary
resource, window, and Qt object it creates.

## Writing tests

- Test public behavior and invariants rather than private implementation steps.
- Assert both successful state changes and rejection behavior.
- Do not catch unexpected exceptions or discard them with `assume(False)`.
- Build independent test oracles; do not use the implementation under test to generate expected
  results.
- Include empty, boundary, invalid, nested, and cleanup cases where relevant.
- For UI tests, use pytest-qt fixtures and register windows for cleanup.
- Avoid timing assumptions. Wait for explicit signals or conditions.
- Keep generated tests reproducible and promote useful minimized failures to permanent regression
  examples.

## Commands

Run all tests:

```bash
uv run pytest
```

On headless Linux:

```bash
QT_QPA_PLATFORM=offscreen uv run pytest
```

Run generated core tests with the CI profile:

```bash
HYPOTHESIS_PROFILE=ci uv run pytest tests/edon/property tests/edon/fuzz
```

Replay with a recorded seed when applicable:

```bash
uv run pytest <test-path> --hypothesis-seed=<seed>
```

Record the failing test, source revision, `uv.lock`, profile, and seed or reproduction blob.
Seed replay depends on unchanged code, dependency versions, and settings.

## Hypothesis profiles

Profiles are selected once in `tests/conftest.py`, before test modules are imported:

- `dev` (default): 50 examples and up to 50 state-machine steps.
- `ci`: 200 examples and up to 100 state-machine steps with deterministic generation.

Both retain shrinking and health checks, disable timing deadlines, and print reproduction blobs.
Do not load profiles or override shared state-machine settings in individual modules without a
specific test-level reason.

## Quality gate

A change is ready when its relevant tests pass and the complete validation result is reported:

```bash
uv run pyrefly check
uv run ruff check .
uv run ruff format --check .
QT_QPA_PLATFORM=offscreen uv run pytest
```

Never hide a failure with exclusions or suppressions. If an unrelated known failure exists, state
it explicitly with evidence.
