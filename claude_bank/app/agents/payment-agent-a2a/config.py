"""
Configuration for Payment Agent A2A Microservice
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Azure AI Foundry V2 Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_PROJECT_API_KEY = os.getenv("AZURE_AI_PROJECT_API_KEY")
PAYMENT_AGENT_MODEL_DEPLOYMENT = os.getenv("PAYMENT_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# Agent Name and Version (NEW Foundry V2 format: name:version)
PAYMENT_AGENT_NAME = os.getenv("PAYMENT_AGENT_NAME", "payment-a2a")
PAYMENT_AGENT_VERSION = os.getenv("PAYMENT_AGENT_VERSION", "1")

# MCP Server URLs
ACCOUNT_MCP_SERVER_URL = os.getenv("ACCOUNT_MCP_SERVER_URL", "https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")
TRANSACTION_MCP_SERVER_URL = os.getenv("TRANSACTION_MCP_SERVER_URL", "https://transaction.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")
PAYMENT_MCP_SERVER_URL = os.getenv("PAYMENT_MCP_SERVER_URL", "https://payment-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")
CONTACTS_MCP_SERVER_URL = os.getenv("CONTACTS_MCP_SERVER_URL", "https://contacts-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")

# Agent Configuration
PAYMENT_AGENT_CONFIG = {
    "max_completion_tokens": 800,  # More tokens for payment workflows
    "temperature": 0.0,  # Fully deterministic for consistent tool calling
    "parallel_tool_calls": True,  # Enable parallel MCP tool execution
}

# URL FIX: Force external URLs for local development (prevents .internal transformation)
FORCE_EXTERNAL_MCP_URLS = os.getenv("FORCE_EXTERNAL_MCP_URLS", "true").lower() == "true"

# A2A Server Configuration
A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "0.0.0.0")
A2A_SERVER_PORT = int(os.getenv("A2A_SERVER_PORT", "9003"))


def validate_config():
    """Validate required configuration"""
    required = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "PAYMENT_AGENT_NAME": PAYMENT_AGENT_NAME,
        "ACCOUNT_MCP_SERVER_URL": ACCOUNT_MCP_SERVER_URL,
        "TRANSACTION_MCP_SERVER_URL": TRANSACTION_MCP_SERVER_URL,
        "PAYMENT_MCP_SERVER_URL": PAYMENT_MCP_SERVER_URL,
        "CONTACTS_MCP_SERVER_URL": CONTACTS_MCP_SERVER_URL,
    }
    
    missing = [k for k, v in required.items() if not v]
    
    if missing:
        raise ValueError(f"Missing required configuration: {missing}")
    
    print(f"✅ Configuration validated")
    print(f"📍 Azure AI Endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"🤖 Payment Agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")
    print(f"🔧 Force External URLs: {FORCE_EXTERNAL_MCP_URLS}")
    print(f"🔗 MCP Servers:")
    print(f"   Account:     {ACCOUNT_MCP_SERVER_URL}")
    print(f"   Transaction: {TRANSACTION_MCP_SERVER_URL}")
    print(f"   Payment:     {PAYMENT_MCP_SERVER_URL}")
    print(f"   Contacts:    {CONTACTS_MCP_SERVER_URL}")
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    print("✅ PaymentAgent configuration validated")


if __name__ == "__main__":
    validate_config()
    print(f"Payment Agent: {PAYMENT_AGENT_NAME} v{PAYMENT_AGENT_VERSION}")
    print(f"Azure Endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Model: {PAYMENT_AGENT_MODEL_DEPLOYMENT}")
    print(f"Account MCP: {ACCOUNT_MCP_SERVER_URL}")
    print(f"Transaction MCP: {TRANSACTION_MCP_SERVER_URL}")
    print(f"Payment MCP: {PAYMENT_MCP_SERVER_URL}")
    print(f"Contacts MCP: {CONTACTS_MCP_SERVER_URL}")
    print(f"Server: {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
