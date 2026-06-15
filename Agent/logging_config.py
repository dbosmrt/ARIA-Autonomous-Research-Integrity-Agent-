"""
Logging configuration.
Production: goolge cloud structured logging : Cloud Logging
Development: Rich Console output with colors.
"""

import os
import logging
import sys

def setup_logging() -> None:

    environment = os.getenv("ENVIRONMENT", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    if environment == "production":
        _setup_cloud_logging(root_logger)
    else:
        _setup_dev_logging(root_logger)


def _setup_cloud_logging(logger: logging.Logger) -> None:
    try:
        from google.cloud.logging.handlers import StructuredLogHandler

        handler = StructuredLogHandler()
        logger.addHandler(handler)
        logger.info("Cloud Logging initialized (production mode)")
    except ImportError:
        _setup_dev_logging(logger)
        logger.warning(
            "google-cloud-logging not installed, falling back to console logging."
        )

def _setup_dev_logging(logger: logging.Logger) -> None:
    try:
        from rich.logging import RichHandler

        # Console handler with Rich formatting
        console_handler = RichHandler(
            rich_tracebacks= True,
            show_time= True,
            show_level= True,
            show_path=True,
        )
        console_formatter = logging.Formatter("%(name)s-%(messages)s-%(levelnames)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler for persistent logs
        import os
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "aria.log")

        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    except ImportError:
        # Fallback if rich is not available
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctimes)s | %(levelname)-8s | %(name)s = %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Still add file logging even in fallback case
        import os
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "aria.log")

        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

def get_agent_logger(agent_name: str) -> logging.Logger:
    return logging.getLogger(f"reprcheck.agent.{agent_name}")

