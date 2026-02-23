"""
Unified Payment MCP Server - Main Application

FastMCP server that exposes the unified payment MCP tools.
Consolidates account, beneficiary, limits, and transfer operations.

Run with: python main.py
"""

import os
import logging
from logging_config import configure_logging
from mcp_tools import mcp

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    configure_logging()
    profile = os.environ.get("PROFILE", "prod")
    
    # Use environment variable PORT if set, otherwise use default
    port = int(os.environ.get("PORT", "8076"))
    logger.info(f"Starting payment-unified MCP server with profile: {profile}, port: {port}")
    mcp.run(transport="http", port=port, host="0.0.0.0")
