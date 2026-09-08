"""Resize hit testing and native-resize request lifecycle."""

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWindow
from pytestqt.qtbot import QtBot

from edon_ui.graph.controller import WorkspaceController
from edon_ui.views.window import MainWindow


@pytest.fixture
def window(qtbot: QtBot) -> MainWindow:
    controller: WorkspaceController = WorkspaceController()
    window: MainWindow = MainWindow(controller.view)
    qtbot.addWidget(window)
    window.resize(400, 300)
    return window


@pytest.mark.parametrize(
    "position, expected",
    [
        (QPoint(200, 150), Qt.Edge(0)),
        (QPoint(-1, 150), Qt.Edge(0)),
        (QPoint(0, 150), Qt.Edge.LeftEdge),
        (QPoint(399, 150), Qt.Edge.RightEdge),
        (QPoint(200, 0), Qt.Edge.TopEdge),
        (QPoint(200, 299), Qt.Edge.BottomEdge),
        (QPoint(0, 0), Qt.Edge.LeftEdge | Qt.Edge.TopEdge),
        (QPoint(399, 299), Qt.Edge.RightEdge | Qt.Edge.BottomEdge),
    ],
)
def test_resize_hit_testing(window: MainWindow, position: QPoint, expected: Qt.Edge) -> None:
    assert window._detect_edge(position) == expected
    global_position: QPointF = QPointF(window.mapToGlobal(position))
    assert window.is_position_on_resize_edge(global_position) == bool(expected)


@pytest.mark.parametrize("accepted", [True, False])
def test_resize_request_and_release(
    window: MainWindow,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
    accepted: bool,
) -> None:
    requested: list[Qt.Edge] = []

    def start_resize(handle: QWindow, edges: Qt.Edge) -> bool:
        requested.append(edges)
        return accepted

    monkeypatch.setattr(QWindow, "startSystemResize", start_resize)
    window.show()
    qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(200, 150))
    assert not requested
    qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(200, 150))
    qtbot.mousePress(window, Qt.MouseButton.LeftButton, pos=QPoint(1, 150))
    assert requested == [Qt.Edge.LeftEdge]
    assert window._resizing is accepted
    assert window._resize_edge == (Qt.Edge.LeftEdge if accepted else Qt.Edge(0))
    qtbot.mouseRelease(window, Qt.MouseButton.LeftButton, pos=QPoint(1, 150))
    assert not window._resizing
    assert window._resize_edge == Qt.Edge(0)
