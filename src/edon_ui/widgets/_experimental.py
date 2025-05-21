# def set_dynamic_width_and_height(
#         self, screen_geometry: QRect, width_ratio: float = 0.5, height_ratio: float = 0.5
#     ):
#         """
#         The screen and height will be updated to match the screen geometry.
#         """
#         screen_width = int(screen_geometry.width() * width_ratio)
#         screen_height = int(screen_geometry.height() * height_ratio)
#         self.resize(screen_width, screen_height)
#         self.overlay.resize(screen_geometry.width(), screen_geometry.height())

#         # Make the dialog window appear in the center of the screen
#         x = int(screen_geometry.center().x() - self.width() / 2)
#         y = int(screen_geometry.center().y() - self.height() / 2)
#         self.move(x, y)
# def showEvent(self, event: QShowEvent) -> None:
#     super().showEvent(event)

#     window = self.parent().window()

#     self.overlay = Overlay(self)
#     self.raise_()

#     screen = window.windowHandle().screen()
#     screen_geometry = screen.geometry()
#     self.set_dynamic_width_and_height(screen_geometry)

#     screen.geometryChanged.connect(self.set_dynamic_width_and_height)
