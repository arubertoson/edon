# Feature Request: Node Type Registry and Discovery

## Overview
To support extensibility, usability, and a scalable user experience, the application should provide a robust system for registering, discovering, and managing available node types. This registry will serve as the foundation for both built-in and user-defined nodes, enabling dynamic node creation, search, and categorization within the UI.

## Desired Outcomes
- **Centralized Node Management:** All node types (core, custom, and plugin) are registered in a single, discoverable location, making it easy for the system and users to know what is available.
- **Dynamic Node Creation:** Users can add new nodes to their graph from a searchable or categorized list, without requiring code changes or restarts.
- **Extensibility:** Third-party developers and advanced users can add new node types (via plugins or scripts) that are automatically discoverable and usable in the UI.
- **UI Integration:** The node registry powers UI features such as context menus, palettes, and search bars, allowing users to browse, filter, and select node types based on categories, tags, or capabilities.
- **Consistency and Safety:** The registry ensures that only valid, compatible node types are available for creation, reducing errors and improving user confidence.
- **Documentation and Metadata:** Each node type can provide metadata (e.g., description, category, icon) to enhance discoverability and help users understand node functionality before adding it to the graph.

## User Stories
- As a user, I want to see all available node types in a searchable list, so I can quickly find and add the node I need.
- As a plugin developer, I want to register my custom node types so they appear in the UI alongside built-in nodes.
- As a power user, I want to categorize and tag nodes, so I can filter and organize them in large projects.
- As a new user, I want to see descriptions and icons for each node type, so I can understand what each node does before using it.

## Success Criteria
- Users can add any registered node type from the UI without restarting or editing code.
- New node types (from plugins or scripts) appear automatically in the UI after registration.
- The node registry supports metadata for each node type (name, description, category, icon, etc.).
- The system prevents duplicate or invalid node registrations.
- The registry is accessible to both the core application and extensions/plugins. 