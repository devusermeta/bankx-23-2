from fastmcp import FastMCP
import logging
from typing import Annotated
from pathlib import Path
import sys

# Add common directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "common"))
from path_utils import get_base_dir

logger = logging.getLogger(__name__)

mcp = FastMCP("Cache MCP Server")

# Cache directory
CACHE_DIR = get_base_dir() / "memory"


@mcp.tool(name="invalidateCache", description="Invalidate user cache to force fresh data retrieval")
def invalidate_cache(
    customer_id: Annotated[str, "Customer ID (e.g., CUST-002) whose cache should be invalidated"]
):
    """
    Invalidates (deletes) the cache file for a specific customer.
    This forces the system to fetch fresh data from MCP servers on next request.
    
    Use this tool after:
    - Processing a payment (to refresh balance and transactions)
    - Adding a beneficiary (to refresh beneficiary list)
    - Any operation that modifies user data
    
    Args:
        customer_id: Customer ID (e.g., "CUST-002")
    
    Returns:
        dict: Status of cache invalidation
    """
    logger.info(f"🗑️ Cache invalidation requested for {customer_id}")
    
    try:
        cache_path = CACHE_DIR / f"{customer_id}.json"
        
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"✅ Cache deleted for {customer_id}")
            return {
                "status": "ok",
                "message": f"Cache invalidated for {customer_id}",
                "cache_deleted": True
            }
        else:
            logger.info(f"ℹ️ No cache file found for {customer_id}")
            return {
                "status": "ok",
                "message": f"No cache found for {customer_id}",
                "cache_deleted": False
            }
    
    except Exception as e:
        logger.error(f"❌ Failed to invalidate cache for {customer_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to invalidate cache: {str(e)}",
            "cache_deleted": False
        }
