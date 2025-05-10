import os
import sys
from datetime import datetime

from loguru import logger


def setup_logging(debug_mode=False):
    """Set up Loguru logging for the application"""

    # Remove default handler
    logger.remove()

    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    logs_dir = os.environ.get("EDON_LOGS_DIR", logs_dir)

    os.makedirs(logs_dir, exist_ok=True)

    # Determine log file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = os.path.join(logs_dir, f"edon-{timestamp}.log")

    # Log level based on debug mode
    log_level = "DEBUG" if debug_mode else "INFO"

    # Add file handler with rotation
    logger.add(
        log_file,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="1 week",  # Keep logs for 1 week
        compression="zip",  # Compress rotated logs
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        backtrace=True,  # Include traceback info for errors
        diagnose=True,  # Show variable values in tracebacks
    )

    # Add console handler for immediate feedback
    logger.add(
        sys.stdout,
        level=log_level,
        format="<level>{level: <8}</level> | <green>{name}</green>:<yellow>{function}</yellow>:<blue>{line}</blue> - <level>{message}</level>",
        colorize=True,
    )

    # Intercept exceptions
    @logger.catch(onerror=lambda _: sys.exit(1))
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't catch keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.opt(exception=(exc_type, exc_value, exc_traceback)).critical("Uncaught exception:")

    sys.excepthook = handle_exception

    logger.info(f"Logging initialized. Log file: {log_file}")

    return logger
