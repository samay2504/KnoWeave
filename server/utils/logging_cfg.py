"""
Logging configuration for the application
"""

import logging
import sys
import os
import warnings
from pathlib import Path
from typing import Optional
from datetime import datetime

# Suppress pkg_resources deprecation warning from aioarango
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)

# Try to import rich for pretty logging
try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.traceback import install

    RICH_AVAILABLE = True
    install()  # Install rich traceback handler
except ImportError:
    RICH_AVAILABLE = False

# Try to import structlog for structured logging
try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}"
                f"{self.COLORS['RESET']}"
            )

        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_rich: bool = True,
    use_structured: bool = False,
    log_dir: str = "logs",
) -> logging.Logger:
    """
    Setup application logging with multiple handlers

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name
        use_rich: Use rich console logging if available
        use_structured: Use structured logging if available
        log_dir: Directory for log files

    Returns:
        Configured logger
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Create logs directory
    if log_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

    # Clear any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure root logger
    root_logger.setLevel(numeric_level)

    # Setup console handler
    if use_rich and RICH_AVAILABLE:
        # Use Rich handler for beautiful console output
        console = Console(stderr=True)
        console_handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=False,
        )
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
    else:
        # Use standard console handler with colors
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(numeric_level)

        if os.name != "nt":  # Don't use colors on Windows
            formatter = ColoredFormatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Setup file handler if requested
    if log_file:
        file_path = Path(log_dir) / log_file
        file_handler = logging.FileHandler(file_path, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file

        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Setup daily rotating file handler for errors
    try:
        from logging.handlers import TimedRotatingFileHandler

        if log_file:
            error_file = Path(log_dir) / "errors.log"
            error_handler = TimedRotatingFileHandler(
                error_file,
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)

            error_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"
            )
            error_handler.setFormatter(error_formatter)
            root_logger.addHandler(error_handler)

    except ImportError:
        pass  # TimedRotatingFileHandler not available

    # Setup structured logging if requested
    if use_structured and STRUCTLOG_AVAILABLE:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)

    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logger = logging.getLogger("human_ai_cocreation")
    logger.info(
        f"Logging configured - Level: {level}, Rich: {use_rich and RICH_AVAILABLE}"
    )

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module"""
    return logging.getLogger(f"human_ai_cocreation.{name}")


def log_function_call(
    func_name: str, args: dict, result: any = None, error: Exception = None
):
    """Helper function to log function calls with parameters and results"""
    logger = get_logger("function_calls")

    if error:
        logger.error(
            f"Function {func_name} failed",
            extra={
                "function": func_name,
                "args": args,
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )
    else:
        logger.debug(
            f"Function {func_name} completed",
            extra={
                "function": func_name,
                "args": args,
                "result_type": type(result).__name__ if result else None,
            },
        )


def log_performance(operation: str, duration: float, details: dict = None):
    """Log performance metrics"""
    logger = get_logger("performance")

    extra = {
        "operation": operation,
        "duration_seconds": duration,
        "details": details or {},
    }

    if duration > 5.0:
        logger.warning(f"Slow operation: {operation} took {duration:.2f}s", extra=extra)
    elif duration > 1.0:
        logger.info(f"Operation: {operation} took {duration:.2f}s", extra=extra)
    else:
        logger.debug(f"Operation: {operation} took {duration:.2f}s", extra=extra)


class LoggingContext:
    """Context manager for adding context to logs"""

    def __init__(self, logger: logging.Logger, **context):
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        if STRUCTLOG_AVAILABLE:
            self.old_factory = structlog.get_logger().bind(**self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if STRUCTLOG_AVAILABLE and self.old_factory:
            # Reset the logger factory
            pass


# Pre-configured loggers for different components
def get_agent_logger(agent_name: str) -> logging.Logger:
    """Get logger for agent components"""
    return get_logger(f"agents.{agent_name}")


def get_db_logger(db_type: str) -> logging.Logger:
    """Get logger for database components"""
    return get_logger(f"db.{db_type}")


def get_api_logger() -> logging.Logger:
    """Get logger for API components"""
    return get_logger("api")


def get_llm_logger() -> logging.Logger:
    """Get logger for LLM provider"""
    return get_logger("llm")


# Initialize default logging on import
setup_logging()
