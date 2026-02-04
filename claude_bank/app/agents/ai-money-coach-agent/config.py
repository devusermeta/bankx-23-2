"""Configuration for AIMoneyCoach Agent Service."""
import os
from dataclasses import dataclass

@dataclass
class AgentConfig:
    AGENT_NAME: str = "AIMoneyCoachAgent"
    AGENT_VERSION: str = "1.0.0"
    AGENT_ID: str = os.getenv("AGENT_ID", "ai-money-coach-agent-001")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8104"))
    AGENT_REGISTRY_URL: str = os.getenv("AGENT_REGISTRY_URL", "http://localhost:9000")
    MCP_MONEYCOACH_URL: str = os.getenv("MCP_MONEYCOACH_URL", "http://localhost:8075")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
