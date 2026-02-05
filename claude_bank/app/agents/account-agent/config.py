"""
Configuration for Account Agent Service.
"""

import os
from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Configuration for Account Agent."""

    # Agent identity
    AGENT_NAME: str = "AccountAgent"
    AGENT_VERSION: str = "1.0.0"
    AGENT_ID: str = os.getenv("AGENT_ID", "account-agent-001")

    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8100"))

    # Agent Registry
    AGENT_REGISTRY_URL: str = os.getenv(
        "AGENT_REGISTRY_URL", "http://localhost:9000"
    )

    # MCP Services
    MCP_ACCOUNT_URL: str = os.getenv("MCP_ACCOUNT_URL", "https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
    MCP_LIMITS_URL: str = os.getenv("MCP_LIMITS_URL", "https://limits-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")

    # Observability
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Application Insights (optional)
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv(
        "APPLICATIONINSIGHTS_CONNECTION_STRING", ""
    )
