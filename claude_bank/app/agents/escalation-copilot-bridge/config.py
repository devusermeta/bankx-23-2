"""
Configuration management for Escalation Copilot Bridge.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""
    
    # Service Configuration
    A2A_SERVER_PORT: int = 9006
    SERVICE_NAME: str = "EscalationCopilotBridge"
    AGENT_NAME: str = "EscalationAgent"
    AGENT_TYPE: str = "communication"
    VERSION: str = "1.0.0"
    
    # Power Automate Configuration (Primary method for escalations)
    POWER_AUTOMATE_FLOW_URL: str = os.getenv("POWER_AUTOMATE_FLOW_URL", "")
    POWER_AUTOMATE_TIMEOUT_SECONDS: int = int(os.getenv("POWER_AUTOMATE_TIMEOUT_SECONDS", "60"))
    COPILOT_BOT_NAME: str = os.getenv("COPILOT_BOT_NAME", "EscalationAgent")
    
    # Azure Tenant Configuration
    AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")  # metakaal.com tenant
    POWER_PLATFORM_ENVIRONMENT_ID: Optional[str] = os.getenv("POWER_PLATFORM_ENVIRONMENT_ID", None)
    
    # Agent Registry Configuration
    AGENT_REGISTRY_URL: str = os.getenv("AGENT_REGISTRY_URL", "http://localhost:9000")
    REGISTER_WITH_REGISTRY: bool = os.getenv("REGISTER_WITH_REGISTRY", "true").lower() == "true"
    
    # A2A Configuration
    A2A_TIMEOUT_SECONDS: int = 30
    A2A_MAX_RETRIES: int = 3
    
    # Default Ticket Values
    DEFAULT_TICKET_PRIORITY: str = "normal"
    DEFAULT_TICKET_STATUS: str = "Open"
    DEFAULT_CUSTOMER_ID: str = "CUST-UNKNOWN"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


def validate_settings() -> tuple[bool, list[str]]:
    """
    Validate required settings are configured.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check Power Automate configuration (primary method)
    if not settings.POWER_AUTOMATE_FLOW_URL:
        errors.append("POWER_AUTOMATE_FLOW_URL is not set - required to call Power Automate flow")
    
    if not settings.AZURE_TENANT_ID:
        errors.append("AZURE_TENANT_ID is not set - should be metakaal.com tenant ID")
    
    # Warnings for optional fields
    if not settings.POWER_PLATFORM_ENVIRONMENT_ID:
        errors.append("POWER_PLATFORM_ENVIRONMENT_ID is not set (optional but recommended)")
    
    return len(errors) == 0, errors

