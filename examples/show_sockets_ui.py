import sys
import os

# Adjust path to import from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from PySide6.QtWidgets import QApplication
# QGraphicsView is not directly used here anymore, MainWindow handles it.
# from PySide6.QtGui import QPainter # Not directly used here anymore

# GraphicsScene is also not directly instantiated here, MainWindow creates it.
# from edon_ui.graphics_scene import GraphicsScene
from edon_ui.node import NodeItem
from edon_ui.window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load the stylesheet (similar to main.py)
    # Assuming styles/main_style.qss is relative to src/edon_ui/
    # and this example is run from the project root.
    stylesheet_path = os.path.join(src_path, "edon_ui", "styles", "main_style.qss")
    try:
        with open(stylesheet_path, "r") as f:
            stylesheet = f.read()
        app.setStyleSheet(stylesheet)
    except FileNotFoundError:
        print(f"Warning: Stylesheet not found at {stylesheet_path}. Using default styles.")
    except Exception as e:
        print(f"Error loading stylesheet: {e}")

    # Create the main window
    main_window = MainWindow()

    # Access the scene from the MainWindow
    scene_from_main_window = main_window.scene
    # Alternatively, could be main_window.canvas.scene() if scene wasn't a direct attribute

    # Create a NodeItem instance
    # The NodeItem's __init__ now creates placeholder SocketItems
    node1 = NodeItem(title="Test Node in MainWindow", x=100, y=100)  # Adjusted position for better visibility

    # Add the node to the scene managed by MainWindow
    scene_from_main_window.addItem(node1)

    # Show the main window
    main_window.show()

    sys.exit(app.exec())
