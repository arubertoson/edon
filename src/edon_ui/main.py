import sys
from PySide6.QtWidgets import QApplication
from edon_ui.window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load the stylesheet
    try:
        with open("src/edon_ui/styles/main_style.qss", "r") as f:
            stylesheet = f.read()
        app.setStyleSheet(stylesheet)
    except FileNotFoundError:
        print("Warning: src/edon_ui/styles/main_style.qss not found. Using default styles.")
    except Exception as e:
        print(f"Error loading stylesheet: {e}")

    window = MainWindow()
    window.show()

    sys.exit(app.exec()) 