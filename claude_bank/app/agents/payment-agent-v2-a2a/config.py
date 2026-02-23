"""
Payment Agent v2 Configuration

Centralized configuration for agent name, version, and Azure settings.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Azure AI Foundry Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_PROJECT_ENDPOINT")
PAYMENT_AGENT_MODEL_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

# Azure AI Model Deployment (required by agent framework)
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")

# Agent Identity
PAYMENT_AGENT_NAME = os.getenv("AGENT_NAME", "payment-agent-v2")
PAYMENT_AGENT_VERSION = os.getenv("AGENT_VERSION", "2.0.0")

# MCP Server Configuration
PAYMENT_UNIFIED_MCP_URL = os.getenv("PAYMENT_UNIFIED_MCP_URL", "http://localhost:8076/mcp")

# A2A Server Configuration
PAYMENT_AGENT_PORT = int(os.getenv("PAYMENT_AGENT_PORT", "9003"))
PAYMENT_AGENT_HOST = os.getenv("PAYMENT_AGENT_HOST", "0.0.0.0")

def validate_config():
    """Validate that all required configuration is present"""
    required = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "PAYMENT_AGENT_NAME": PAYMENT_AGENT_NAME,
    }
    
    # Note: AZURE_AI_PROJECT_API_KEY is optional when using AzureCliCredential (az login)
    
    missing = [key for key, value in required.items() if not value]
    
    if missing:
        raise ValueError(
            f"Missing required configuration: {', '.join(missing)}. "
            f"Please check your .env file."
        )
    
    print("✅ Payment Agent v2 A2A configuration validated")


if __name__ == "__main__":
    # Test configuration
    validate_config()
    print(f"Payment Agent v2 will run on {PAYMENT_AGENT_HOST}:{PAYMENT_AGENT_PORT}")
    print(f"Using Azure AI Foundry endpoint: {AZURE_AI_PROJECT_ENDPOINT}")