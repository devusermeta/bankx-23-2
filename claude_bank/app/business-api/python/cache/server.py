"""
Cache MCP Server - Cache invalidation service

Provides tools for invalidating user cache to ensure fresh data retrieval.
"""

import logging
from mcp_tools import mcp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Starting Cache MCP Server on stdio")
    mcp.run(transport='stdio')
