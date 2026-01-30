"""
Logging configuration for Account MCP Server
"""

import logging
import sys


def configure_logging(level: str = "INFO"):
    """
    Configure logging for the MCP server.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger("fastmcp").setLevel(level)
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel("WARNING")  # Reduce access log noise
    
    logging.info("Logging configured successfully")
