"""
Structured logging configuration for BankX A2A system.
"""

import sys
import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict
from logging import LogRecord


class JsonFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            # Use timezone-aware UTC timestamp
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        if hasattr(record, "customer_id"):
            log_data["customer_id"] = record.customer_id
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    service_name: str = "bankx-agent",
) -> None:
    """
    Set up structured logging for the service.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting (True for production)
        service_name: Name of the service for log context

    Example:
        >>> setup_logging(level="INFO", json_format=True, service_name="account-agent")
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers = []

    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # Set formatter
    if json_format:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt=(
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add service name to all log records
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.service_name = service_name
        return record

    logging.setLogRecordFactory(record_factory)

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    # Filter noisy connection reset errors coming from asyncio/Proactor on Windows
    class ConnectionResetFilter(logging.Filter):
        def filter(self, record: LogRecord) -> bool:
            # If an exception is attached and it's a ConnectionResetError, drop it
            if record.exc_info:
                exc_type = record.exc_info[0]
                if exc_type and exc_type.__name__ == "ConnectionResetError":
                    return False

            # If the message text contains ConnectionResetError, drop it
            try:
                msg = record.getMessage()
                if "ConnectionResetError" in msg:
                    return False
            except Exception:
                pass

            return True

    console_handler.addFilter(ConnectionResetFilter())

    root_logger.info(f"Logging initialized for {service_name} at level {level}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing request", extra={"customer_id": "CUST-001"})
    """
    return logging.getLogger(name)
