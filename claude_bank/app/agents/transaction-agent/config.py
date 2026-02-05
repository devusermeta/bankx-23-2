import os
from dataclasses import dataclass

@dataclass
class AgentConfig:
    AGENT_NAME: str = "TransactionAgent"
    AGENT_VERSION: str = "1.0.0"
    AGENT_ID: str = os.getenv("AGENT_ID", "transaction-agent-001")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8101"))
    AGENT_REGISTRY_URL: str = os.getenv("AGENT_REGISTRY_URL", "http://localhost:9000")
    MCP_TRANSACTION_URL: str = os.getenv("MCP_TRANSACTION_URL", "https://transaction.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
