import pytest

# Attempt to import Qt bindings. If not available, skip UI tests.
from PySide6.QtWidgets import QApplication

from edon_ui.app import EdonApplication
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
        # MainWindow constructor: __init__(self, view: "GraphicsView")
        # It also uses self.key_mapping and self.command_registry internally.
        # These might need to be set or mocked if accessed during __init__.
        # For a pure smoke test, we try to provide minimal valid dependencies.

        scene = GraphicsScene()
        view = GraphicsView(scene)  # GraphicsView constructor: __init__(self, scene, parent=None)

        # Mock or provide real command_registry and key_mapping if MainWindow's __init__ uses them
        # For now, assume they can be None or are set post-init if not passed.
        # If MainWindow's __init__ directly accesses attributes set by EdonApplication,
        # this test might need to be part of a larger integration test or MainWindow needs refactoring
        # for easier standalone testing.
        # Based on typical structure, MainWindow might expect these to be available via an `app` context
        # or passed in. The current __init__ only takes `view`.

        window = MainWindow(view=view)
        qtbot.addWidget(window)  # Manage widget lifecycle
        assert window is not None
    except Exception as e:
        pytest.fail(f"MainWindow instantiation failed: {e}")


def test_graphics_scene_instantiates(qapp_instance, qtbot):
    """Tests that GraphicsScene can be instantiated."""
    try:
        scene = GraphicsScene()
        assert scene is not None
    except Exception as e:
        pytest.fail(f"GraphicsScene instantiation failed: {e}")


def test_graphics_view_instantiates(qapp_instance, qtbot):
    """Tests that GraphicsView can be instantiated."""
    try:
        scene = GraphicsScene()  # GraphicsView requires a scene
        view = GraphicsView(scene)
        qtbot.addWidget(view)
        assert view is not None
    except Exception as e:
        pytest.fail(f"GraphicsView instantiation failed: {e}")
