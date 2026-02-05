"""
Configuration for Account Agent A2A Microservice
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Azure AI Foundry V2 Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_PROJECT_API_KEY = os.getenv("AZURE_AI_PROJECT_API_KEY")
ACCOUNT_AGENT_MODEL_DEPLOYMENT = os.getenv("ACCOUNT_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# Agent Name and Version (NEW Foundry V2 format: name:version)
ACCOUNT_AGENT_NAME = os.getenv("ACCOUNT_AGENT_NAME", "account-a2a")
ACCOUNT_AGENT_VERSION = os.getenv("ACCOUNT_AGENT_VERSION", "1")

# MCP Server URLs
ACCOUNT_MCP_SERVER_URL = os.getenv("ACCOUNT_MCP_SERVER_URL", "https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")
LIMITS_MCP_SERVER_URL = os.getenv("LIMITS_MCP_SERVER_URL", "https://limits-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp")

# Agent Configuration
ACCOUNT_AGENT_CONFIG = {
    "max_completion_tokens": 500,  # Concise responses for account queries
    "temperature": 0.0,  # Fully deterministic for consistent tool calling
    "parallel_tool_calls": True,  # Enable parallel MCP tool execution
}

# A2A Server Configuration
A2A_SERVER_PORT = int(os.getenv("ACCOUNT_AGENT_A2A_PORT", "9001"))
A2A_SERVER_HOST = os.getenv("ACCOUNT_AGENT_A2A_HOST", "0.0.0.0")

# Observability
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

# User Mapper (for customer email lookup)
USER_MAPPER_ENABLED = os.getenv("USER_MAPPER_ENABLED", "true").lower() == "true"

# Validate required configuration
def validate_config():
    """Validate that all required configuration is present"""
    required = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "ACCOUNT_AGENT_NAME": ACCOUNT_AGENT_NAME,
    }
    
    # Note: AZURE_AI_PROJECT_API_KEY is optional when using AzureCliCredential (az login)
    
    missing = [key for key, value in required.items() if not value]
    
    if missing:
        raise ValueError(
            f"Missing required configuration: {', '.join(missing)}. "
            f"Please check your .env file."
        )
    
    print("✅ Account Agent A2A configuration validated")

if __name__ == "__main__":
    # Test configuration
    validate_config()
    print(f"Account Agent A2A will run on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    print(f"Using Azure AI Foundry endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Agent: {ACCOUNT_AGENT_NAME}:{ACCOUNT_AGENT_VERSION}")
    print(f"Account MCP URL: {ACCOUNT_MCP_SERVER_URL}")
    print(f"Limits MCP URL: {LIMITS_MCP_SERVER_URL}")
