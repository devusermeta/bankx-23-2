"""
Configuration for AIMoneyCoach Agent A2A Service
UC3: Personal Finance Advisory with Azure AI Foundry file_search
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
AI_MONEY_COACH_AGENT_NAME = os.getenv("AI_MONEY_COACH_AGENT_NAME", "ai-money-coach-a2a")
AI_MONEY_COACH_AGENT_VERSION = os.getenv("AI_MONEY_COACH_AGENT_VERSION", "1")
AI_MONEY_COACH_AGENT_MODEL_DEPLOYMENT = os.getenv("AI_MONEY_COACH_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# =============================================================================
# MCP SERVER CONFIGURATION (Escalation Comms for ticket creation)
# =============================================================================
# No longer using direct MCP connection - using A2A call to Escalation Agent instead

# =============================================================================
# ESCALATION AGENT CONFIGURATION (A2A calls for ticket creation)
# =============================================================================
ESCALATION_AGENT_A2A_URL = os.getenv("ESCALATION_AGENT_A2A_URL", "http://localhost:9006")

# =============================================================================
# A2A SERVER CONFIGURATION
# =============================================================================
A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "0.0.0.0")
A2A_SERVER_PORT = int(os.getenv("A2A_SERVER_PORT", "9005"))

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config():
    """Validate that all required configuration is present"""
    required_vars = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "AI_MONEY_COACH_AGENT_NAME": AI_MONEY_COACH_AGENT_NAME,
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    print("✅ Configuration validated successfully")
    print(f"✅ AIMoneyCoachAgent A2A configuration validated")


if __name__ == "__main__":
    validate_config()
    print(f"Azure AI Project: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Agent: {AI_MONEY_COACH_AGENT_NAME}:{AI_MONEY_COACH_AGENT_VERSION}")
    print(f"Model: {AI_MONEY_COACH_AGENT_MODEL_DEPLOYMENT}")
    print(f"A2A Server: {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    print(f"Escalation MCP: {ESCALATION_COMMS_MCP_SERVER_URL}")
