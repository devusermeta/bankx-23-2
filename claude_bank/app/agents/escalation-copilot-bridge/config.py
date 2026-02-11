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
    
    # Microsoft Graph API Configuration
    AZURE_CLIENT_ID: str = os.getenv("AZURE_CLIENT_ID", "")
    AZURE_CLIENT_SECRET: str = os.getenv("AZURE_CLIENT_SECRET", "")
    AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")
    
    # Microsoft Graph API Scopes
    GRAPH_SCOPE: str = "https://graph.microsoft.com/.default"
    GRAPH_API_ENDPOINT: str = "https://graph.microsoft.com/v1.0"
    
    # Excel Configuration
    EXCEL_SITE_ID: Optional[str] = os.getenv("EXCEL_SITE_ID", None)  # SharePoint site ID
    EXCEL_DRIVE_ID: Optional[str] = os.getenv("EXCEL_DRIVE_ID", None)  # Drive ID (OneDrive/SharePoint)
    EXCEL_FILE_PATH: str = os.getenv("EXCEL_FILE_PATH", "/tickets.xlsx")  # Path relative to drive root
    EXCEL_TABLE_NAME: str = os.getenv("EXCEL_TABLE_NAME", "TicketsTable")
    EXCEL_USER_ID: Optional[str] = os.getenv("EXCEL_USER_ID", None)  # User ID for OneDrive access
    
    # Email Configuration
    EMAIL_SENDER_ADDRESS: str = os.getenv("EMAIL_SENDER_ADDRESS", "")  # Your Outlook email
    EMAIL_SENDER_NAME: str = os.getenv("EMAIL_SENDER_NAME", "BankX Support Team")
    
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
    
    # Check Azure AD configuration
    if not settings.AZURE_CLIENT_ID:
        errors.append("AZURE_CLIENT_ID is not set")
    if not settings.AZURE_CLIENT_SECRET:
        errors.append("AZURE_CLIENT_SECRET is not set")
    if not settings.AZURE_TENANT_ID:
        errors.append("AZURE_TENANT_ID is not set")
    
    # Check email configuration
    if not settings.EMAIL_SENDER_ADDRESS:
        errors.append("EMAIL_SENDER_ADDRESS is not set")
    
    # Check Excel configuration - need either Site ID or User ID
    if not settings.EXCEL_DRIVE_ID:
        if not settings.EXCEL_SITE_ID and not settings.EXCEL_USER_ID:
            errors.append("Either EXCEL_SITE_ID or EXCEL_USER_ID must be set")
    
    return len(errors) == 0, errors
