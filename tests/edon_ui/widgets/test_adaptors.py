from unittest.mock import patch

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QLabel, QStyleOptionGraphicsItem
from pytestqt.qtbot import QtBot

from edon_ui.widgets.adaptors import SocketTextAdaptor, SocketWidgetAdaptor
from edon_ui.widgets.gfx import SocketLabel


@pytest.mark.parametrize("kind", ["text", "widget"])
def test_adaptor_paint_is_intentionally_empty(qtbot: QtBot, kind: str) -> None:
    adaptor = (
        SocketTextAdaptor(SocketLabel("Socket", 24.0))
        if kind == "text"
        else SocketWidgetAdaptor(QLabel("Socket"))
    )
    image = QImage(100, 40, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    original = image.copy()
    painter = QPainter(image)
    try:
        with patch("edon_ui.base.logger.critical") as critical:
            adaptor.paint(painter, QStyleOptionGraphicsItem())
            critical.assert_not_called()
    finally:
        painter.end()

    assert image == original
    assert len(adaptor.childItems()) == 1
    assert not adaptor.boundingRect().isEmpty()
