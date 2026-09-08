"""Application ownership and basic widget construction checks."""

import os
import subprocess
import sys
from collections.abc import Callable
from types import TracebackType

import pytest
from PySide6.QtCore import QMessageLogContext, QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from edon_ui.app import EdonApplication
from edon_ui.graph.controller import WorkspaceController
from edon_ui.views.window import MainWindow


def test_edon_application_reuses_host(qapp: QApplication, qtbot: QtBot) -> None:
    original_stylesheet: str = qapp.styleSheet()
    original_hook: Callable[[type[BaseException], BaseException, TracebackType | None], object] = (
        sys.excepthook
    )

    def host_message_handler(
        message_type: QtMsgType,
        context: QMessageLogContext,
        message: str,
    ) -> None:
        return None

    previous_handler: object = qInstallMessageHandler(host_message_handler)
    try:
        app: EdonApplication = EdonApplication()
        qtbot.addWidget(app.main_window)
        assert app._qt_app is qapp
        assert QApplication.instance() is qapp
        assert sys.excepthook is original_hook
        assert qapp.styleSheet() == original_stylesheet
        assert app.main_window.styleSheet()
        installed_handler: object = qInstallMessageHandler(host_message_handler)
        assert installed_handler is host_message_handler
    finally:
        qInstallMessageHandler(previous_handler)


def test_hosted_run_does_not_start_event_loop(
    qapp: QApplication,
    qtbot: QtBot,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_exec() -> int:
        pytest.fail("A hosted Edon window must not start another Qt event loop")

    monkeypatch.setattr(QApplication, "exec", unexpected_exec)
    app: EdonApplication = EdonApplication()
    qtbot.addWidget(app.main_window)
    assert app.run() == 0
    assert app.main_window.isVisible()
    app.main_window.close()
    assert QApplication.instance() is qapp
    assert not app.main_window.isVisible()


def test_multiple_edon_windows_share_host(qapp: QApplication, qtbot: QtBot) -> None:
    first: EdonApplication = EdonApplication()
    second: EdonApplication = EdonApplication()
    qtbot.addWidget(first.main_window)
    qtbot.addWidget(second.main_window)
    assert first._qt_app is second._qt_app is qapp
    assert first.main_window is not second.main_window


def test_standalone_application_owns_event_loop() -> None:
    script: str = """
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from edon_ui.app import EdonApplication, EdonLoggingApplication

assert QApplication.instance() is None
app: EdonApplication = EdonApplication()
assert isinstance(QApplication.instance(), EdonLoggingApplication)
QTimer.singleShot(0, lambda: QApplication.exit(7))
assert app.run() == 7
assert app.main_window.isVisible()
app.main_window.close()
"""
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_non_widget_qt_application_is_rejected() -> None:
    script: str = """
from PySide6.QtCore import QCoreApplication
from edon_ui.app import EdonApplication

host: QCoreApplication = QCoreApplication([])
try:
    EdonApplication()
except RuntimeError as error:
    assert "Edon requires QApplication" in str(error)
else:
    raise AssertionError("A QCoreApplication cannot host widgets")
assert QCoreApplication.instance() is host
"""
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        [sys.executable, "-c", script],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_main_window_instantiates(qtbot: QtBot) -> None:
    controller: WorkspaceController = WorkspaceController()
    window: MainWindow = MainWindow(view=controller.view)
    qtbot.addWidget(window)
    assert controller.view.window() is window


def test_graphics_view_instantiates(qtbot: QtBot) -> None:
    controller: WorkspaceController = WorkspaceController()
    qtbot.addWidget(controller.view)
    assert controller.view.scene() is controller.scene
