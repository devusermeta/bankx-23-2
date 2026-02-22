import os
from dataclasses import dataclass

@dataclass
class AgentConfig:
    AGENT_NAME: str = "PaymentAgent"
    AGENT_VERSION: str = "1.0.0"
    AGENT_ID: str = os.getenv("AGENT_ID", "payment-agent-001")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8102"))
    AGENT_REGISTRY_URL: str = os.getenv("AGENT_REGISTRY_URL", "http://localhost:9000")
    MCP_PAYMENT_URL: str = os.getenv("MCP_PAYMENT_URL", "https://payment-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
    MCP_LIMITS_URL: str = os.getenv("MCP_LIMITS_URL", "https://limits-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
