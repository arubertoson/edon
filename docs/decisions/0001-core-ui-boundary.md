# ADR 0001: Keep the graph core independent of Qt

- Status: Accepted
- Date: 2025-05-09

## Context

Edon needs a reusable graph model and a PySide6 editor. Allowing domain objects to depend on Qt
would make graph execution harder to test and reuse, while allowing visual items to own domain
state would create competing sources of truth.

## Decision

`src/edon/` contains the graph model and execution logic and must not depend on PySide6 or
`edon_ui`. `src/edon_ui/` depends on the core and uses `WorkspaceController` as the coordination
boundary between graph mutations and visual state.

The graph owns nodes, sockets, edges, and their invariants. Qt items own presentation and direct
interaction state. UI components receive narrow domain identifiers and presentation values where
possible; the controller performs translation and synchronization.

## Consequences

- Core graph behavior can run and be tested without a Qt application.
- Alternative interfaces can reuse the graph engine.
- UI code may import core contracts, but the reverse dependency is prohibited.
- The controller and UI registry carry explicit synchronization responsibility.
- Changes to domain representations may require adapter changes without requiring rendering items
  to duplicate domain rules.
