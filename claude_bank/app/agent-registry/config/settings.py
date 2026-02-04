"""Configuration settings for agent registry."""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Agent registry settings."""

    # Application
    app_name: str = "BankX Agent Registry"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 9000

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_ttl_seconds: int = 300  # 5 minutes

    # Cosmos DB
    cosmos_endpoint: Optional[str] = None
    cosmos_key: Optional[str] = None
    cosmos_database_name: str = "bankx_db"
    cosmos_container_name: str = "agent_registry"
    use_cosmos: bool = False

    # Health Check
    health_check_enabled: bool = True
    health_check_interval_seconds: int = 30
    stale_agent_threshold_minutes: int = 5

    # Authentication
    auth_enabled: bool = True
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 3600

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # CORS
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True

    # Azure
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        # Load from environment
        settings = cls()

        # Override with specific env vars if present
        if os.getenv("AGENT_REGISTRY_PORT"):
            settings.port = int(os.getenv("AGENT_REGISTRY_PORT"))

        if os.getenv("REDIS_URL"):
            settings.redis_url = os.getenv("REDIS_URL")

        if os.getenv("AZURE_COSMOS_ENDPOINT"):
            settings.cosmos_endpoint = os.getenv("AZURE_COSMOS_ENDPOINT")
            settings.use_cosmos = True

        if os.getenv("AZURE_COSMOS_KEY"):
            settings.cosmos_key = os.getenv("AZURE_COSMOS_KEY")

        if os.getenv("A2A_JWT_SECRET_KEY"):
            settings.jwt_secret_key = os.getenv("A2A_JWT_SECRET_KEY")

        if os.getenv("A2A_HEALTH_CHECK_ENABLED"):
            settings.health_check_enabled = os.getenv("A2A_HEALTH_CHECK_ENABLED").lower() == "true"

        if os.getenv("LOG_LEVEL"):
            settings.log_level = os.getenv("LOG_LEVEL")

        return settings


# Global settings instance
settings = Settings.from_env()
