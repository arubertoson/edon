from PySide6.QtGui import QColor, QFont

# --- Primary Palette ---
COLOR_BACKGROUND_DARK = QColor("#2D2D2D")  # Dark grey, good for view/scene backgrounds
COLOR_BACKGROUND_MEDIUM = QColor("#6d6d6d") # Dark slate gray, from image node background
COLOR_BACKGROUND_LIGHT = QColor("#b0b0b0") # Lighter slate gray, from image input field background

COLOR_SURFACE = QColor("#4A4A4A")         # For surfaces on top of backgrounds (unused for now)

COLOR_TEXT_LIGHT = QColor("#D1D1D1")       # Light text for dark backgrounds (title, labels from image)
COLOR_TEXT_MEDIUM = QColor("#BBBBBB")      # Medium emphasis text (unused for now)
COLOR_TEXT_DARK = QColor("#202020")        # Dark text for light backgrounds (if you had them)
COLOR_TEXT_INPUT = QColor("#E0E0E0")       # Text inside input fields from image

# --- Accent Colors ---
ACCENT_PRIMARY = QColor("#FF6B6B")        # Red/coral for ports from image
ACCENT_SECONDARY = QColor("#7A81DD")      # A muted blue/purple, could be for selection or highlights
ACCENT_SUCCESS = QColor("#2ECC71")        # Green
ACCENT_WARNING = QColor("#F39C12")        # Orange
ACCENT_ERROR = QColor("#E74C3C")          # Red

# --- Node Specific (derived from image and palette) ---
NODE_BACKGROUND = COLOR_BACKGROUND_MEDIUM
NODE_BORDER_DEFAULT = NODE_BACKGROUND.lighter(110) # Subtle darker border
NODE_BORDER_SELECTED = QColor("#5F9FDF") # A distinct blue for selection
NODE_BORDER_RADIUS = 8.0
NODE_BORDER_WIDTH_DEFAULT = 1.5
NODE_BORDER_WIDTH_SELECTED = 2.0

NODE_HORIZONTAL_PADDING = 10.0 # Padding inside the node, before socket row content starts
NODE_MIN_WIDTH = 150.0         # Minimum overall width for a node
NODE_MIN_HEIGHT = 60.0         # Minimum overall height for a node

NODE_TITLE_BACKGROUND = COLOR_BACKGROUND_DARK.darker(200)
NODE_TITLE_TEXT = COLOR_TEXT_LIGHT
NODE_TITLE_HEIGHT = 35.0 # Adjusted to look like image

NODE_CONTENT_BACKGROUND = COLOR_BACKGROUND_LIGHT.lighter(110) # Background for input fields

NODE_LABEL_TEXT = COLOR_TEXT_LIGHT # For labels like "A", "B", "Use Cache"

NODE_PORT_COLOR = ACCENT_PRIMARY
NODE_PORT_RADIUS = 7.0

# --- Fonts (matching Segoe UI look if available, otherwise common sans-serif) ---
FONT_FAMILY_UI = "Segoe UI"
FONT_NODE_TITLE = QFont(FONT_FAMILY_UI, 10, QFont.Weight.DemiBold)
FONT_NODE_LABEL = QFont(FONT_FAMILY_UI, 9)
FONT_NODE_INPUT = QFont(FONT_FAMILY_UI, 9)
FONT_NODE_FOOTER = QFont(FONT_FAMILY_UI, 9)


# --- Grid Colors ---
GRID_COLOR_LIGHT = QColor(55, 55, 55) # Dots in the image background
GRID_COLOR_DARK = QColor(45, 45, 45)  # Not visible in image, but good for pattern

# --- Checkbox (can be styled further in QSS) ---
CHECKBOX_INDICATOR_CHECKED_BG = QColor("#4A90E2") # Blue from typical checkbox
CHECKBOX_TEXT = NODE_LABEL_TEXT

# --- SpinBox/Input Fields (can be styled further in QSS) ---
INPUT_BACKGROUND = COLOR_BACKGROUND_LIGHT
INPUT_TEXT_COLOR = COLOR_TEXT_INPUT
INPUT_BORDER_COLOR = COLOR_BACKGROUND_MEDIUM.darker(120)

# --- Scene Specific Backgrounds ---
SCENE_BACKGROUND = QColor(30, 30, 30) # Very dark gray for the furthest background
SCENE_ACTIVE_AREA_BACKGROUND = QColor(40, 40, 40) # Background for the area where nodes primarily reside
SCENE_ACTIVE_AREA_BORDER = QColor(1, 1, 1)     # Border for the active area

# Socket Colors
SOCKET_BORDER_COLOR = QColor("#FF000000") # Black
SOCKET_FILL_COLOR_DEFAULT = QColor("#FFAAAAAA") # Light Gray

# Colors per socket type (using string keys)
SOCKET_FILL_COLORS = {
    "default": QColor("#FFAAAAAA"), # Light Gray
    "integer": QColor("#FF007ACC"),  # Blue
    "float": QColor("#FF00A000"),   # Green
    "string": QColor("#FFFFA500"),  # Orange
    "boolean": QColor("#FFD60000"), # Red
    "trigger": QColor("#FFFFFFFF"),  # White (often used for execution flow)
    # Add more as needed
}

# Socket Properties
SOCKET_RADIUS = 6.0 # pixels
SOCKET_ROW_HEIGHT = 25.0 # Total vertical space for a socket row (for circle + label/widget)
SOCKET_PADDING = 5.0 # Padding around sockets for layout (e.g., above first socket row)
SOCKET_SPACING = 10.0 # Vertical spacing between socket visual elements (DEPRECATED if using ROW_HEIGHT consistently)
                        # We'll keep it for now but SOCKET_ROW_HEIGHT will be the primary driver for layout

# New theme constants
SOCKET_HOVER_FILL_COLOR = QColor("#FF0000") # Example: Bright red for hover
EDGE_Z_VALUE = -1 # For finalized connections (currently drawn below nodes)
EDGE_Z_VALUE_DRAGGING = 100 # For connections being actively dragged
EDGE_COLOR_DEFAULT = QColor("#F0F0F0") # Example: Light gray/white
EDGE_THICKNESS = 2.0
EDGE_COLOR_SELECTED = QColor("#FF0000") # Example: Bright red for selected