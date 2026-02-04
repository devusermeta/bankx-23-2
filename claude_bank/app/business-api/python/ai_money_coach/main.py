"""
AIMoneyCoach MCP Server - AI-Powered Personal Finance Advisory

Port: 8077
Purpose: Personal finance coaching grounded in "Debt-Free to Financial Freedom" book
         with strict 100% grounding validation using AI Search and Content Understanding

Tools:
1. ai_search_rag_results - Search book content with AI Search
2. ai_foundry_content_understanding - Validate 100% grounding and synthesize personalized advice
"""

import os
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables from workspace root
workspace_root = Path(__file__).parent.parent.parent.parent.parent
env_path = workspace_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logging.info(f"Loaded .env from: {env_path}")
else:
    logging.warning(f".env file not found at: {env_path}")

# Add app directory to path for common imports
app_dir = workspace_root / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from logging_config import setup_logging
from services import MoneyCoachAISearchService, MoneyCoachContentUnderstandingService
from mcp_tools import register_tools

# Import observability
from common.observability import setup_mcp_observability, MCPMetrics

# Setup logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration from environment
PORT = int(os.getenv("PORT", "8077"))
HOST = os.getenv("HOST", "0.0.0.0")

# Azure AI Search configuration
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
# Use multimodal index if available, otherwise fall back to standard index
AZURE_AI_SEARCH_INDEX = os.getenv("AZURE_AI_SEARCH_INDEX_UC3_MULTIMODAL") or os.getenv("AZURE_AI_SEARCH_INDEX_UC3", "bankx-money-coach")

# Azure AI Evaluation configuration
AZURE_AI_PROJECT_CONFIG = {
    "subscription_id": os.getenv("AZURE_AI_AGENT_SUBSCRIPTION_ID"),
    "resource_group_name": os.getenv("AZURE_AI_AGENT_RESOURCE_GROUP_NAME"),
    "project_name": os.getenv("AZURE_AI_AGENT_PROJECT_NAME")
}
AZURE_OPENAI_GPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT", "gpt-4.1-mini")

# Initialize FastMCP server
mcp = FastMCP("AIMoneyCoach MCP Server")

# Initialize observability
setup_mcp_observability(
    service_name="ai-money-coach",
    port=PORT
)
metrics = MCPMetrics("ai-money-coach")
logger.info("✅ Observability initialized for AIMoneyCoach MCP Server")

logger.info("=" * 80)
logger.info("AIMoneyCoach MCP Server - UC3: AI-Powered Personal Finance Advisory")
logger.info("=" * 80)
logger.info(f"Port: {PORT}")
logger.info(f"AI Search Index: {AZURE_AI_SEARCH_INDEX}")
logger.info(f"AI Search Endpoint: {AZURE_AI_SEARCH_ENDPOINT}")
logger.info(f"Azure AI Project: {AZURE_AI_PROJECT_CONFIG.get('project_name')}")
logger.info(f"Model Deployment: {AZURE_OPENAI_GPT_DEPLOYMENT}")
logger.info("Book: 'Debt-Free to Financial Freedom' (12 chapters)")
logger.info("=" * 80)

# Validate required configuration
if not AZURE_AI_SEARCH_ENDPOINT:
    logger.error("AZURE_AI_SEARCH_ENDPOINT is required")
    raise ValueError("AZURE_AI_SEARCH_ENDPOINT environment variable is required")

# Initialize services
logger.info("Initializing services...")

ai_search_service = MoneyCoachAISearchService(
    endpoint=AZURE_AI_SEARCH_ENDPOINT,
    key=AZURE_AI_SEARCH_KEY,
    index_name=AZURE_AI_SEARCH_INDEX
)

# Initialize Azure AI Evaluation (Groundedness Evaluator)
print("\n" + "=" * 80)
print("🔍 AZURE AI EVALUATION INITIALIZATION")
print("=" * 80)
try:
    if all(AZURE_AI_PROJECT_CONFIG.values()):
        content_understanding_service = MoneyCoachContentUnderstandingService(
            project_config=AZURE_AI_PROJECT_CONFIG,
            model_deployment=AZURE_OPENAI_GPT_DEPLOYMENT
        )
        print(f"✅ Azure AI Project configured: {AZURE_AI_PROJECT_CONFIG.get('project_name')}")
        print(f"📦 Model deployment: {AZURE_OPENAI_GPT_DEPLOYMENT}")
        print("✅ Azure AI Evaluation (Groundedness) ENABLED")
        logger.info("✅ Azure AI Evaluation enabled for Money Coach")
    else:
        content_understanding_service = None
        print("⚠️  Azure AI Project not fully configured")
        print("   Grounding validation will be DISABLED")
        logger.warning("⚠️ Azure AI Evaluation disabled - missing project configuration")
except Exception as e:
    content_understanding_service = None
    print(f"❌ Failed to initialize Azure AI Evaluation: {e}")
    logger.error(f"Failed to initialize Azure AI Evaluation: {e}")
print("=" * 80 + "\n")

# Register MCP tools
logger.info("Registering MCP tools...")
register_tools(
    mcp=mcp,
    ai_search=ai_search_service,
    content_understanding=content_understanding_service
)

logger.info("✅ AIMoneyCoach MCP Server initialized successfully")
logger.info("=" * 80)

if __name__ == "__main__":
    logger.info(f"Starting AIMoneyCoach MCP Server on {HOST}:{PORT}...")
    mcp.run(transport="http", host=HOST, port=PORT)
