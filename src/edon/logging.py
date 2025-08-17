import os
import sys
from datetime import datetime
from types import TracebackType

from loguru import logger
from PySide6.QtCore import QCoreApplication  # Important for Qt app exit


# This will be our global excepthook
def an_exception_handler(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """
    Global excepthook that logs all unhandled exceptions using Loguru
    and then terminates the application.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Respect KeyboardInterrupt and let the default handler deal with it
        # which typically involves a clean exit.
        logger.warning("KeyboardInterrupt received. Exiting...")
        logger.complete()  # Flush logs before default handler takes over
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Log the critical error using Loguru, which will include the traceback
    logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical(
        f"CRITICAL UNHANDLED EXCEPTION ({exc_type.__name__}). Application will terminate."
    )

    # Ensure all logs are flushed before attempting to exit
    # Loguru's critical messages might flush, but being explicit is safer.
    logger.complete()

    # For Qt applications, it's often best to ask the QCoreApplication to exit first
    app = QCoreApplication.instance()
    if app:
        logger.info("Requesting QCoreApplication to exit due to unhandled exception.")
        # app.exit(1) # This signals the event loop to terminate.
        # However, sys.exit(1) below is more forceful and immediate
        # if we're in an excepthook.
        # If you experience issues with Qt cleanup, you might reinstate app.exit()
        # and potentially add a small delay or a more complex shutdown sequence.
        # For now, direct sys.exit after logging is often most reliable for tracebacks.
        pass  # Often, sys.exit is enough and more direct from an excepthook.

    # Forcefully exit the application.
    # This is crucial: if the excepthook returns, Python might consider the exception handled.
    sys.exit(1)  # Use a non-zero exit code to indicate an error.


def setup_logging(log_level: str = "INFO", enable_file_logging: bool = False) -> None:
    """
    Set up Loguru logging for the application.
    """
    logger.remove()  # Remove default handlers

    if enable_file_logging:
        logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        logs_dir = os.environ.get("EDON_LOGS_DIR", logs_dir)
        os.makedirs(logs_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_file = os.path.join(logs_dir, f"edon-{timestamp}.log")

        logger.add(
            log_file,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            backtrace=True,  # Essential for exceptions
            diagnose=True,  # Useful for variable values in tracebacks
            enqueue=True,  # Make file logging asynchronous and process-safe
        )
        logger.info(f"File logging initialized. Log file: {log_file}")

    # Console handler
    logger.add(
        sys.stderr,  # Log to stderr by convention for errors/diagnostics
        level=log_level,
        format="<level>{level: <8}</level> | <green>{name}</green>:<yellow>{function}</yellow>:<blue>{line}</blue> - <level>{message}</level>",
        colorize=True,
        backtrace=True,  # Ensure console also gets tracebacks for logged exceptions
        diagnose=True,
    )

    logger.info(f"Console logging initialized at level {log_level}.")

    # Set the global exception hook
    # The @logger.catch on an_exception_handler is not strictly necessary
    # if the handler itself is robust, but can catch errors within the handler.
    # For simplicity here, we'll make the handler robust.
    # If you want to use @logger.catch on the excepthook itself:
    # @logger.catch(onerror=lambda _: sys.exit(2)) # Exit with 2 if excepthook itself fails
    # def an_exception_handler_decorated(...): ...
    # sys.excepthook = an_exception_handler_decorated
    sys.excepthook = an_exception_handler
    logger.info("Global exception handler (sys.excepthook) configured.")
