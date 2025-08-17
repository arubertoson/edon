# Sub-Graph Implementation Plan & Memory

## Overview
This document tracks the implementation plan, progress, and decisions for the sub-graph feature in Edon. Sub-graphs allow EntityNodes to encapsulate entire EntityGraphs, creating reusable, hierarchical components.

## Strategic Implementation Plan

### Phase 1: Core Data Model Foundation (PRIORITY 1)
**Goal**: Establish the fundamental data structures without UI dependencies

#### 1.1 Parameter System Design
- **ParameterMapping**: Link sub-graph parameters to internal node attributes/sockets
- **ParameterValue**: Type-safe parameter storage with validation
- **Parameter exposure strategy**: How users designate which internal values become configurable

#### 1.2 SubGraphNode Implementation
- Extend EntityNode with internal_graph capability
- Proxy socket mapping system (external sockets → internal sockets)
- Parameter management integration
- Socket definition derivation from proxy mappings

#### 1.3 ExecutionEngine Enhancement
- Recursive graph execution support
- Sub-graph context management
- Error propagation from nested graphs
- Performance optimization for deep nesting

**Deliverables**:
- `ParameterMapping` and related classes
- `SubGraphNode` class with core functionality
- Enhanced `ExecutionEngine` with sub-graph support
- Unit tests for all core functionality

### Phase 2: Graph Navigation & Management (PRIORITY 2)
**Goal**: Enable creation, editing, and navigation of sub-graphs

#### 2.1 Graph Context System
- **GraphContext**: Track current editing context (parent vs sub-graph)
- **Navigation stack**: Breadcrumb system for nested editing
- **Context switching**: Safe transitions between graph levels

#### 2.2 Sub-Graph Creation Workflows
- **From selection**: Convert selected nodes into sub-graph
- **From scratch**: Create empty sub-graph node
- **Boundary analysis**: Automatic proxy socket detection from selection edges

#### 2.3 Proxy Socket Management
- **Socket exposure UI**: Mark internal sockets as "exposed"
- **Dynamic socket updates**: Add/remove proxy sockets on SubGraphNode
- **Mapping validation**: Ensure proxy mappings remain valid

**Deliverables**:
- Graph context management system
- Sub-graph creation commands
- Proxy socket exposure mechanisms
- Navigation infrastructure

### Phase 3: Serialization & Persistence (PRIORITY 3)
**Goal**: Save/load sub-graphs with full fidelity

#### 3.1 Serialization Strategy
- **Nested graph serialization**: Handle EntityGraph within SubGraphNode
- **Reference integrity**: Maintain proxy socket mappings across save/load
- **Version compatibility**: Handle schema evolution
- **Circular reference handling**: Prevent infinite serialization loops

#### 3.2 Sub-Graph Library System
- **Template storage**: Save sub-graph definitions for reuse
- **Versioning**: Track sub-graph template versions
- **Import/export**: Share sub-graph definitions between projects

**Deliverables**:
- Enhanced serialization for nested graphs
- Sub-graph template system
- Import/export functionality

### Phase 4: UI Integration (PRIORITY 4)
**Goal**: Provide intuitive visual interface for sub-graph management

#### 4.1 Visual Representation
- **SubGraphNode styling**: Distinct appearance from regular nodes
- **Nesting indicators**: Visual cues for graph hierarchy
- **Parameter panels**: UI for configuring exposed parameters

#### 4.2 Editing Interface
- **Double-click navigation**: Enter sub-graph editing mode
- **Context breadcrumbs**: Show current location in graph hierarchy
- **Socket exposure UI**: Right-click to expose/unexpose sockets

#### 4.3 Advanced Features
- **Minimap**: Overview of sub-graph contents
- **Parameter binding UI**: Visual parameter-to-socket connections
- **Validation feedback**: Real-time error indication

**Deliverables**:
- SubGraphNode visual components
- Sub-graph editing interface
- Parameter configuration UI
- Navigation and context UI

## Technical Architecture Decisions

### 1. Parameter System Architecture
```python
@dataclass
class ParameterMapping:
    """Maps a sub-graph parameter to an internal node attribute or socket."""
    parameter_name: str
    target_type: Literal["node_attribute", "socket_value", "socket_default"]
    target_node_id: str
    target_path: str  # e.g., "value" for node attr, "input_socket_name" for socket
    parameter_type: SocketType
    default_value: Any = None

@dataclass
class SubGraphParameter:
    """Represents an exposed parameter of a sub-graph."""
    name: str
    parameter_type: SocketType
    description: str = ""
    default_value: Any = None
    current_value: Any = None
```

### 2. Execution Flow Strategy
- **Depth-first execution**: Process sub-graphs completely before continuing parent
- **Context isolation**: Each sub-graph execution maintains separate state
- **Error bubbling**: Propagate errors with context information
- **Cycle detection**: Enhanced to work across graph boundaries

### 3. Socket Proxy System
```python
@dataclass
class ProxySocketMapping:
    """Maps a SubGraphNode socket to an internal graph socket."""
    proxy_socket_name: str
    internal_socket_addr: SocketAddress
    socket_def: SocketDef  # Derived from internal socket
```

### 4. Navigation Context
```python
@dataclass
class GraphEditingContext:
    """Tracks the current graph editing context."""
    current_graph: EntityGraph
    parent_context: GraphEditingContext | None = None
    sub_graph_node_id: str | None = None  # If editing a sub-graph
    breadcrumb_path: list[str] = field(default_factory=list)
```

## Implementation Order & Dependencies

### Phase 1 Tasks (Weeks 1-2)
1. **ParameterMapping system** (1-2 days)
   - Define parameter mapping data structures
   - Implement parameter validation
   - Unit tests for parameter system

2. **SubGraphNode core** (3-4 days)
   - Basic SubGraphNode class
   - Proxy socket mapping logic
   - Socket definition derivation
   - Parameter integration

3. **ExecutionEngine enhancement** (2-3 days)
   - Recursive execution support
   - Sub-graph context management
   - Error handling improvements

### Phase 2 Tasks (Weeks 3-4)
1. **Graph context system** (2-3 days)
   - GraphEditingContext implementation
   - Navigation stack management
   - Context switching logic

2. **Sub-graph creation** (3-4 days)
   - Selection-to-subgraph conversion
   - Boundary edge analysis
   - Proxy socket auto-detection

3. **Socket exposure system** (2-3 days)
   - Mark sockets as exposed
   - Dynamic proxy socket updates
   - Validation and error handling

### Phase 3 Tasks (Weeks 5-6)
1. **Serialization enhancement** (4-5 days)
   - Nested graph serialization
   - Reference integrity maintenance
   - Version compatibility

2. **Sub-graph library** (2-3 days)
   - Template storage system
   - Import/export functionality

### Phase 4 Tasks (Weeks 7-8)
1. **Visual components** (3-4 days)
   - SubGraphNode UI representation
   - Parameter configuration panels
   - Context navigation UI

2. **Editing interface** (3-4 days)
   - Sub-graph editing mode
   - Socket exposure UI
   - Advanced features

## Risk Assessment & Mitigation

### High Risk Areas
1. **Execution complexity**: Recursive execution with proper error handling
   - *Mitigation*: Extensive unit testing, execution context isolation
   
2. **Serialization complexity**: Nested graphs with circular references
   - *Mitigation*: Reference tracking, validation during serialization
   
3. **UI state management**: Complex navigation between graph contexts
   - *Mitigation*: Clear state management patterns, context isolation

### Medium Risk Areas
1. **Performance**: Deep sub-graph nesting could impact execution speed
   - *Mitigation*: Execution profiling, optimization strategies
   
2. **Parameter binding complexity**: Complex parameter-to-internal mappings
   - *Mitigation*: Simple parameter types initially, gradual complexity increase

## Current Status
- **Phase**: Phase 1.1 - Core Data Model Foundation (COMPLETED)
- **Next Action**: Create unit tests and integration tests for SubGraphNode functionality
- **Blockers**: None
- **Notes**: 
  - ✅ Parameter system implemented with simplified SocketAddress-based approach
  - ✅ SubGraphNode with dynamic socket creation implemented
  - ✅ ExecutionEngine enhanced for recursive sub-graph execution
  - ✅ All core data structures and methods implemented
  - 🔄 Ready for testing phase - need unit tests and integration validation

## Decision Log
- **2025-06-02**: Decided on 4-phase implementation approach
- **2025-06-02**: Parameter system will use mapping-based approach for flexibility
- **2025-06-02**: Execution will be depth-first for simplicity and predictability
- **2025-06-02**: Simplified parameter system to use SocketAddress directly, avoiding duplication
- **2025-06-02**: SubGraphNode overrides __post_init__ completely for dynamic socket creation
- **2025-06-02**: ExecutionEngine uses depth tracking and string-based SubGraphNode detection
- **2025-06-02**: Phase 1.1 completed - all core data structures implemented and ready for testing

## Open Questions
1. Should sub-graphs support recursive self-reference? (Probably not initially)
2. How deep should sub-graph nesting be allowed? (Start with reasonable limit)
3. Should parameters support complex types or start with primitives? (Start simple)
4. How should sub-graph templates handle version conflicts? (Manual resolution initially)

## Future Enhancements (Post-MVP)
- Sub-graph debugging tools
- Performance profiling for nested execution
- Advanced parameter types (lists, objects)
- Sub-graph diff/merge tools
- Collaborative sub-graph sharing
