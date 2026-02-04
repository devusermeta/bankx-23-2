"""
ProdInfoFAQ MCP Server - Product Information & FAQ with AI Search and Content Understanding

Port: 8076
Purpose: RAG-based product info retrieval with grounding validation using Azure AI Search and AI Foundry Content Understanding

Tools:
1. search_documents - AI Search with vector embeddings
2. get_document_by_id - Retrieve specific document sections
3. get_content_understanding - Validate grounding with AI Foundry (CRITICAL for 100% accuracy)
4. write_to_cosmosdb - Store support tickets
5. read_from_cosmosdb - Check cache for similar queries
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
from services import AISearchService, ContentUnderstandingService, CosmosDBService
from mcp_tools import register_tools

# Import observability
from common.observability import setup_mcp_observability, MCPMetrics

# Setup logging
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Configuration from environment
PORT = int(os.getenv("PORT", "8076"))
HOST = os.getenv("HOST", "0.0.0.0")

# Azure AI Search configuration
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
AZURE_AI_SEARCH_INDEX = os.getenv("AZURE_AI_SEARCH_INDEX_UC2", "bankx-products-faq")

# Azure AI Foundry Project Configuration (for Evaluation SDK)
AZURE_AI_PROJECT_CONFIG = {
    "subscription_id": os.getenv("AZURE_AI_AGENT_SUBSCRIPTION_ID"),
    "resource_group_name": os.getenv("AZURE_AI_AGENT_RESOURCE_GROUP_NAME"),
    "project_name": os.getenv("AZURE_AI_AGENT_PROJECT_NAME")
}

# Azure CosmosDB configuration
AZURE_COSMOSDB_ENDPOINT = os.getenv("AZURE_COSMOSDB_ENDPOINT")
AZURE_COSMOSDB_KEY = os.getenv("AZURE_COSMOSDB_KEY")
AZURE_COSMOSDB_DATABASE = os.getenv("AZURE_COSMOSDB_DATABASE", "BankX")
AZURE_COSMOSDB_CONTAINER = os.getenv("AZURE_COSMOSDB_CONTAINER_TICKETS", "support_tickets")

# Initialize FastMCP server
mcp = FastMCP("ProdInfoFAQ MCP Server")

# Initialize observability
setup_mcp_observability(
    service_name="prodinfo-faq",
    port=PORT
)
metrics = MCPMetrics("prodinfo-faq")
logger.info("✅ Observability initialized for ProdInfoFAQ MCP Server")

logger.info("=" * 80)
logger.info("ProdInfoFAQ MCP Server - UC2: Product Info & FAQ")
logger.info("=" * 80)
logger.info(f"Port: {PORT}")
logger.info(f"AI Search Index: {AZURE_AI_SEARCH_INDEX}")
logger.info(f"AI Search Endpoint: {AZURE_AI_SEARCH_ENDPOINT}")
logger.info(f"Azure AI Project: {AZURE_AI_PROJECT_CONFIG['project_name']}")
logger.info(f"CosmosDB: {AZURE_COSMOSDB_ENDPOINT}")
logger.info("=" * 80)

# Validate required configuration
if not AZURE_AI_SEARCH_ENDPOINT:
    logger.error("AZURE_AI_SEARCH_ENDPOINT is required")
    raise ValueError("AZURE_AI_SEARCH_ENDPOINT environment variable is required")

if not all(AZURE_AI_PROJECT_CONFIG.values()):
    logger.warning("⚠️ Azure AI Project not fully configured - RAG Grounding Evaluation will be disabled")
    logger.warning("   Search will work, but grounding validation will be skipped")

# Initialize services
logger.info("Initializing services...")

ai_search_service = AISearchService(
    endpoint=AZURE_AI_SEARCH_ENDPOINT,
    key=AZURE_AI_SEARCH_KEY,
    index_name=AZURE_AI_SEARCH_INDEX
)

# Initialize Azure AI Evaluation (Groundedness) only if project is configured
content_understanding_service = None
AZURE_OPENAI_GPT_DEPLOYMENT = os.getenv("AZURE_OPENAI_GPT_DEPLOYMENT", "gpt-4.1-mini")

print("\n" + "="*80)
print("🔍 AZURE AI EVALUATION INITIALIZATION")
print("="*80)

if all(AZURE_AI_PROJECT_CONFIG.values()):
    print(f"✅ Azure AI Project configured: {AZURE_AI_PROJECT_CONFIG['project_name']}")
    print(f"📦 Model deployment: {AZURE_OPENAI_GPT_DEPLOYMENT}")
    try:
        content_understanding_service = ContentUnderstandingService(
            project_config=AZURE_AI_PROJECT_CONFIG,
            model_deployment=AZURE_OPENAI_GPT_DEPLOYMENT
        )
        print("✅ Azure AI Evaluation (Groundedness) ENABLED")
        print("="*80 + "\n")
        logger.info("✅ Azure AI Evaluation (Groundedness) enabled")
    except Exception as e:
        print(f"❌ Azure AI Evaluation initialization FAILED: {e}")
        print("⚠️  Continuing without grounding evaluation")
        print("="*80 + "\n")
        logger.warning(f"⚠️ Azure AI Evaluation initialization failed: {e}")
        logger.warning("Continuing without grounding evaluation - answers may not be validated")
else:
    print("❌ Azure AI Project NOT configured - missing environment variables")
    print("="*80 + "\n")
    logger.warning("⚠️ Azure AI Evaluation disabled - grounding validation will be skipped")

# CosmosDB is optional (for dev mode, can work without it)
cosmosdb_service = None
if AZURE_COSMOSDB_ENDPOINT and "your-cosmosdb" not in AZURE_COSMOSDB_ENDPOINT:
    try:
        cosmosdb_service = CosmosDBService(
            endpoint=AZURE_COSMOSDB_ENDPOINT,
            key=AZURE_COSMOSDB_KEY,
            database=AZURE_COSMOSDB_DATABASE,
            container=AZURE_COSMOSDB_CONTAINER
        )
        logger.info("✅ CosmosDB service initialized")
    except Exception as e:
        logger.warning(f"⚠️  CosmosDB initialization failed: {e}")
        logger.warning("Continuing without CosmosDB - ticket creation and caching disabled")
else:
    logger.warning("⚠️  CosmosDB not configured - ticket creation and caching disabled")

# Register MCP tools
logger.info("Registering MCP tools...")
register_tools(
    mcp=mcp,
    ai_search=ai_search_service,
    content_understanding=content_understanding_service,
    cosmosdb=cosmosdb_service
)

logger.info("✅ ProdInfoFAQ MCP Server initialized successfully")
logger.info("=" * 80)

if __name__ == "__main__":
    logger.info(f"Starting ProdInfoFAQ MCP Server on {HOST}:{PORT}...")
    mcp.run(transport="http", host=HOST, port=PORT)
