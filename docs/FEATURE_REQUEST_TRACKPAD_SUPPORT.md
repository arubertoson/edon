# PRD: Trackpad Support for Node Editor

## 1. Introduction

*   **Problem:** The current node editor primarily relies on mouse-specific interactions (e.g., middle-mouse button for panning, scroll wheel for zooming). This can be cumbersome for users on laptops or those who prefer using a trackpad, potentially hindering workflow efficiency and ease of use.
*   **Goal:** To enhance the usability and accessibility of the node editor by providing intuitive, smooth, and responsive trackpad-based navigation controls for panning and zooming the canvas, making the application more ergonomic for a wider range of users and input devices.

## 2. Goals

*   Enable fluid and natural panning of the node editor canvas using a two-finger drag gesture on a trackpad.
*   Enable intuitive zooming of the node editor canvas using a two-finger pinch gesture on a trackpad.
*   Ensure trackpad interactions are smooth, responsive, and consistent with standard trackpad behaviors experienced in other modern graphical applications.
*   Maintain full compatibility and harmonious coexistence with existing mouse-based navigation controls.
*   Improve the overall user experience for individuals using trackpads as their primary pointing device.

## 3. User Stories

*   **US1:** As a laptop user, I want to pan the canvas by dragging with two fingers on my trackpad, so I can easily navigate large graphs without needing an external mouse or awkward mouse button combinations.
*   **US2:** As a trackpad user, I want to zoom in and out of the canvas using a pinch gesture (spreading fingers apart to zoom in, pinching fingers together to zoom out), so I can quickly adjust my view of the graph details or get an overview of the entire structure.
*   **US3:** As a user, I want the trackpad zoom to be centered on my cursor position (or the midpoint of my fingers if cursor position is not feasible), so the view magnifies the area I am currently focusing on.
*   **US4:** As a user, I want the trackpad gestures to feel smooth and responsive, without lag or jitter, providing a high-quality interactive experience.
*   **US5:** As a user, I want to be able to use both trackpad gestures and traditional mouse controls (if a mouse is connected) without them interfering with each other.

## 4. Functional Requirements

### FR1: Two-Finger Pan
*   **FR1.1:** The canvas shall pan in the direction corresponding to a two-finger drag gesture on the trackpad.
*   **FR1.2:** Panning shall be continuous and update in real-time as the user moves their fingers.
*   **FR1.3:** Panning speed/sensitivity should feel natural and comfortable by default.
*   **FR1.4:** Panning should respect the boundaries of the scene if applicable, similar to existing pan behavior.

### FR2: Pinch-to-Zoom
*   **FR2.1:** The canvas shall zoom in when two fingers are spread apart (pinch out) on the trackpad.
*   **FR2.2:** The canvas shall zoom out when two fingers are brought closer together (pinch in) on the trackpad.
*   **FR2.3:** Zooming operations shall be centered at the current mouse cursor position over the view. If the cursor is outside the view, or if this is technically challenging, zooming can be centered at the midpoint of the pinch gesture.
*   **FR2.4:** Zooming shall be continuous and update in real-time with the pinch gesture.
*   **FR2.5:** Zoom speed/sensitivity should feel natural and allow for fine-grained control as well as quick large-scale zooms.
*   **FR2.6:** The existing zoom limits (minimum and maximum zoom levels) defined for mouse wheel zoom shall be respected by trackpad zoom.
*   **FR2.7:** Scene rect adjustment logic (`_request_scene_rect_adjustment`) should be triggered after zooming to ensure the scene boundaries are updated correctly.

### FR3: Configuration (Optional - Desirable for future enhancement)
*   **FR3.1:** Provide an option in application settings to enable/disable trackpad-specific gestures (pan and zoom, possibly independently).
*   **FR3.2:** Allow users to adjust the sensitivity for two-finger panning.
*   **FR3.3:** Allow users to adjust the sensitivity for pinch-to-zoom.
*   **FR3.4:** (Consider) Allow users to invert the direction for two-finger panning (e.g., "natural" vs. "traditional" scrolling direction).
*   **FR3.5:** (Consider) Allow users to invert the direction for pinch-to-zoom.

## 5. Non-Functional Requirements

*   **NFR1: Performance:** Trackpad interactions must be performant, not introducing noticeable lag, stuttering, or increased CPU/GPU load, even with complex scenes. The current rendering performance should not be negatively impacted.
*   **NFR2: Responsiveness:** Visual feedback for panning and zooming via trackpad must be immediate and feel directly connected to the user's gestures.
*   **NFR3: Compatibility:**
    *   The feature must work reliably on major desktop operating systems supported by Qt/PySide6 (Windows, macOS, Linux) that have standard trackpad drivers.
    *   The implementation should leverage Qt's built-in gesture or high-precision wheel event handling where possible (e.g., `QWheelEvent::pixelDelta()` for precision panning/zooming, `QWheelEvent::phase()` for gesture start/update/end).
*   **NFR4: Coexistence with Mouse Controls:** Trackpad gestures must not interfere with existing mouse-based navigation (e.g., middle-mouse pan, scroll-wheel zoom). Both input methods should function harmoniously and independently.
*   **NFR5: Smoothness:** Panning and zooming actions should be visually smooth. Abrupt or jerky movements must be avoided. If feasible, employ minor easing or animation to enhance the feel.
*   **NFR6: Standard Behavior:** The feel and behavior of trackpad pan and zoom should be generally consistent with what users expect from other graphical applications on their respective operating systems (e.g., web browsers, image editors, mapping applications).
*   **NFR7: No Interference with Item Interaction:** Trackpad gestures for view navigation should not unintentionally trigger actions on graphics items within the scene (e.g., selecting or moving nodes) unless that is the intended combined behavior (e.g., a pinch gesture over an item could potentially have a specific meaning for that item in the future, but view navigation should take precedence if the gesture is ambiguous or generic).

## 6. Out of Scope (for initial release)

*   Advanced multi-touch gestures beyond two-finger pan and pinch-to-zoom (e.g., three-finger swipes for history navigation, rotation gestures).
*   Haptic feedback related to trackpad interactions.
*   User-defined custom trackpad gestures.
*   Highly device-specific tuning or calibration UIs beyond what the OS/drivers provide (rely on Qt's abstraction).

## 7. Success Metrics

*   **SM1:** Positive qualitative feedback from users, especially those on laptops, indicating an improved and more intuitive navigation experience.
*   **SM2:** An observable increase in the use of pan/zoom functionalities by users who are identified or presumed to be using trackpads.
*   **SM3:** A reduction in user-reported difficulties or frustrations related to canvas navigation on devices primarily using trackpads.
*   **SM4:** Successful and consistent behavior across target operating systems (Windows, macOS, Linux) during testing.

## 8. Technical Considerations & Questions for Engineering

*   **TC1: Event Handling in Qt/PySide6:**
    *   How does Qt (`PySide6`) interpret and deliver trackpad gestures on different platforms? Specifically, are two-finger pans and pinches consistently translated into `QWheelEvent`s?
    *   Investigate `QWheelEvent` attributes: `angleDelta()` (for traditional wheel mice), `pixelDelta()` (for high-resolution mice and trackpad scrolling/panning), and `phase()` (`Qt.ScrollPhase` enum: `ScrollBegin`, `ScrollUpdate`, `ScrollEnd`, `ScrollMomentum`) to manage gesture lifecycle.
    *   Are `QNativeGestureEvent` or `QTouchEvent` necessary or more appropriate for certain platforms or finer control, or can `QWheelEvent` suffice?
*   **TC2: Distinguishing Trackpad from Mouse Wheel:**
    *   If both trackpad gestures and mouse wheel events generate `QWheelEvent`s, how can the application reliably distinguish their source or intent to apply different sensitivity or behavior if needed? (e.g., checking `event.source()` or other event properties). For the initial implementation, it might be acceptable if they are treated similarly, as long as the experience is good for both.
*   **TC3: Integration with `GraphicsView.py`:**
    *   How will the new trackpad handling logic integrate into the existing `wheelEvent` method in `GraphicsView.py`?
    *   Panning via trackpad (likely horizontal and vertical `pixelDelta` from `QWheelEvent`) needs to be integrated. The current `mouseMoveEvent` handles middle-mouse panning.
*   **TC4: Zoom Centering:**
    *   Confirm that `setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)` correctly handles zoom centering for trackpad-generated zoom events.
*   **TC5: Smoothness Implementation:**
    *   Explore options for ensuring smooth visual transitions during pan and zoom. This might involve interpolating values or using Qt's animation framework subtly if direct event values are too coarse.
*   **TC6: Testing:**
    *   What is the testing strategy across different operating systems (macOS, Windows, various Linux distributions/desktop environments) and different trackpad hardware (e.g., Apple Magic Trackpad, various laptop built-in trackpads)?

## 9. Future Considerations

*   Rotation gesture for rotating the view or selected items.
*   Support for three-finger gestures for other commands (e.g., undo/redo, opening a tool palette). 