# Create a new file like base_graphics_item.py or add to a common utils module
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QWidget
from PySide6.QtGui import QPainter
from PySide6.QtCore import QRectF
from loguru import logger
import typing


class BaseEdonGraphicsObject(QGraphicsObject):
    def __init_subclass__(cls, **kwargs):
        """
        This hook is called when a class inherits from BaseEdonGraphicsObject.
        It checks if essential Qt graphics methods are directly overridden in the subclass.
        """
        super().__init_subclass__(**kwargs)

        # Check if 'paint' is directly implemented in the subclass's __dict__
        # and not just inherited from this base class or QGraphicsObject itself.
        if "paint" not in cls.__dict__ or cls.paint == BaseEdonGraphicsObject.paint:
            logger.warning(
                f"Class '{cls.__module__}.{cls.__name__}' inherits from BaseEdonGraphicsObject "
                f"but does not appear to directly override the 'paint' method. "
                f"If this is not an abstract class, it will raise an error at runtime."
            )

        if (
            "boundingRect" not in cls.__dict__
            or cls.boundingRect == BaseEdonGraphicsObject.boundingRect
        ):
            logger.warning(
                f"Class '{cls.__module__}.{cls.__name__}' inherits from BaseEdonGraphicsObject "
                f"but does not appear to directly override the 'boundingRect' method. "
                f"If this is not an abstract class, it will raise an error at runtime."
            )

    def boundingRect(self) -> QRectF:
        """
        This method MUST be overridden by all concrete (non-abstract) subclasses.
        """
        error_message = (
            f"CRITICAL ERROR: boundingRect() was called on an instance of "
            f"'{self.__class__.__module__}.{self.__class__.__name__}', but this class "
            f"has not properly overridden it. This method is essential for item layout and interaction."
        )
        # Log it first so it appears before the exception potentially gets re-wrapped by Qt
        logger.critical(error_message)
        raise NotImplementedError(error_message)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: typing.Optional[QWidget] = None,
    ) -> None:
        """
        This method MUST be overridden by all concrete (non-abstract) subclasses.
        """
        error_message = (
            f"CRITICAL ERROR: paint() was called on an instance of "
            f"'{self.__class__.__module__}.{self.__class__.__name__}', but this class "
            f"has not properly overridden it. This method is essential for drawing the item."
        )
        logger.critical(error_message)
        # raise NotImplementedError(error_message)
