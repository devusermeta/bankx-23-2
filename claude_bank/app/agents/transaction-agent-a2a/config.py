"""Configuration for TransactionAgent A2A Microservice"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment from .env file
load_dotenv(override=True)

# =============================================================================
# AZURE AI FOUNDRY SETTINGS
# =============================================================================
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
if not AZURE_AI_PROJECT_ENDPOINT:
    raise ValueError("AZURE_AI_PROJECT_ENDPOINT is required")

# =============================================================================
# AGENT SETTINGS (TransactionAgent in Azure AI Foundry)
# =============================================================================
TRANSACTION_AGENT_NAME = os.getenv("TRANSACTION_AGENT_NAME", "transaction-a2a")
TRANSACTION_AGENT_VERSION = os.getenv("TRANSACTION_AGENT_VERSION", "1")
TRANSACTION_AGENT_MODEL_DEPLOYMENT = os.getenv("TRANSACTION_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# Azure AI Model Deployment (fallback)
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")

# =============================================================================
# MCP SERVER URLS (Transaction agent uses Account + Transaction MCP)
# =============================================================================
ACCOUNT_MCP_SERVER_URL = os.getenv("ACCOUNT_MCP_SERVER_URL", "https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")
TRANSACTION_MCP_SERVER_URL = os.getenv("TRANSACTION_MCP_SERVER_URL", "https://transaction.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")

# =============================================================================
# A2A SERVER SETTINGS
# =============================================================================
A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "0.0.0.0")
A2A_SERVER_PORT = int(os.getenv("A2A_SERVER_PORT", "9002"))


def validate_config():
    """Validate all required configuration values are present"""
    required_vars = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "TRANSACTION_AGENT_NAME": TRANSACTION_AGENT_NAME,
        "TRANSACTION_AGENT_VERSION": TRANSACTION_AGENT_VERSION,
        "ACCOUNT_MCP_SERVER_URL": ACCOUNT_MCP_SERVER_URL,
        "TRANSACTION_MCP_SERVER_URL": TRANSACTION_MCP_SERVER_URL,
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    print("✅ Configuration validated successfully")

    
    print("✅ TransactionAgent A2A configuration validated")


if __name__ == "__main__":
    validate_config()
    print(f"Transaction Agent: {settings.TRANSACTION_AGENT_NAME} v{settings.TRANSACTION_AGENT_VERSION}")
    print(f"Account MCP: {settings.ACCOUNT_MCP_SERVER_URL}")
    print(f"Transaction MCP: {settings.TRANSACTION_MCP_SERVER_URL}")
    print(f"Server will run on {settings.HOST}:{settings.PORT}")
