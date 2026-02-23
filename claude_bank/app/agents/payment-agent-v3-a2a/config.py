"""
Configuration for Payment Agent V3 A2A Microservice
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Azure AI Foundry Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_PROJECT_API_KEY = os.getenv("AZURE_AI_PROJECT_API_KEY")
PAYMENT_AGENT_MODEL_DEPLOYMENT = os.getenv("PAYMENT_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# Agent Name and Version (Foundry V2 format: name:version)
PAYMENT_AGENT_NAME = os.getenv("PAYMENT_AGENT_NAME", "payment-agent-v3")
PAYMENT_AGENT_VERSION = os.getenv("PAYMENT_AGENT_VERSION", "1")

# MCP Server URL (single payment-unified MCP server)
PAYMENT_UNIFIED_MCP_URL = os.getenv(
    "PAYMENT_UNIFIED_MCP_URL",
    "https://payment-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp"
)

# Agent Configuration
PAYMENT_AGENT_CONFIG = {
    "max_completion_tokens": 800,
    "temperature": 0.0,       # Fully deterministic for consistent tool calling
    "parallel_tool_calls": False,  # Sequential: prepareTransfer THEN wait, executeTransfer THEN done
}

# A2A Server Configuration
A2A_SERVER_PORT = int(os.getenv("PAYMENT_AGENT_A2A_PORT", "9004"))
A2A_SERVER_HOST = os.getenv("PAYMENT_AGENT_A2A_HOST", "0.0.0.0")

# Observability
APPLICATIONINSIGHTS_CONNECTION_STRING = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")


def validate_config():
    """Validate that all required configuration is present"""
    required = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "PAYMENT_AGENT_NAME": PAYMENT_AGENT_NAME,
    }

    missing = [key for key, value in required.items() if not value]

    if missing:
        raise ValueError(
            f"Missing required configuration: {', '.join(missing)}. "
            f"Please check your .env file."
        )

    print("✅ Payment Agent V3 A2A configuration validated")


if __name__ == "__main__":
    validate_config()
    print(f"Payment Agent V3 A2A will run on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    print(f"Using Azure AI Foundry endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")
    print(f"Payment MCP URL: {PAYMENT_UNIFIED_MCP_URL}")
