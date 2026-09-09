from PySide6.QtWidgets import QGraphicsScene, QGraphicsView, QMainWindow
from pytestqt.qtbot import QtBot

from edon_ui.widgets.editors import CustomDialogWidget, ExpandLineEdit, ValueTextEdit
from edon_ui.widgets.factories import create_large_string_socket_component


def test_large_string_dialog_uses_proxy_scene_and_view_window(qtbot: QtBot) -> None:
    scene = QGraphicsScene()
    view = QGraphicsView(scene)
    window = QMainWindow()
    window.setCentralWidget(view)
    qtbot.addWidget(window)
    window.show()

    adaptor = create_large_string_socket_component("initial text", "node", "input")
    scene.addItem(adaptor)
    editor = adaptor.proxy.widget()
    assert isinstance(editor, ExpandLineEdit)

    editor._open_text_dialog()
    qtbot.wait(1)
    dialog = window.findChild(CustomDialogWidget)
    assert dialog is not None
    assert dialog.parentWidget() is window
    assert dialog.scene is scene
    assert dialog.isVisible()
    assert not view.isInteractive()

    content = dialog.findChild(ValueTextEdit)
    assert content is not None
    assert content.toPlainText() == "initial text"

    dialog.reject()
    assert view.isInteractive()
