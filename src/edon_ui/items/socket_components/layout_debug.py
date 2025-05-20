# Copyright (c) 2016-2023 Paul Walmsley and others
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy, QWidget, QLayoutItem, QWidgetItem, QSpacerItem, QBoxLayout


def _size_policy_to_string(policy: QSizePolicy):
    return f"({policy.horizontalPolicy().name}, {policy.verticalPolicy().name})"


def _get_widget_info(w: QWidget) -> str:
    geom = w.geometry()
    hint = w.sizeHint()
    hidden_str = "" if w.isVisible() else " **HIDDEN**"
    return (
        f"{w.metaObject().className()} {w.winId()} ({w.objectName()}), "
        f"pos ({geom.x()}, {geom.y()}), size ({geom.width()} x {geom.height()}), "
        f"hint ({hint.width()} x {hint.height()}) policy: {_size_policy_to_string(w.sizePolicy())}{hidden_str}"
    )


def _get_spacer_item_info(si: QSpacerItem):
    layout = si.layout()
    hint = si.sizeHint()
    return (
        f" SpacerItem hint ({hint.width()} x {hint.height()}) "
        f"policy: {_size_policy_to_string(si.sizePolicy())} "
        f"constraint: {si.layout().sizeConstraint().name}"
    )


def _get_layout_item_info(item: QLayoutItem):
    if isinstance(item, QWidgetItem):
        return _get_widget_info(item.widget())
    elif isinstance(item, QSpacerItem):
        return _get_spacer_item_info(item)
    else:
        return ""


def _print_widget_and_children(w: QWidget, level: int = 1):
    padding = ""
    for _ in range(level):
        padding += " "

    layout = w.layout()
    dumped_children = []
    if layout is not None and not layout.isEmpty():
        margins = layout.contentsMargins()
        margins_str = f"margin({margins.left()},{margins.top()},{margins.right()},{margins.bottom()})"
        if isinstance(layout, QBoxLayout):
            spacing_str = f" spacing: {layout.spacing()}"
        else:
            spacing_str = ""

        print(f"{padding}Layout {margins_str}, constraint: {layout.sizeConstraint().name}{spacing_str}")

        num_items = layout.count()
        for i in range(num_items):
            layout_item = layout.itemAt(i)
            item_info = _get_layout_item_info(layout_item)
            print(f"{padding}{item_info}")
            if isinstance(layout_item, QWidgetItem):
                _print_widget_and_children(layout_item.widget(), level + 1)
                dumped_children.append(layout_item.widget())

    # Now output any child widgets that weren't dumped as part of the layout
    widgets = w.findChildren(QWidget, "", Qt.FindChildOption.FindDirectChildrenOnly)
    undumped_children = []
    for child in widgets:
        if child not in dumped_children:
            undumped_children.append(child)

    if len(undumped_children) != 0:
        print(f"{padding} non-layout children:")
        for child in undumped_children:
            _print_widget_and_children(child)


def print_widget_hierarchy(w: QWidget):
    print(_get_widget_info(w))
    _print_widget_and_children(w)
