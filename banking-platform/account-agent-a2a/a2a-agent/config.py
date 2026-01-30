"""
Configuration management for Account A2A Agent
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Azure AI Foundry Settings
    azure_ai_project_endpoint: str
    azure_ai_model_deployment_name: str
    
    # Agent Settings
    account_agent_name: str = "AccountAgent"
    account_agent_version: str = "1"
    
    # MCP Server Settings
    account_mcp_server_url: str = "http://localhost:8070/mcp"
    
    # A2A Server Settings
    a2a_server_host: str = "0.0.0.0"
    a2a_server_port: int = 9001
    
    # Observability
    applicationinsights_connection_string: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
