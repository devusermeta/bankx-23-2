
import os
import logging
from logging_config import configure_logging
from mcp_tools import mcp

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    configure_logging()
    profile = os.environ.get("PROFILE", "prod")

    # Use environment variable PORT if set, otherwise use profile-based default
    port = int(os.environ.get("PORT", "8074"))
    logger.info(f"Starting contacts service server with profile: {profile}, port: {port}")
    mcp.run(transport="http", port=port, host="0.0.0.0")
