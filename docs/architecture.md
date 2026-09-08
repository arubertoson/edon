# Architecture

## System boundary

Edon consists of two packages with a one-way dependency:

```text
edon_ui  ->  edon
   Qt        no Qt
```

`src/edon/` is the authoritative graph model and execution layer. It must not import PySide6 or
`edon_ui`. `src/edon_ui/` may import the core and translates between domain state and Qt items.

## Core graph (`src/edon/`)

- `EntityGraph` owns nodes and directed edges and enforces graph-linking rules.
- `EntityNode` is the base class for executable nodes and owns its `EntitySocket` instances.
- `EntitySocket`, `SocketAddress`, `SocketDef`, and `EdgeKey` define graph connections.
- `ExecutionEngine` topologically orders and executes nodes.
- `EntitySubGraphNode` contains an internal graph and maps exposed proxy sockets across the graph
  boundary. Nested execution has a configured depth limit.

The graph model is the source of truth. UI state must not redefine graph connectivity or domain
validation.

## User interface (`src/edon_ui/`)

- `EdonApplication` owns or borrows the Qt application, composes services, and creates the main
  window.
- `WorkspaceController` coordinates graph mutations, scenes, visual registries, and nested graph
  navigation.
- `GraphicsScene` and `GraphicsView` handle visual presentation and direct interaction.
- `NodeItem`, `SocketItem`, and `EdgeItem` render graph objects.
- The command registry, key mapping, and key processor translate user input into actions.
- `WorkspaceContextStack` keeps each nested graph paired with its scene and UI registry.

UI events should reach the graph through the controller. After a successful model mutation, the
controller updates the scene and registry. Qt items should receive only the domain identifiers
and presentation data they need.

## Graph lifecycle

1. `WorkspaceController` starts with an empty root graph and scene.
2. `load_graph()` replaces the root context and rebuilds its visual representation.
3. User node and edge requests update the graph and corresponding Qt items through the
   controller.
4. Entering a subgraph pushes a graph/scene/registry context; leaving it restores the parent.
5. `clear_graph()` loads a new empty graph.

## Design constraints

- Preserve core/UI dependency direction.
- Keep graph invariants in the core rather than duplicating them in widgets.
- Keep Qt object ownership and application ownership explicit.
- Use identifiers at coordination boundaries where retaining domain objects would create hidden
  ownership or stale references.
- Treat serialization formats and public APIs as unstable until explicitly versioned.

Significant changes to these constraints require an architecture decision record under
`docs/decisions/`.
