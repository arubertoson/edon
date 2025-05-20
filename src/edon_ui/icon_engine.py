import sys
from loguru import logger
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QVBoxLayout
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QColor, QFont, QPixmap
from PySide6.QtCore import Qt, QRect, QSize, QPoint
import qtawesome as qta


def _get_qta_char_code(font_prefix):
    """
    Retrieves the integer Unicode character code for a qtawesome icon
    using the simpler qta.charmap().
    """
    try:
        char_map = qta.charmap(font_prefix)
        if char_map:
            logger.info(f"Char map for {font_prefix}: {char_map}")
            return char_map
        else:
            logger.warning(f"Warning: Char code not found for {font_prefix} using qta.charmap.")
    except Exception as e:
        logger.error(f"Error getting char code for {font_prefix} via qta.charmap: {e}")
        return None


class FontIconEngine(QIconEngine):
    """
    Custom QIconEngine that renders an icon from a qtawesome font character.
    """

    def __init__(self, full_icon_name: str, base_color: QColor = QColor("black")):
        super().__init__()
        self.icon_name = full_icon_name
        self.char_code = _get_qta_char_code(self.icon_name)
        self.base_color = QColor(base_color)  # Ensure it's a QColor copy

        self.prefix, self.char_key = self.icon_name.split(".")

    def paint(self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State):
        """
        Paints the icon character within the given rectangle.
        """
        if self.char_code is None:
            # Optionally draw a fallback placeholder if char_code is not found
            painter.save()
            painter.setPen(Qt.red)
            painter.drawText(rect, Qt.AlignCenter, "?")
            painter.restore()
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        if hasattr(self, "size"):
            point_size = self.size.height()
            logger.error(f"Icon size: {self.size}")
        else:
            # Determine font point size based on the target rectangle's height
            # Adjust the factor (e.g., 0.75) to get the desired relative icon size
            point_size = int(rect.height() * 0.8)
            if point_size < 6:  # Ensure a minimum sensible font size
                point_size = 6

        rect.setLeft(rect.left() - point_size - 4)

        try:
            # Get the QFont for the font family (prefix) and calculated size
            icon_qfont = qta.font(self.prefix, point_size)
        except Exception as e:
            logger.error(f"Error getting qta.font for prefix '{self.prefix}': {e}. Using fallback.")
            icon_qfont = QFont()  # Default system font
            icon_qfont.setPointSize(point_size)

        painter.setFont(icon_qfont)

        # Determine color based on icon mode
        current_color = QColor(self.base_color)  # Start with the base color

        if mode == QIcon.Mode.Disabled:
            # For disabled state, typically use a desaturated or semi-transparent color
            # Using QColor's HSL values to desaturate and lighten
            h, s, l, a = current_color.getHsl()
            current_color.setHsl(h, int(s * 0.3), min(255, l + 60), int(a * 0.6))
        elif mode == QIcon.Mode.Selected or mode == QIcon.Mode.Active:
            # For selected/active, make it slightly brighter or use a theme color
            # Here, we'll just make it a bit brighter if it's not too light already
            h, s, l, a = current_color.getHsl()
            if l < 230:  # Avoid making very light colors pure white
                current_color.setHsl(h, s, min(255, l + 25), a)
            # Alternatively, you could use QApplication.palette().highlight().color()
            # current_color = QApplication.palette().color(QPalette.ColorRole.Highlight)

        painter.setPen(current_color)
        painter.drawText(rect, Qt.AlignCenter, self.char_code)

        painter.restore()

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        """
        Returns a QPixmap rendering of the icon.
        This is essential for QIcon to work correctly in many contexts.
        """
        pm = QPixmap(size)
        pm.fill(Qt.transparent)  # Transparent background for the pixmap

        painter = QPainter(pm)
        # The rect for painting on the pixmap is its full bounds
        self.paint(painter, QRect(QPoint(0, 0), size), mode, state)
        painter.end()  # Crucial to end painter when drawing on QPixmap directly

        return pm

    def clone(self) -> QIconEngine:
        """
        Returns a new instance of this icon engine. Required by QIconEngine.
        """
        return FontIconEngine(self.full_icon_name, self.base_color)

    def virtual_hook(self, id, data):
        """
        Handles virtual hooks if any.
        """
        return super().virtual_hook(id, data)


class FontIcon(QIcon):
    """
    Custom QIcon that uses FontIconEngine to render icons from qtawesome fonts.
    """

    def __init__(self, full_icon_name: str, color: QColor = QColor("black"), parent=None):
        # Create an instance of our custom engine
        self.engine = FontIconEngine(full_icon_name, color)
        # Initialize QIcon with the custom engine
        super().__init__(self.engine)

    def font(self, size: QSize = QSize(24, 24)):
        return qta.font(self.engine.prefix, size)

    def set_size(self, size: QSize):
        self.engine.size = size

    def char(self):
        return self.engine.char_code


# --- Example Usage ---
class TestWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test FontIcon")
        layout = QVBoxLayout(self)

        # Create icons using the custom QtaFontIcon class
        icon_expand = FontIcon("fa5s.expand", QColor("dodgerblue"))
        icon_expand.set_size(QSize(32, 32))
        icon_user = FontIcon("fa5s.user-circle", QColor("green"))
        icon_cog_disabled = FontIcon("fa5s.cog", QColor("darkgray"))  # Base color for normal state
        icon_unknown = FontIcon("foo.bar")  # Test fallback for unknown icon

        # Create buttons and set icons
        button1 = QPushButton("Expand")
        button1.setIcon(icon_expand)
        button1.setIconSize(QSize(24, 24))  # QIcon will use engine to paint at this size
        layout.addWidget(button1)

        button2 = QPushButton("User")
        button2.setIcon(icon_user)
        button2.setIconSize(QSize(32, 32))
        layout.addWidget(button2)

        button3 = QPushButton("Settings (Disabled)")
        button3.setIcon(icon_cog_disabled)
        button3.setIconSize(QSize(48, 48))
        button3.setEnabled(False)  # This will trigger QIcon.Mode.Disabled
        layout.addWidget(button3)

        button4 = QPushButton("Unknown Icon")
        button4.setIcon(icon_unknown)
        button4.setIconSize(QSize(32, 32))
        layout.addWidget(button4)

        button5 = QPushButton("Selected State (Style Dependent)")
        # For selected state to show visually, the widget style must support it,
        # or you might need to handle it more explicitly if not a checkable button.
        button5.setCheckable(True)
        button5.setChecked(True)  # This can trigger QIcon.Mode.Selected or QIcon.Mode.On
        button5.setIcon(FontIcon("fa5s.check-square", QColor("purple")))
        button5.setIconSize(QSize(24, 24))
        layout.addWidget(button5)

        self.setLayout(layout)
        self.resize(300, 300)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # It's good practice to initialize qtawesome early,
    # though importing often does enough for basic use.
    # qta.init_resource() # If you're using its resource system

    test_widget = TestWidget()
    test_widget.show()
    sys.exit(app.exec())
