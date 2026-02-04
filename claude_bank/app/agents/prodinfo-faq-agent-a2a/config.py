"""
Configuration for ProdInfoFAQ Agent A2A Service
UC2: Product Information & FAQ with Azure AI Foundry file_search
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# =============================================================================
# AZURE AI FOUNDRY CONFIGURATION
# =============================================================================
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
PRODINFO_FAQ_AGENT_NAME = os.getenv("PRODINFO_FAQ_AGENT_NAME", "prodinfo-faq-a2a")
PRODINFO_FAQ_AGENT_VERSION = os.getenv("PRODINFO_FAQ_AGENT_VERSION", "1")
PRODINFO_FAQ_AGENT_MODEL_DEPLOYMENT = os.getenv("PRODINFO_FAQ_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# =============================================================================
# ESCALATION AGENT A2A CONFIGURATION (for ticket creation)
# =============================================================================
ESCALATION_AGENT_A2A_URL = os.getenv("ESCALATION_AGENT_A2A_URL", "http://localhost:9006")

# =============================================================================
# A2A SERVER CONFIGURATION
# =============================================================================
A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "0.0.0.0")
A2A_SERVER_PORT = int(os.getenv("A2A_SERVER_PORT", "9004"))

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config():
    """Validate that all required configuration is present"""
    required_vars = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "PRODINFO_FAQ_AGENT_NAME": PRODINFO_FAQ_AGENT_NAME,
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    print("✅ Configuration validated successfully")
    print(f"✅ ProdInfoFAQAgent A2A configuration validated")


if __name__ == "__main__":
    validate_config()
    print(f"Azure AI Project: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Agent: {PRODINFO_FAQ_AGENT_NAME}:{PRODINFO_FAQ_AGENT_VERSION}")
    print(f"Model: {PRODINFO_FAQ_AGENT_MODEL_DEPLOYMENT}")
    print(f"A2A Server: {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    print(f"Escalation MCP: {ESCALATION_COMMS_MCP_SERVER_URL}")
