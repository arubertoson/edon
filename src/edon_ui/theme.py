from PySide6.QtGui import QColor, QFont

# --- Primary Palette ---
COLOR_BACKGROUND_DARK = QColor("#2D2D2D")  # Dark grey, good for view/scene backgrounds
COLOR_BACKGROUND_MEDIUM = QColor("#6d6d6d")  # Dark slate gray, from image node background
COLOR_BACKGROUND_LIGHT = QColor("#b0b0b0")  # Lighter slate gray, from image input field background

COLOR_SURFACE = QColor("#4A4A4A")  # For surfaces on top of backgrounds (unused for now)

COLOR_TEXT_LIGHT = QColor("#D1D1D1")  # Light text for dark backgrounds (title, labels from image)
COLOR_TEXT_MEDIUM = QColor("#BBBBBB")  # Medium emphasis text (unused for now)
COLOR_TEXT_DARK = QColor("#202020")  # Dark text for light backgrounds (if you had them)
COLOR_TEXT_INPUT = QColor("#E0E0E0")  # Text inside input fields from image

# --- Accent Colors ---
ACCENT_PRIMARY = QColor("#FF6B6B")  # Red/coral for ports from image
ACCENT_SECONDARY = QColor("#7A81DD")  # A muted blue/purple, could be for selection or highlights
ACCENT_SUCCESS = QColor("#2ECC71")  # Green
ACCENT_WARNING = QColor("#F39C12")  # Orange
ACCENT_ERROR = QColor("#E74C3C")  # Red

# --- Node Specific (derived from image and palette) ---
NODE_BACKGROUND = QColor("#4A4A4A")
SUBGRAPH_NODE_BACKGROUND = QColor("#3E505B")  # Distinct background for SubGraphNode instances
NODE_BORDER_DEFAULT = NODE_BACKGROUND.lighter(110)  # Subtle darker border
NODE_BORDER_SELECTED = QColor("#5F9FDF")  # A distinct blue for selection
NODE_BORDER_RADIUS = 4.0
NODE_BORDER_WIDTH_DEFAULT = 1.5
NODE_BORDER_WIDTH_SELECTED = 2.0

NODE_HORIZONTAL_PADDING = 10.0  # Padding inside the node, before socket row content starts
NODE_MIN_WIDTH = 125.0  # Minimum overall width for a node
NODE_MIN_HEIGHT = 60.0  # Minimum overall height for a node

NODE_TITLE_BACKGROUND = COLOR_BACKGROUND_DARK.darker(200)
NODE_TITLE_TEXT = COLOR_TEXT_LIGHT
NODE_TITLE_HEIGHT = 25.0  # Adjusted to look like image

NODE_CONTENT_BACKGROUND = COLOR_BACKGROUND_LIGHT.lighter(110)  # Background for input fields

NODE_LABEL_TEXT = COLOR_TEXT_LIGHT  # For labels like "A", "B", "Use Cache"

NODE_PORT_COLOR = ACCENT_PRIMARY
NODE_PORT_RADIUS = 7.0

# --- Fonts (matching Segoe UI look if available, otherwise common sans-serif) ---
FONT_FAMILY_UI = "Segoe UI"
FONT_NODE_TITLE = QFont(FONT_FAMILY_UI, 8, QFont.Weight.DemiBold)
FONT_NODE_LABEL = QFont(FONT_FAMILY_UI, 9)
FONT_NODE_INPUT = QFont(FONT_FAMILY_UI, 9)
FONT_NODE_FOOTER = QFont(FONT_FAMILY_UI, 9)


# --- Grid Colors ---
GRID_COLOR_LIGHT = QColor(55, 55, 55)  # Dots in the image background
GRID_COLOR_DARK = QColor(45, 45, 45)  # Not visible in image, but good for pattern

# --- Checkbox (can be styled further in QSS) ---
CHECKBOX_INDICATOR_CHECKED_BG = QColor("#4A90E2")  # Blue from typical checkbox
CHECKBOX_TEXT = NODE_LABEL_TEXT

# --- SpinBox/Input Fields (can be styled further in QSS) ---
INPUT_BACKGROUND = COLOR_BACKGROUND_LIGHT
INPUT_TEXT_COLOR = COLOR_TEXT_INPUT
INPUT_BORDER_COLOR = COLOR_BACKGROUND_MEDIUM.darker(120)

# --- Scene Specific Backgrounds ---
SCENE_BACKGROUND = QColor(30, 30, 30)  # Very dark gray for the furthest background
SCENE_ACTIVE_AREA_BACKGROUND = QColor(
    40, 40, 40
)  # Background for the area where nodes primarily reside
SCENE_ACTIVE_AREA_BORDER = QColor(1, 1, 1)  # Border for the active area

# Socket Colors
SOCKET_BORDER_COLOR = QColor("#FF000000")  # Black
SOCKET_FILL_COLOR_DEFAULT = QColor("#FFAAAAAA")  # Light Gray

# Colors per socket type (using string keys)
SOCKET_FILL_COLORS = {
    "default": QColor("#FFAAAAAA"),  # Light Gray
    "number": QColor("#FF007ACC"),  # Blue
    "integer": QColor("#FF0055FF"),  # Bright Blue
    "float": QColor("#FF00BFFF"),  # Sky Blue
    "string": QColor("#FFFFA500"),  # Orange
    "boolean": QColor("#FFD60000"),  # Red
    "vector": QColor("#FF00C853"),  # Green
    "color": QColor("#FFFF4081"),  # Pink
    "matrix": QColor("#FF8D6E63"),  # Brown
    "image": QColor("#FF7C4DFF"),  # Purple
    "audio": QColor("#FF00B8D4"),  # Cyan
    "object": QColor("#FFB0BEC5"),  # Gray Blue
    "event": QColor("#FFFFFFFF"),  # White
    "enum": QColor("#FF9E9D24"),  # Olive
    "array": QColor("#FF6D4C41"),  # Deep Brown
    "resource": QColor("#FF8BC34A"),  # Light Green
    "time": QColor("#FFFFEB3B"),  # Yellow
    "angle": QColor("#FFFF7043"),  # Deep Orange
    "curve": QColor("#FFAB47BC"),  # Violet
    "path": QColor("#FF607D8B"),  # Blue Gray
    "data": QColor("#FF263238"),  # Dark Gray
    "custom": QColor("#FF00E676"),  # Neon Green
}

# Socket Properties
SOCKET_RADIUS = 6.0  # pixels
SOCKET_ROW_HEIGHT = 20.0  # Total vertical space for a socket row (for circle + label/widget)
SOCKET_PADDING = 5.0  # Padding around sockets for layout (e.g., above first socket row)
SOCKET_SPACING = 10.0  # Vertical spacing between socket visual elements (DEPRECATED if using ROW_HEIGHT consistently)
# We'll keep it for now but SOCKET_ROW_HEIGHT will be the primary driver for layout

# New theme constants
SOCKET_HOVER_FILL_COLOR = QColor("#FF0000")  # Example: Bright red for hover
EDGE_Z_VALUE = -1  # For finalized connections (currently drawn below nodes)
EDGE_Z_VALUE_DRAGGING = 100  # For connections being actively dragged
EDGE_COLOR_DEFAULT = QColor("#F0F0F0")  # Example: Light gray/white
EDGE_THICKNESS = 2.0
EDGE_COLOR_SELECTED = QColor("#FF0000")  # Example: Bright red for selected

EDGE_THICKNESS_DRAGGING = EDGE_THICKNESS
EDGE_COLOR_DRAGGING = EDGE_COLOR_DEFAULT

INPUT_BORDER_RADIUS = 4.0
INPUT_BACKGROUND_COLOR = QColor("#FF000000")  # Black
INPUT_TEXT_COLOR = QColor("#FFFFFFFF")  # White

# Add these lines (if not already present)
SOCKET_HORIZONTAL_PADDING = 4.0
SOCKET_VERTICAL_ITEM_PADDING = 2.0
SOCKET_VERTICAL_CONTENT_MARGIN = 4.0
SOCKET_CIRCLE_SPACING = 8.0
SOCKET_ITEM_FIXED_WIDTH = 70.0
SOCKET_ITEM_VERTICAL_MARGIN = 4.0
NODE_MIN_CONTENT_HEIGHT = 20.0

# For QLineEdit based input widgets in sockets
INPUT_WIDGET_BACKGROUND_COLOR = COLOR_BACKGROUND_MEDIUM  # A medium-dark gray
INPUT_WIDGET_TEXT_COLOR = QColor("#E0E0E0")  # Light gray for text
INPUT_WIDGET_BORDER_COLOR = QColor("#606060")  # Border for the input widget
INPUT_WIDGET_BORDER_RADIUS = 2  # Integer for rounded corners
INPUT_WIDGET_PADDING = 2  # Internal padding for QLineEdit

# Widths for the SocketWidgetAdaptor (total width including its margins)
SOCKET_INTEGER_WIDGET_ADAPTOR_WIDTH = 70.0
SOCKET_FLOAT_WIDGET_ADAPTOR_WIDTH = 70.0
SOCKET_STRING_WIDGET_ADAPTOR_WIDTH = 100.0  # Strings often need more space

# Horizontal margin for the SocketWidgetAdaptor itself
# This is the space the adaptor adds *around* the QLineEdit
# SOCKET_WIDGET_ADAPTOR_HORIZONTAL_MARGIN = getattr(
#     theme, "SOCKET_HORIZONTAL_PADDING", 2.0
# )  # Default to existing socket padding

# For SocketLabel text
SOCKET_LABEL_TEXT_COLOR = QColor("#B0B0B0")  # A slightly dimmer gray for socket labels
FONT_SOCKET_LABEL_DEFAULT_SIZE = 9  # Default font size for socket labels (adjust as needed)

# Default Colors for Icons
ICON_COLOR = "#C0C0C0"  # Light gray for icons
ICON_COLOR_ACTIVE = "#FFFFFF"  # White for active/hovered icons

# Default Colors for Text Inputs
INPUT_TEXT_DISABLED_COLOR = "#808080"  # Medium gray for disabled input text

# --- Global Application Stylesheet ---
# This is where we'll define QSS rules for the entire application.
# We'll use f-strings to embed theme constants directly into the stylesheet.

APPLICATION_STYLESHEET = f"""
/* === QLineEdit === */
QLineEdit {{
    background-color: {INPUT_WIDGET_BACKGROUND_COLOR.name()};
    color: {INPUT_WIDGET_TEXT_COLOR.name()};
    border: 1px solid {INPUT_WIDGET_BORDER_COLOR.name()};
    border-radius: {INPUT_WIDGET_BORDER_RADIUS}px;
    padding: {INPUT_WIDGET_PADDING}px;
    selection-background-color: {ACCENT_SECONDARY.name()};
    selection-color: {COLOR_TEXT_LIGHT.name()}; /* For selected text color */
}}

QLineEdit:focus {{
    border-color: {NODE_BORDER_SELECTED.name()}; /* Highlight border on focus */
}}

/* === QPushButton (Placeholder - customize as needed) === */
QPushButton {{
    background-color: {ACCENT_PRIMARY.name()};
    color: {COLOR_TEXT_LIGHT.name()};
    border-radius: {INPUT_BORDER_RADIUS}px;
    padding: 5px 10px;
    border: 1px solid {ACCENT_PRIMARY.darker(120).name()};
}}

QPushButton:hover {{
    background-color: {ACCENT_PRIMARY.lighter(120).name()};
}}

QPushButton:pressed {{
    background-color: {ACCENT_PRIMARY.darker(130).name()};
}}

/* === QCheckBox (Placeholder - customize as needed) === */
QCheckBox {{
    spacing: 5px; /* Space between indicator and text */
    color: {CHECKBOX_TEXT.name()};
}}

QCheckBox::indicator {{
    width: 13px;
    height: 13px;
    border-radius: 3px;
    border: 1px solid {INPUT_BORDER_COLOR.name()};
    background-color: {INPUT_BACKGROUND.name()};
}}

QCheckBox::indicator:checked {{
    background-color: {CHECKBOX_INDICATOR_CHECKED_BG.name()};
    border: 1px solid {CHECKBOX_INDICATOR_CHECKED_BG.darker(120).name()};
    image: url(none); /* Remove default checkmark if you want to use a custom one or none */
}}

QCheckBox::indicator:unchecked:hover {{
    border-color: {NODE_BORDER_SELECTED.name()};
}}

QCheckBox::indicator:checked:hover {{
    background-color: {CHECKBOX_INDICATOR_CHECKED_BG.lighter(120).name()};
    border-color: {CHECKBOX_INDICATOR_CHECKED_BG.darker(130).name()};
}}

/* Add more global styles here for other widgets or custom items by class name */

"""
