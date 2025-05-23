# Edon Project Architectural Guidelines

## 1. Introduction

This document outlines the high-level architectural principles and core component responsibilities for the Edon project. Its purpose is to ensure a consistent and maintainable codebase by defining the fundamental structure.

For detailed instructions on extending Edon (e.g., adding new node types or commands), please refer to the [Extending Edon: A Developer's Guide](./EXTENDING_EDON_GUIDE.md).

## 2. Core Philosophy

Edon's architecture prioritizes:
-   **Modularity**: Components are loosely coupled with well-defined responsibilities.
-   **Separation of Concerns**: A clear distinction is maintained between the core data model and the user interface.
-   **Readability and Maintainability**: Code should be structured logically (see also the [Python Style Guide](./PYTHON_STYLE_GUIDE.md)).
-   **Testability**: Components are designed to facilitate testing.

## 3. High-Level Architecture: Model-View-Controller (MVC)

Edon employs an architecture inspired by the MVC pattern, tailored for a node-based editor.

### 3.1. The Core Engine (`src/edon/`) - The Model

-   **Purpose**: Contains the fundamental, UI-agnostic data structures and logic of the Edon application. This is the **single source of truth** for the application's data.
-   **Key Components**:
    -   **`EntityGraph`**: The central data model. Manages nodes and the links (edges) between them. It is entirely independent of any UI framework.
    -   **`EntityNode`**: The base representation for nodes within the `EntityGraph`. Defines node properties and sockets.
    -   **`Socket`**: Defines points on an `EntityNode` where links can be formed. Sockets have a direction (source or target) and manage data type compatibility for links.
-   **Responsibilities**:
    -   Defining the structure and state of the node graph.
    -   Managing node and link creation, deletion, and modification.
    -   Serialization and deserialization of the graph.
    -   Any core computational logic related to graph execution (potentially via an `Executor` component).
-   **Key Guideline**: The `edon` package must remain UI-agnostic. No Qt or other UI library dependencies are allowed here.

### 3.2. The User Interface (`src/edon_ui/`) - The View & Controller

-   **Purpose**: Responsible for all aspects of user interaction and visual representation, built using PySide6 (Qt).
-   **Key Components & Responsibilities**:
    -   **`EdonApplication` (`QApplication` subclass)**: The main application entry point; orchestrates UI and core components. (Its detailed responsibilities are standard for a Qt application and not exhaustively listed here beyond its role in initialization).
    -   **Views (`GraphicsView`, `GraphicsScene`, UI `items`)**:
        -   `GraphicsScene` (View): Contains the visual `QGraphicsItem` representations of nodes and links.
        -   `GraphicsView` (View): Displays the `GraphicsScene` and handles direct user interactions (panning, zooming).
        -   UI `items` (`QGraphicsItem` subclasses): Visual counterparts to `EntityNode` and links, residing in the `GraphicsScene`.
    -   **`GraphController` (Controller)**:
        -   **Critical Role**: Acts as the bridge between the `EntityGraph` (Model) and the `GraphicsScene`/`GraphicsView` (View).
        -   **Synchronization**: Observes the `EntityGraph` for changes and updates the `GraphicsScene` to reflect these changes visually.
        -   **Action Translation**: Translates user actions from the `GraphicsView` (e.g., an attempt to draw a link between two visual nodes) into operations on the `EntityGraph` (e.g., creating a logical link between two `EntityNode` instances).
    -   **Command System (`commands/`)**:
        -   Manages user-triggerable actions (e.g., "Create Node," "Save File").
        -   The `KeyProcessor`, `CommandRegistry`, and `KeyMapping` work together to interpret user input (like keyboard shortcuts) and execute the corresponding command logic.
        -   Command actions often interact with the `GraphController` to modify the application state.
-   **Key Guideline**: The `edon_ui` package handles all UI-specific logic, Qt dependencies, event handling, and direct user interaction.

## 4. Key Architectural Principles

-   **Strict Separation of Concerns**: The `edon` core must not depend on `edon_ui`. The UI depends on the core.
-   **Data Flow**:
    1.  User actions in the UI (View) are translated by the `GraphController` (Controller) or Commands.
    2.  These operations modify the `EntityGraph` (Model).
    3.  The `GraphController` (Controller) observes changes in the `EntityGraph` (Model) and updates the `GraphicsScene` (View).