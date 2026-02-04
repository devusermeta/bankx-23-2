"""
Configuration for Azure Purview integration.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class PurviewSettings(BaseSettings):
    """Purview configuration settings"""

    # Azure Purview Account
    PURVIEW_ACCOUNT_NAME: str = "bankx-purview"
    PURVIEW_ENABLED: bool = True

    # Azure Purview Endpoint
    AZURE_PURVIEW_ENDPOINT: Optional[str] = None

    # Lineage tracking configuration
    PURVIEW_TRACK_MCP_CALLS: bool = True
    PURVIEW_TRACK_AGENT_ROUTING: bool = True
    PURVIEW_TRACK_RAG_SEARCHES: bool = True

    # Performance settings
    PURVIEW_ASYNC_MODE: bool = True
    PURVIEW_BATCH_SIZE: int = 10
    PURVIEW_RETRY_COUNT: int = 3

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
purview_settings = PurviewSettings()
