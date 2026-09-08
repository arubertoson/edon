"""Regression coverage for icon copying and rendering."""

import pytest
from PySide6.QtCore import QRect, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

from edon_ui.icon_engine import FontIcon, FontIconEngine


@pytest.mark.parametrize("size", [None, QSize(16, 16)])
def test_clone_preserves_rendering(qapp: QApplication, size: QSize | None) -> None:
    engine: FontIconEngine = FontIconEngine("fa5s.expand", QColor("red"))
    engine.size = size
    cloned: FontIconEngine = engine.clone()
    assert cloned is not engine
    assert cloned.icon_name == engine.icon_name
    assert cloned.base_color == engine.base_color
    assert cloned.size == size
    original: QPixmap = engine.pixmap(QSize(32, 32), QIcon.Mode.Normal, QIcon.State.Off)
    copied: QPixmap = cloned.pixmap(QSize(32, 32), QIcon.Mode.Normal, QIcon.State.Off)
    assert not original.isNull()
    assert original.toImage() == copied.toImage()
    assert any(original.toImage().pixelColor(x, y).alpha() for x in range(32) for y in range(32))
    cloned.base_color.setBlue(255)
    assert cloned.base_color != engine.base_color
    if cloned.size is not None:
        cloned.size.setHeight(20)
        assert engine.size == QSize(16, 16)


def test_paint_preserves_supplied_rectangle(qapp: QApplication) -> None:
    engine: FontIconEngine = FontIconEngine("fa5s.expand")
    pixmap: QPixmap = QPixmap(32, 32)
    painter: QPainter = QPainter(pixmap)
    rect: QRect = QRect(0, 0, 32, 32)
    try:
        engine.paint(painter, rect, QIcon.Mode.Normal, QIcon.State.Off)
    finally:
        painter.end()
    assert rect == QRect(0, 0, 32, 32)


def test_icon_size_is_copied_and_font_uses_height(qapp: QApplication) -> None:
    icon: FontIcon = FontIcon("fa5s.expand")
    size: QSize = QSize(16, 18)
    icon.set_size(size)
    size.setHeight(30)
    assert icon.engine.size == QSize(16, 18)
    assert icon.font(QSize(16, 18)).pixelSize() == 18
