"""
Configuration for Payment Agent v2 A2A Microservice
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
PAYMENT_AGENT_NAME = os.getenv("PAYMENT_AGENT_NAME", "payment-agent-v2")
PAYMENT_AGENT_VERSION = os.getenv("PAYMENT_AGENT_VERSION", "20")
# MCP Server URL
PAYMENT_UNIFIED_MCP_URL = os.getenv("PAYMENT_UNIFIED_MCP_URL", "http://localhost:8076/mcp")

# Agent Configuration
PAYMENT_AGENT_CONFIG = {
    "max_completion_tokens": 800,  # Allow detailed payment confirmations
    "temperature": 0.0,  # Fully deterministic for consistent tool calling
    "parallel_tool_calls": False,  # Sequential for transfer validation flow
}

# A2A Server Configuration
A2A_SERVER_PORT = int(os.getenv("PAYMENT_AGENT_A2A_PORT", "9003"))
A2A_SERVER_HOST = os.getenv("PAYMENT_AGENT_A2A_HOST", "0.0.0.0")

# Observability
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

# User Mapper (for customer email lookup)
USER_MAPPER_ENABLED = os.getenv("USER_MAPPER_ENABLED", "true").lower() == "true"

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
    validate_config()
    print(f"\n📋 Configuration Summary:")
    print(f"   Agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")
    print(f"   Model: {PAYMENT_AGENT_MODEL_DEPLOYMENT}")
    print(f"   MCP: {PAYMENT_UNIFIED_MCP_URL}")
    print(f"   Port: {A2A_SERVER_PORT}")


if __name__ == "__main__":
    # Test configuration
    validate_config()
    print(f"Payment Agent v2 will run on {PAYMENT_AGENT_HOST}:{PAYMENT_AGENT_PORT}")
    print(f"Using Azure AI Foundry endpoint: {AZURE_AI_PROJECT_ENDPOINT}")