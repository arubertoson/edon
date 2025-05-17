class SingleLineTextItem(QGraphicsTextItem):
    def __init__(self, text="", target_layout_height: float = theme.SOCKET_ROW_HEIGHT, parent=None):
        super().__init__(text, parent)
        logger.trace(f"SingleLineTextItem created with text: '{text}'")
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self._alignment = Qt.AlignmentFlag.AlignCenter
        self._text_margin = theme.SOCKET_HORIZONTAL_PADDING  # Use theme padding

        font = self.font()
        font.setPointSize(getattr(theme, "FONT_SOCKET_LABEL_DEFAULT_SIZE", 10))

        self.setFont(font)
        self.setDefaultTextColor(getattr(theme, "SOCKET_LABEL_TEXT_COLOR", theme.INPUT_TEXT_COLOR))
        self.setPlainText(text)

        doc = self.document()
        doc.setDocumentMargin(0)  # Crucial for predictable layout
        doc.setUndoRedoEnabled(False)

        text_option = QTextOption(self._alignment)  # Start with current alignment
        text_option.setWrapMode(QTextOption.WrapMode.NoWrap)
        doc.setDefaultTextOption(text_option)

        self._view_width = 0.0
        self._view_height = target_layout_height  # Height is fixed by target_layout_height
        self._hscroll = 0.0  # Horizontal scroll offset in pixels

    def set_view_size(self, width: float, height: float):
        self.prepareGeometryChange()
        self._view_width = width
        self._view_height = height
        self.document().setTextWidth(max(0, width - 2 * self._text_margin))

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._view_width, self._view_height)

    def _updateScrollPosition(self):
        if not self.hasFocus():
            # Optionally reset scroll when not focused if elision should always show start of text
            # self._hscroll = 0
            self.update()
            return

        text = self.toPlainText()
        if not text:
            self._hscroll = 0
            self.update()
            return

        cursor = self.textCursor()
        cursor_idx = cursor.position()
        metrics = QFontMetricsF(self.font())

        # This is the width of the area where text is actually drawn (inside margins)
        drawable_text_width_area = self._view_width - 2 * self._text_margin
        if drawable_text_width_area <= 0:
            return

        pixel_pos_of_cursor = metrics.horizontalAdvance(text[:cursor_idx])

        new_hscroll = self._hscroll

        # If cursor is trying to go past the right edge of the visible scrolled window
        if pixel_pos_of_cursor > self._hscroll + drawable_text_width_area:
            new_hscroll = pixel_pos_of_cursor - drawable_text_width_area
        # If cursor is trying to go past the left edge of the visible scrolled window
        elif pixel_pos_of_cursor < self._hscroll:
            new_hscroll = pixel_pos_of_cursor

        # Snap new_hscroll to a character boundary (to its left)
        snapped_hscroll = 0.0
        accumulated_width = 0.0
        found_snap_point = False
        for i in range(len(text)):
            char_segment = text[i : i + 1]
            char_w = metrics.horizontalAdvance(char_segment)
            if accumulated_width + char_w > new_hscroll:
                snapped_hscroll = accumulated_width
                found_snap_point = True
                break
            accumulated_width += char_w

        if not found_snap_point and len(text) > 0:  # If new_hscroll is beyond all text or text is empty
            snapped_hscroll = accumulated_width  # Should be full text width if new_hscroll was large

        self._hscroll = snapped_hscroll

        # Final clamping of _hscroll
        full_text_pixel_width = metrics.horizontalAdvance(text)
        if full_text_pixel_width <= drawable_text_width_area:
            self._hscroll = 0.0
        else:
            self._hscroll = max(0.0, min(self._hscroll, full_text_pixel_width - drawable_text_width_area))
            # Special case: if cursor is at the very end of text, ensure last characters are visible
            if cursor_idx == len(text):  # Cursor is at the end
                self._hscroll = max(self._hscroll, full_text_pixel_width - drawable_text_width_area)

        self.update()

    def keyPressEvent(self, event):
        logger.debug(
            f"SingleLineTextItem.keyPressEvent: key={event.key()}, text='{event.text()}', modifiers={event.modifiers()}, item_has_focus={self.hasFocus()}"
        )
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            logger.debug("  Enter/Return pressed, clearing focus.")
            self.clearFocus()
            event.accept()  # Accept to prevent further processing if this item handles it
            return
        if event.key() == Qt.Key.Key_Tab:
            logger.debug("  Tab pressed, clearing focus.")
            self.clearFocus()  # Default QGraphicsTextItem might handle tab for focus change, let it.
            # Do not accept, allow superclass to handle tab for focus navigation
            super().keyPressEvent(event)
            return
        if event.key() == Qt.Key.Key_Backspace and self.toPlainText() == "":
            logger.debug("  Backspace on empty text, clearing focus.")
            self.clearFocus()
            event.accept()  # Accept to prevent further processing
            return
        if event.text() == "\\n":  # Prevent newlines
            logger.debug("  Newline character detected, ignoring.")
            event.accept()
            return

        super().keyPressEvent(event)
        logger.debug(f"  After super().keyPressEvent, event.isAccepted={event.isAccepted()}")
        self._updateScrollPosition()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent):
        logger.trace(f"SingleLineTextItem.mousePressEvent, item_has_focus={self.hasFocus()}")
        super().mousePressEvent(event)
        self._updateScrollPosition()

    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent):
        logger.trace(f"SingleLineTextItem.mouseDoubleClickEvent, item_has_focus={self.hasFocus()}")
        super().mouseDoubleClickEvent(event)
        self._updateScrollPosition()

    def set_alignment(self, alignment: Qt.AlignmentFlag):
        self._alignment = alignment
        doc = self.document()
        option = doc.defaultTextOption()
        option.setAlignment(alignment)
        doc.setDefaultTextOption(option)
        self.update()

    def alignment(self) -> Qt.AlignmentFlag:
        return self._alignment

    def focusInEvent(self, event):
        logger.debug(f"SingleLineTextItem.focusInEvent, reason={event.reason()}")
        super().focusInEvent(event)
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        self.setTextCursor(cursor)
        self._updateScrollPosition()

    def focusOutEvent(self, event):
        logger.debug(f"SingleLineTextItem.focusOutEvent, reason={event.reason()}")
        super().focusOutEvent(event)
        cursor = self.textCursor()
        cursor.clearSelection()
        self.setTextCursor(cursor)
        self._updateScrollPosition()
        self.update()

    def paint(self, painter: "QPainter", option: "QStyleOptionGraphicsItem", widget: QWidget | None = None):
        # Full bounding rect of this QGraphicsTextItem
        full_rect = self.boundingRect()

        # The rectangle inside margins where text, cursor, selection are drawn
        line_rect = full_rect.adjusted(self._text_margin, 0, -self._text_margin, 0)

        # Draw background (using full_rect)
        painter.setBrush(theme.INPUT_WIDGET_BACKGROUND_COLOR)
        if self.hasFocus():
            painter.setPen(theme.NODE_BORDER_SELECTED)
        else:
            painter.setPen(theme.INPUT_WIDGET_BORDER_COLOR)
        painter.drawRoundedRect(full_rect, theme.INPUT_WIDGET_BORDER_RADIUS, theme.INPUT_WIDGET_BORDER_RADIUS)

        painter.save()
        painter.setClipRect(line_rect)  # Essential: clip all drawing to this inner rectangle

        painter.setFont(self.font())
        painter.setPen(self.defaultTextColor())

        full_text = self.toPlainText()
        metrics = QFontMetricsF(self.font())

        text_to_display = full_text
        # XXX: NOT TRUE FOR DIFFERENT ALIGNMENTS
        text_draw_x_origin = line_rect.left()  # Base X for drawing text

        full_text_pixel_width = metrics.horizontalAdvance(full_text)
        drawable_text_width_area = line_rect.width()

        if not self.hasFocus() and full_text_pixel_width > drawable_text_width_area:
            # Not focused and text overflows: Elide
            text_to_display = metrics.elidedText(full_text, Qt.TextElideMode.ElideRight, drawable_text_width_area)
            # Elided text is drawn according to alignment within line_rect
            # No scrolling offset is applied here.
            # painter.drawText will handle alignment within line_rect.

            # Early return to avoid drawing text that will be clipped
            painter.drawText(line_rect, int(self._alignment), text_to_display)
            painter.restore()
            return

        text_draw_x_origin -= self._hscroll

        # Vertical alignment for text baseline
        # Ascent is distance from baseline to top of char. Descent is baseline to bottom.
        # Height is ascent + descent.
        # To center vertically: line_rect.center().y() - metrics.height()/2 + metrics.ascent()
        # Or simpler: line_rect.top() + (line_rect.height() - metrics.height()) / 2 + metrics.ascent()
        text_baseline_y = line_rect.top() + (line_rect.height() + metrics.ascent() - metrics.descent()) / 2

        # Draw potentially scrolled text. For scrolled text, alignment is implicitly left relative to the scroll window.
        # The drawText with QPointF always draws left-aligned from that point.
        # If we want to respect original alignment for text that FITS after scrolling, it's more complex.
        # For now, assume scrolled text is drawn from its computed origin.

        # If full text (even scrolled) is SHORTER than drawable_text_width_area, apply alignment to the scrolled view
        actual_draw_x = text_draw_x_origin
        if (
            full_text_pixel_width - self._hscroll < drawable_text_width_area
        ):  # if the remaining visible text is shorter than the view
            if self._alignment == Qt.AlignmentFlag.AlignRight:
                actual_draw_x = line_rect.right() - (full_text_pixel_width - self._hscroll)
            elif self._alignment == Qt.AlignmentFlag.AlignHCenter or self._alignment == Qt.AlignmentFlag.AlignCenter:
                actual_draw_x = (
                    line_rect.left() + (drawable_text_width_area - (full_text_pixel_width - self._hscroll)) / 2
                )

        painter.drawText(QPointF(actual_draw_x, text_baseline_y), full_text)

        # --- Draw Selection Highlight ---
        cursor = self.textCursor()
        if self.hasFocus() and cursor.hasSelection():
            sel_start_idx = min(cursor.anchor(), cursor.position())
            sel_end_idx = max(cursor.anchor(), cursor.position())

            if sel_start_idx != sel_end_idx:
                pixel_pos_sel_start_in_text = metrics.horizontalAdvance(full_text[:sel_start_idx])
                pixel_pos_sel_end_in_text = metrics.horizontalAdvance(full_text[:sel_end_idx])

                sel_highlight_width = pixel_pos_sel_end_in_text - pixel_pos_sel_start_in_text

                # Determine the base X for the selection highlight
                # actual_draw_x is calculated before drawing the text and considers alignment and scroll
                base_x_for_selection = actual_draw_x
                sel_highlight_screen_x = base_x_for_selection + pixel_pos_sel_start_in_text

                # If text is scrolled, sel_start_pixel is relative to the beginning of the *full text*.
                # actual_draw_x might be line_rect.left() if scrolled, or offset if aligned and fits.
                # The key is that pixel_pos_sel_start_in_text is an offset *from the start of the string*.
                # actual_draw_x is where that string (or its scrolled part) begins drawing.
                if (
                    self._hscroll > 0
                ):  # If scrolled, actual_draw_x is effectively line_rect.left() for the scrolled content starting point
                    sel_highlight_screen_x = line_rect.left() + (pixel_pos_sel_start_in_text - self._hscroll)

                highlight_y = line_rect.top() + (line_rect.height() - metrics.height()) / 2
                selection_rect = QRectF(sel_highlight_screen_x, highlight_y, sel_highlight_width, metrics.height())

                # Use a more specific default or ensure theme.INPUT_WIDGET_SELECTION_COLOR exists
                selection_color = getattr(theme, "INPUT_WIDGET_SELECTION_COLOR", QColor(0, 120, 215, 128))
                painter.fillRect(selection_rect, selection_color)

        # --- Draw Cursor ---
        if self.hasFocus() and not cursor.hasSelection():
            cursor_idx = cursor.position()
            pixel_pos_of_cursor_in_text = metrics.horizontalAdvance(full_text[:cursor_idx])

            # Use actual_draw_x as the base, similar to selection.
            # actual_draw_x is calculated before drawing the text and considers alignment and scroll
            base_x_for_cursor = actual_draw_x
            cursor_screen_x = base_x_for_cursor + pixel_pos_of_cursor_in_text

            if self._hscroll > 0:  # If scrolled
                cursor_screen_x = line_rect.left() + (pixel_pos_of_cursor_in_text - self._hscroll)

            cursor_y_start = line_rect.top() + (line_rect.height() - metrics.height()) / 2
            cursor_y_end = cursor_y_start + metrics.height()

            painter.setPen(self.defaultTextColor())  # Ensure pen is set for cursor
            painter.drawLine(int(cursor_screen_x), int(cursor_y_start), int(cursor_screen_x), int(cursor_y_end))

        painter.restore()


class StyledTextSocketAdaptor(QGraphicsObject):
    def __init__(
        self,
        text_item: SingleLineTextItem,
        fixed_width: float = theme.NODE_MIN_WIDTH,
        fixed_height: float = theme.SOCKET_ROW_HEIGHT,
        horizontal_margin: float = theme.SOCKET_HORIZONTAL_PADDING,
        parent: QGraphicsItem | None = None,
    ):
        super().__init__(parent)
        logger.trace(f"StyledTextSocketAdaptor created for text_item: {text_item}")
        self._text_item = text_item
        self._adaptor_fixed_width = fixed_width
        self._adaptor_fixed_height = fixed_height
        self._text_item_content_width = self._adaptor_fixed_width - (2 * horizontal_margin)
        self._text_item_content_height = self._adaptor_fixed_height

        if self._text_item.parentItem() != self:
            self._text_item.setParentItem(self)

        self._text_item.set_view_size(self._text_item_content_width, self._text_item_content_height)
        self._text_item.setPos(horizontal_margin, 0)

    def get_required_component_width(self) -> float:
        return self._adaptor_fixed_width

    def get_required_component_height(self) -> float:
        return self._adaptor_fixed_height

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._adaptor_fixed_width, self._adaptor_fixed_height)

    def text_item(self) -> SingleLineTextItem:
        return self._text_item

    def set_text_alignment(self, alignment: Qt.AlignmentFlag) -> None:
        if hasattr(self._text_item, "set_alignment"):
            self._text_item.set_alignment(alignment)


def create_string_socket_component(
    initial_value: Any = "",
    controller: "GraphController | None" = None,
    node_id: str = "",
    socket_name: str = "",
    parent_gfx_item: QGraphicsItem | None = None,
) -> tuple[StyledTextSocketAdaptor, SingleLineTextItem]:
    """Creates a SingleLineTextItem for string display/input, wrapped in a StyledTextSocketAdaptor.

    Args:
        initial_value: The initial string value for the text item. Defaults to "".
        controller: The graph controller, if interactions need to update the backend.
                    Currently unused in this specific factory. Defaults to None.
        node_id: The ID of the parent node entity. Currently unused. Defaults to "".
        socket_name: The name of the socket entity. Currently unused. Defaults to "".
        parent_gfx_item: The parent QGraphicsItem for the StyledTextSocketAdaptor.
                         Defaults to None.

    Returns:
        A tuple containing the configured StyledTextSocketAdaptor and the SingleLineTextItem
        instance.
    """
    logger.debug(
        f"Creating string socket component (SingleLineTextItem) for node_id='{node_id}', socket_name='{socket_name}' with initial_value='{initial_value}'"
    )
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter
    text_item = SingleLineTextItem(str(initial_value if initial_value is not None else ""))
    adaptor = StyledTextSocketAdaptor(
        text_item=text_item,
        parent=parent_gfx_item,
    )
    adaptor.set_text_alignment(alignment)
    return adaptor, text_item
