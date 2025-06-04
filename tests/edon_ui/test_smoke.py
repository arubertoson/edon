import pytest

# Attempt to import Qt bindings. If not available, skip UI tests.
from PySide6.QtWidgets import QApplication

from edon_ui.app import EdonApplication
from edon_ui.graph.controller import WorkspaceController
from edon_ui.views.scene import GraphicsScene
from edon_ui.views.viewer import GraphicsView
from edon_ui.views.window import MainWindow


@pytest.fixture(scope="session")
def qapp_instance():
    """Ensure a QApplication instance exists for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_edon_application_instantiates(qapp_instance, qtbot):
    """Tests that the main EdonApplication can be instantiated."""
    try:
        # EdonApplication might require node_registry, command_registry, key_mapping
        # Providing minimal valid instances or None if allowed by constructor
        app = EdonApplication(
            node_registry=None,  # Or a mock/empty registry
        )
        assert app is not None
    except Exception as e:
        pytest.fail(f"EdonApplication instantiation failed: {e}")


def test_main_window_instantiates(qapp_instance, qtbot):
    """Tests that the MainWindow can be instantiated."""
    try:
        controller = WorkspaceController()

        window = MainWindow(view=controller.view)
        qtbot.addWidget(window)
        assert window is not None
    except Exception as e:
        pytest.fail(f"MainWindow instantiation failed: {e}")


def test_graphics_view_instantiates(qapp_instance, qtbot):
    """Tests that GraphicsView can be instantiated."""
    try:
        controller = WorkspaceController()

        qtbot.addWidget(controller.view)

        assert controller.view is not None
        assert controller.scene is not None
    except Exception as e:
        pytest.fail(f"GraphicsView instantiation failed: {e}")
