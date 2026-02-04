"""Configuration for ProdInfoFAQ Agent Service."""
import os
from dataclasses import dataclass

@dataclass
class AgentConfig:
    AGENT_NAME: str = "ProdInfoFAQAgent"
    AGENT_VERSION: str = "1.0.0"
    AGENT_ID: str = os.getenv("AGENT_ID", "prodinfo-faq-agent-001")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8103"))
    AGENT_REGISTRY_URL: str = os.getenv("AGENT_REGISTRY_URL", "http://localhost:9000")
    MCP_PRODINFO_URL: str = os.getenv("MCP_PRODINFO_URL", "http://localhost:8074")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
