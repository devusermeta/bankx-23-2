"""
Configuration for ProdInfoFAQ MCP Service (UC2)
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """ProdInfoFAQ service configuration"""

    # Environment
    PROFILE: str = "dev"

    # Azure AI Search
    AZURE_SEARCH_ENDPOINT: str
    AZURE_SEARCH_KEY: str
    AZURE_SEARCH_INDEX_NAME: str = "bankx-products-index"

    # Cosmos DB
    COSMOS_ENDPOINT: str
    COSMOS_KEY: str
    COSMOS_DATABASE_NAME: str = "bankx"
    COSMOS_CONTAINER_NAME: str = "support_tickets"

    # Azure OpenAI (for synthesis)
    FOUNDRY_PROJECT_ENDPOINT: str
    FOUNDRY_MODEL_DEPLOYMENT_NAME: str = "gpt-4o"
    AZURE_CLIENT_ID: Optional[str] = None

    # Service Configuration
    PORT: int = 8076
    LOG_LEVEL: str = "INFO"

    # Confidence thresholds
    MIN_CONFIDENCE_THRESHOLD: float = 0.3
    HIGH_CONFIDENCE_THRESHOLD: float = 0.7

    # Search parameters
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
