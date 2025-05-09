# Refactoring Decision Log - edon_ui

This document records significant architectural decisions and refactoring steps taken within the `edon_ui` module.

## Goal: Decoupling Components with Signals and Slots

**Date:** (Current Date)

**Problem:** The initial implementation of `edon_ui` exhibits tight coupling between several components:
    - `NodeItem` directly calls methods on `GraphicsScene`.
    - `AppContextMenu` directly calls methods on `MainWindow` and `QApplication`.
    - `MainWindow` directly calls methods on `GraphicsView` to notify of scene changes.

This tight coupling reduces modularity, makes components harder to reuse independently, and can lead to a more brittle codebase where changes in one component have unintended ripple effects in others.

**Decision:** Refactor the codebase to use Qt's signals and slots mechanism for inter-component communication. This will:
    - Decouple senders of information from receivers.
    - Improve code clarity by making data flow more explicit.
    - Enhance reusability and testability of individual components.
    - Make the system more extensible for future features.

**Affected Components:**
    - `node_item.py`
    - `graphics_scene.py`
    - `context_menu.py`
    - `graphics_view.py`
    - `main_window.py`
