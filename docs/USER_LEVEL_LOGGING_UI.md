# User-Level Logging in the UI

## Motivation

Currently, all logs—including errors and command/hotkey failures—are only visible in the console or log files. For a better user experience, especially for non-technical users or in production deployments, it is important to surface relevant log messages directly in the application's UI. This will help users understand why an action failed (e.g., a hotkey or command did not work) and provide immediate feedback without requiring access to the console.

## Requirements

- Display user-relevant log messages (errors, warnings, info) in the UI.
- When a command or hotkey fails, show a clear message to the user explaining why.
- Allow users to view a history of recent log messages (e.g., in a panel or popup).
- Optionally, allow filtering by log level (error, warning, info).
- Integrate with the existing logging system (Loguru) so that messages are not duplicated or lost.
- For now, logs are still visible in the console/terminal; this feature is an enhancement for the UI.

## Possible Approaches

### 1. Log Handler/Listener for the UI
- Implement a custom Loguru handler that emits log messages to the UI (e.g., via a Qt signal).
- The handler can filter messages by level and format them for display.
- The UI can subscribe to these signals and display messages in a dedicated widget (e.g., a status bar, notification popup, or log panel).

### 2. Status Bar or Notification System
- For immediate feedback (e.g., command failure), display a brief message in the status bar or as a toast/notification popup.
- For persistent logs, provide a log/history panel accessible from the main window.

### 3. Command/Hotkey Integration
- When a command or hotkey fails (returns False or raises an exception), log a user-level error and trigger a UI notification.
- Optionally, provide more detailed error information on demand (e.g., expandable details in the log panel).

## Integration Points

- The logging system (Loguru) should remain the single source of truth for all logs.
- The UI should subscribe to user-level log events (e.g., via a custom handler or signal).
- Command and hotkey execution paths should log user-facing errors with clear, actionable messages.
- The feature should be optional and not interfere with existing console/file logging.

## Next Steps

- Prototype a custom Loguru handler that emits Qt signals for user-level logs.
- Design a simple log display widget (status bar, popup, or panel).
- Integrate the handler and widget, and update command/hotkey code to log user-facing errors appropriately.

---

*For now, users should run the application with the console/terminal open to see log messages. This document outlines a future enhancement to improve user feedback and error visibility within the UI itself.* 