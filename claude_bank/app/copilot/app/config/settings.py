import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_files() -> List[str]:
    """Get list of environment files to load based on current environment."""
    env = os.getenv("PROFILE")

    if env:
        print(f"Loading environment files for environment: {env}")
    else:
        print("No environment specified, environment variables only configuration will be used.")
        return []
    
    env = env.lower()
    # List of env files to try (in order of priority - later files override earlier ones)
    env_files = [
        ".env",  # Base environment file
        f".env.{env}"  # Environment-specific file
        
    ]
    
    # Filter to only existing files
    return [f for f in env_files if os.path.exists(f)]    

class Settings(BaseSettings):
    """Application settings loaded from environment or environment-specific .env files.

    Settings are loaded in the following order (later sources override earlier ones):
    1. Default values defined in the class
    2. Environment variables
    3. Base .env file
    4. Environment-specific .env file (e.g., .env.development, .env.production)
    
    The environment is determined by the ENVIRONMENT environment variable or defaults to 'development'.
    """

    # app-level
    APP_NAME: str = "Copilot Multi Agent Chat API"
    PROFILE: str = Field(default="prod")

    #Logging and monitoring
    APPLICATIONINSIGHTS_CONNECTION_STRING: str | None = Field(default=None)
    ENABLE_OTEL : bool = Field(default=True)
  
    # Azure AI Foundry configuration
    # maps to environment variables described by the user

    AZURE_DOCUMENT_INTELLIGENCE_SERVICE: str | None = Field(default=None)
    FOUNDRY_PROJECT_ENDPOINT: str | None = Field(default=None)
    FOUNDRY_MODEL_DEPLOYMENT_NAME: str = Field(default="gpt-4o")
    AZURE_OPENAI_ENDPOINT: str | None = Field(default=None)
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME: str = Field(default="gpt-4o")
    AZURE_OPENAI_MINI_DEPLOYMENT_NAME: str = Field(default="gpt-4.1-mini")  # For cache formatting
    
    # OpenTelemetry configuration
    OTEL_RESOURCE_ATTRIBUTES: str = Field(default="service.name=Copilot Multi Agent Chat API,service.version=1.0.0")
    
    # Azure AI Agent IDs (DEPRECATED - OLD FORMAT - Use AGENT_NAME instead)
    SUPERVISOR_AGENT_ID: str | None = Field(default=None)
    PAYMENT_AGENT_ID: str | None = Field(default=None)
    TRANSACTION_AGENT_ID: str | None = Field(default=None)
    ACCOUNT_AGENT_ID: str | None = Field(default=None)

    # Azure AI Agent Names (NEW FORMAT - name:version)
    # These agents should already exist in Azure AI Foundry
    SUPERVISOR_AGENT_NAME: str | None = Field(default=None)
    SUPERVISOR_AGENT_VERSION: str = Field(default="1")
    ACCOUNT_AGENT_NAME: str | None = Field(default=None)
    ACCOUNT_AGENT_VERSION: str = Field(default="1")
    TRANSACTION_AGENT_NAME: str | None = Field(default=None)
    TRANSACTION_AGENT_VERSION: str = Field(default="1")
    PAYMENT_AGENT_NAME: str | None = Field(default=None)
    PAYMENT_AGENT_VERSION: str = Field(default="1")

    # Azure services
    AZURE_STORAGE_ACCOUNT: str | None = Field(default=None)
    AZURE_STORAGE_CONTAINER: str | None = Field(default="content")

    #MCP servers - UC1 (Financial Operations)
    ACCOUNT_MCP_URL: str | None= Field(default=None,description="MCP server URL (required)", min_length=1)
    TRANSACTION_MCP_URL: str | None= Field(default=None,description="MCP server URL (required)", min_length=1)
    PAYMENT_MCP_URL: str | None= Field(default=None,description="MCP server URL (required)", min_length=1)
    LIMITS_MCP_URL: str | None = Field(default=None, description="Limits MCP server URL")
    CONTACTS_MCP_URL: str | None = Field(default=None, description="Contacts MCP server URL")
    AUDIT_MCP_URL: str | None = Field(default=None, description="Audit MCP server URL")
    CACHE_MCP_URL: str | None = Field(default=None, description="Cache MCP server URL (port 8079)")

    #MCP servers - UC2 & UC3 (Product FAQ & Money Coach)
    PRODINFO_FAQ_MCP_URL: str | None = Field(default=None, description="ProdInfoFAQ MCP server URL (port 8076)")
    AI_MONEY_COACH_MCP_URL: str | None = Field(default=None, description="AIMoneyCoach MCP server URL (port 8077)")
    ESCALATION_COMMS_MCP_URL: str | None = Field(default=None, description="EscalationComms MCP server URL (port 8078)")
    
    # Agent IDs (DEPRECATED - OLD FORMAT - Use AGENT_NAME instead)
    PRODINFO_FAQ_AGENT_ID: str | None = Field(default=None, description="ProdInfoFAQ Agent ID")
    AI_MONEY_COACH_AGENT_ID: str | None = Field(default=None, description="AIMoneyCoach Agent ID")
    ESCALATION_COMMS_AGENT_ID: str | None = Field(default=None, description="EscalationComms Agent ID")
    
    # Agent Names (NEW FORMAT - name:version)
    PRODINFO_FAQ_AGENT_NAME: str | None = Field(default=None)
    PRODINFO_FAQ_AGENT_VERSION: str = Field(default="3")
    AI_MONEY_COACH_AGENT_NAME: str | None = Field(default=None)
    AI_MONEY_COACH_AGENT_VERSION: str = Field(default="2")
    ESCALATION_AGENT_NAME: str | None = Field(default=None)
    ESCALATION_AGENT_VERSION: str = Field(default="1")
    
    # Vector Store IDs (for knowledge base agents)
    PRODINFO_FAQ_VECTOR_STORE_IDS: str | None = Field(default=None, description="Comma-separated vector store IDs for ProdInfoFAQ")
    AI_MONEY_COACH_VECTOR_STORE_IDS: str | None = Field(default=None, description="Comma-separated vector store IDs for AIMoneyCoach")

    # Azure AI Search (for UC2 & UC3 RAG)
    AZURE_AI_SEARCH_ENDPOINT: str | None = Field(default=None, description="Azure AI Search endpoint URL")
    AZURE_AI_SEARCH_KEY: str | None = Field(default=None, description="Azure AI Search admin key")
    AZURE_AI_SEARCH_INDEX_UC2: str = Field(default="bankx-products-faq", description="AI Search index for UC2")
    AZURE_AI_SEARCH_INDEX_UC3: str = Field(default="bankx-money-coach", description="AI Search index for UC3")

    # Azure AI Foundry Content Understanding (for grounding validation)
    AZURE_CONTENT_UNDERSTANDING_ENDPOINT: str | None = Field(default=None, description="Azure AI Foundry Content Understanding endpoint")

    # Azure CosmosDB (for ticket storage)
    AZURE_COSMOSDB_ENDPOINT: str | None = Field(default=None, description="Azure CosmosDB endpoint")
    AZURE_COSMOSDB_DATABASE: str = Field(default="bankx", description="CosmosDB database name")
    AZURE_COSMOSDB_CONTAINER_TICKETS: str = Field(default="support_tickets", description="CosmosDB container for tickets")

    # Azure Communication Services (for email)
    AZURE_COMMUNICATION_SERVICES_ENDPOINT: str | None = Field(default=None, description="Azure Communication Services endpoint")
    AZURE_COMMUNICATION_SERVICES_EMAIL_FROM: str = Field(default="support@bankx.com", description="From email address")

    # Support for User Assigned Managed Identity: empty means system-managed
    AZURE_CLIENT_ID: str  | None = Field(default="system-managed-identity")

    # Authentication - Microsoft Entra ID
    AZURE_AUTH_TENANT_ID: str | None = Field(default=None, description="BankX Tenant ID for authentication")
    AZURE_APP_CLIENT_ID: str | None = Field(default=None, description="App Registration Client ID")

    # Phase 1: A2A Migration Configuration (NEW - Jan 2026)
    USE_A2A_FOR_ACCOUNT_AGENT: bool = Field(default=False, description="Feature flag: Enable A2A for AccountAgent")
    USE_A2A_FOR_TRANSACTION_AGENT: bool = Field(default=False, description="Feature flag: Enable A2A for TransactionAgent")
    USE_A2A_FOR_PAYMENT_AGENT: bool = Field(default=False, description="Feature flag: Enable A2A for PaymentAgent")
    
    ACCOUNT_AGENT_A2A_URL: str = Field(default="http://localhost:9001", description="AccountAgent A2A microservice URL")
    TRANSACTION_AGENT_A2A_URL: str = Field(default="http://localhost:9002", description="TransactionAgent A2A microservice URL")
    PAYMENT_AGENT_A2A_URL: str = Field(default="http://localhost:9003", description="PaymentAgent A2A microservice URL")
    PRODINFO_FAQ_AGENT_A2A_URL: str = Field(default="http://localhost:9004", description="ProdInfo FAQ Agent A2A microservice URL")
    AI_MONEY_COACH_AGENT_A2A_URL: str = Field(default="http://localhost:9005", description="AI Money Coach Agent A2A microservice URL")
    ESCALATION_COMMS_AGENT_A2A_URL: str = Field(default="http://localhost:9006", description="Escalation Comms Agent A2A microservice URL")
    
    AZURE_AI_PROJECT_ENDPOINT: str | None = Field(default=None, description="Azure AI Foundry V2 project endpoint (for A2A agents)")
    AZURE_AI_PROJECT_API_KEY: str | None = Field(default=None, description="Azure AI Foundry V2 API key (for A2A agents)")

    model_config = SettingsConfigDict(
        env_file=get_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()