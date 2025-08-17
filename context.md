# Implementation Plan: Decouple Graph from Controller Construction

## Overview
Refactor the GraphController to start with an empty EntityGraph and provide explicit graph loading functionality, eliminating conditional logic in node registration and preparing for robust save/load operations.

## Phase 1: Core Controller Refactoring

### 1.1 Update GraphController Constructor
**File**: `src/edon_ui/graph/controller.py`

```python
def __init__(self, node_type_registry: Mapping[str, Type[EntityNode]] | None = None):
    """
    Initialize controller with empty graph and registry.
    Graph content will be loaded separately via load_graph().
    """
    self._scene: "GraphicsScene | None" = None
    self.entity_graph: EntityGraph = EntityGraph()  # Always start empty
    self.data: GraphUIDataRegistry = GraphUIDataRegistry()
    self.node_registry: NodeRegistryMap = dict(node_type_registry or {})
    
```

### 1.2 Add Graph Loading Method
**File**: `src/edon_ui/graph/controller.py`

```python
def load_graph(self, entity_graph: EntityGraph) -> None:
    """
    Replaces the current graph and rebuilds the entire UI representation.
    
    This method provides a clean slate approach: it clears all existing UI elements,
    replaces the entity graph, and rebuilds the UI from the new graph data.
    Ideal for file loading, graph replacement, or resetting the workspace.
    """
    logger.info(f"Loading new graph with {len(entity_graph.nodes)} nodes")
    
    self._clear_all_ui()
    self.entity_graph = entity_graph
    self._populate_scene_from_graph_data()
    
    logger.info("Graph loading completed successfully")

def clear_graph(self) -> None:
    """
    Clears the current graph and all UI elements, returning to empty state.
    """
    logger.info("Clearing current graph and UI")
    self._clear_all_ui()
    self.entity_graph = EntityGraph()
    self._scene._update_scene_content_display()
```

### 1.3 Add UI Clearing Method
**File**: `src/edon_ui/graph/controller.py`

```python
def _clear_all_ui(self) -> None:
    """
    Removes all UI elements and clears the registry.
    
    This method ensures a clean slate by removing all visual elements
    and resetting the UI data registry. Order matters: edges must be
    removed before nodes due to dependencies.
    """
    logger.debug("Clearing all UI elements and registry")

    # XXX: We should look into scene reset that is prettier than this.
    # I don't think we have to go through everything and delete it.
    # But if we do we should delegate it to scene either way.
    
    # Remove all edges first (they depend on nodes)
    edge_items_to_remove = list(self.data.edges)
    for edge_item in edge_items_to_remove:
        self._scene.remove_edge(edge_item)
    
    # Remove all nodes
    node_items_to_remove = list(self.data.nodes)
    for node_item in node_items_to_remove:
        self._scene.remove_node(node_item)
    
    # Reset the registry to clean state
    self.data = GraphUIDataRegistry()
    self._registration_order.clear()
    
    logger.debug(f"Cleared {len(edge_items_to_remove)} edges and {len(node_items_to_remove)} nodes")
```

### 1.4 Simplify Node Registration
**File**: `src/edon_ui/graph/controller.py`

```python
def _register_node_internal(self, entity_node: EntityNode, scene_position: QPointF) -> NodeItem | None:
    """
    Creates a NodeItem for an EntityNode that is ALREADY in self.entity_graph.
    
    This method only handles UI registration and assumes the entity_node
    is already properly added to the entity graph. It never modifies
    the entity graph itself, maintaining clear separation of concerns.
    """
    logger.debug(f"Registering UI for existing node '{entity_node.id}' at {scene_position}")
    
    # Validate the node exists in the entity graph
    if entity_node.id not in self.entity_graph.nodes:
        raise ValueError(f"Cannot register UI for node '{entity_node.id}': not found in entity graph")
    
    node_item = create_node_item(
        entity_node,
        scene_position.x(),
        scene_position.y(),
    )
    
    # Register with scene and data layer
    self.scene.add_node(node_item)
    self.entity_graph.add_node(new_entity_node)

    self.data.register_node_with_sockets(node_item)
    
    return node_item

def request_add_node(self, node_entity_class: type[EntityNode], scene_position: QPointF, **node_specific_kwargs) -> NodeItem | None:
    """
    Creates a new entity node and adds it to both the entity graph and UI.
    
    This is the primary method for adding new nodes during user interaction.
    It follows the pattern: create entity → add to graph → register UI.
    """
    logger.debug(f"Creating new node of type '{node_entity_class}' at {scene_position}")
    
    new_entity_node = node_entity_class(**node_specific_kwargs)
    
    return self._register_node_internal(new_entity_node, scene_position)
```

## Phase 2: Application Layer Updates

### 2.1 Update EdonApplication Constructor
**File**: `src/edon_ui/app.py`

```python
def __init__(
    self,
    entity_graph: EntityGraph | None = None,
    node_registry: dict[str, type[EntityNode]] | None = None,
    log_level: str = "DEBUG",
) -> None:
    # ... existing logging setup ...
    
    self._node_registry: dict[str, type[EntityNode]] = node_registry or {}
    
    # Controller starts with empty graph
    self._graph_controller: GraphController = GraphController(node_type_registry=self._node_registry)
    
    self._graphics_scene: GraphicsScene = GraphicsScene(controller=self._graph_controller)
    self._graphics_view: GraphicsView = GraphicsView(self._graphics_scene)
    self._graph_controller.set_scene(self._graphics_scene)  # Scene starts empty
    
    # ... rest of initialization ...
    
    # Load initial graph if provided
    if entity_graph:
        self._graph_controller.load_graph(entity_graph)
    
    logger.info("EdonApplication initialized.")
```

### 2.2 Add Graph Management Methods
**File**: `src/edon_ui/app.py`

```python
def load_graph(self, entity_graph: EntityGraph) -> None:
    """
    Loads a new graph, replacing the current one.
    
    This method is the primary interface for loading saved files,
    importing graphs, or replacing the current workspace content.
    """
    logger.info(f"Application loading new graph with {len(entity_graph.nodes)} nodes")
    self._graph_controller.load_graph(entity_graph)

def clear_graph(self) -> None:
    """
    Clears the current graph and returns to empty workspace.
    """
    logger.info("Application clearing current graph")
    self._graph_controller.clear_graph()

@property
def entity_graph(self) -> EntityGraph:
    """Access to the current entity graph for serialization or inspection."""
    return self._graph_controller.entity_graph

@entity_graph.setter
def entity_graph(self, value: EntityGraph) -> None:
    """Sets a new graph via the load_graph mechanism."""
    self.load_graph(value)
```

### 2.3 Remove Reinitialize Method
**File**: `src/edon_ui/app.py`

```python
# Remove the entire _reinitialize_graph_components method and its calls
# The new load_graph approach eliminates the need for component recreation

@property
def node_registry(self) -> dict[str, type[EntityNode]]:
    return self._node_registry

@node_registry.setter
def node_registry(self, value: dict[str, type[EntityNode]]) -> None:
    """
    Sets the registry for mapping node type identifiers to their classes.
    
    Note: This only affects future node creation operations. Existing nodes
    in the graph are not affected by registry changes.
    """
    self._node_registry = value
    self._graph_controller.node_registry.clear()
    self._graph_controller.node_registry.update(value)
    logger.info(f"Node registry updated with {len(value)} node types")
```

## Phase 4: Documentation Updates

### 4.1 Update Docstrings
- Update all affected method docstrings to reflect new behavior
- Add examples of the new loading workflow
- Document the clear separation between entity graph and UI operations

### 4.2 Update Architecture Documentation
**File**: `docs/ARCHITECTURAL_GUIDELINES.md`

Add section on graph loading workflow:
```markdown
## Graph Loading Workflow

The Edon application follows a clear separation between entity graph management
and UI representation:

1. **Initialization**: Controllers start with empty graphs
2. **Loading**: Use `load_graph()` to replace content
3. **Adding**: Use `request_add_node()` for user-driven additions
4. **Clearing**: Use `clear_graph()` to return to empty state
```

## Implementation Order

1. **Phase 1.1-1.3**: Core controller refactoring (constructor, load_graph, clear methods)
2. **Phase 1.4**: Simplify node registration methods
3. **Phase 1.5**: Update scene population
4. **Phase 2**: Application layer updates
5. **Phase 3**: Testing
6. **Phase 4**: Documentation

## Risk Mitigation

- **Backward Compatibility**: The public API remains largely the same
- **Testing**: Each phase includes comprehensive tests
- **Rollback Plan**: Changes are isolated to specific methods, making rollback straightforward
- **Validation**: Registry assertions ensure data integrity throughout

This plan eliminates the conditional logic you disliked while preparing the foundation for robust save/load functionality.

Implement this and stick to the plan and don't do any code deviations.
