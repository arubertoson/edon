# Feature Request: Customizable Key Bindings

## 1. Summary

This feature request proposes the ability for users to customize the key bindings (keyboard shortcuts) for commands within the Edon application. This would allow users to tailor the application's controls to their preferences or to match key binding schemes they are familiar with from other software.

## 2. Motivation

-   **User Preference & Ergonomics**: Different users have different preferences for keyboard shortcuts. Customization allows for a more comfortable and efficient user experience.
-   **Accessibility**: Users with specific accessibility needs might require the ability to remap keys.
-   **Avoiding Conflicts**: Default key bindings might conflict with system-wide shortcuts or shortcuts used by other concurrently running applications.
-   **Workflow Optimization**: Users can optimize their workflows by assigning frequently used commands to easily accessible keys.
-   **Familiarity**: Users migrating from other node-based editors might want to replicate familiar key binding schemes.

## 3. Proposed Changes

### 3.1. Core Functionality

-   **View Current Bindings**: A UI panel or dialog where users can see all registered commands and their current key bindings.
-   **Modify Bindings**: An interface to change the key sequence for any given command.
    -   This should allow for single keys, modifier combinations (Ctrl, Shift, Alt), and potentially sequences of keys.
-   **Persistence**: Custom key bindings should be saved to a user-specific configuration file (e.g., JSON, INI, or YAML format) and loaded when the application starts.
-   **Loading Custom Bindings**: The `KeyMapping` system will need to be updated to:
    1.  Load default key mappings from `CommandDefinition`s.
    2.  Load custom key mappings from the user's configuration file.
    3.  Apply custom mappings, overriding defaults where specified.
-   **Conflict Detection & Resolution**:
    -   When a user attempts to assign a new key binding, the system should check if it's already in use by another command.
    -   If a conflict is detected, the UI should inform the user and provide options (e.g., unbind the conflicting command, choose a different key).
-   **Reset to Defaults**: An option to revert all key bindings (or a specific binding) back to their default state.

### 3.2. `KeyMapping` and `EdonApplication._setup_command_system`

-   The `EdonApplication._setup_command_system` method currently initializes `KeyMapping.from_command_defaults()`. This will need to be augmented to load and apply custom key bindings *after* loading defaults.
-   The `KeyMapping` class might need new methods to support loading from a configuration file and merging/overriding mappings.

## 4. Scope Considerations

-   **Phase 1 (Basic Customization)**:
    -   UI to view and modify bindings for existing commands.
    -   Saving and loading custom bindings to a user config file.
    -   Basic conflict detection (alerting the user).
    -   Reset to defaults.
-   **Phase 2 (Advanced Features - Optional)**:
    -   Support for multiple key binding profiles.
    -   More sophisticated conflict resolution UI.
    -   Ability to export/import key binding configurations.
    -   Context-specific key bindings (though this might be overly complex for an initial implementation).

## 5. Potential Challenges

-   **UI Design**: Creating an intuitive and user-friendly interface for managing a potentially large list of commands and their key bindings.
-   **Key Sequence Input**: Reliably capturing arbitrary key sequences from the user for assignment. Qt provides mechanisms for this (e.g., `QKeySequenceEdit`).
-   **Conflict Resolution Logic**: Designing a robust and clear way to handle and resolve key binding conflicts.
-   **Configuration File Management**: Ensuring robust saving and loading of the custom key binding configuration, and handling potential corruption or versioning issues if the config format evolves.
-   **Discoverability**: Making users aware of which commands are available for key binding.

## 6. Open Questions

-   What is the preferred format for the custom key binding configuration file? (e.g., JSON, YAML, custom format)
-   How should conflicts be presented to the user? Just an error, or a dialog with options?
-   Should all registered commands be customizable, or only a subset? (Presumably all that have a `CommandDefinition`).
-   How to handle unassigning a key from a command? 