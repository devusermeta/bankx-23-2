"""
Configuration for Supervisor Agent A2A Service
Main routing agent for BankX - routes queries to specialized agents
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
# AZURE OPENAI CONFIGURATION (for cache classification and formatting)
# =============================================================================
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
AZURE_OPENAI_MINI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_MINI_DEPLOYMENT_NAME", "gpt-4.1-mini")

# =============================================================================
# AGENT CONFIGURATION
# =============================================================================
SUPERVISOR_AGENT_NAME = os.getenv("SUPERVISOR_AGENT_NAME", "supervisor-a2a")
SUPERVISOR_AGENT_VERSION = os.getenv("SUPERVISOR_AGENT_VERSION", "1")
SUPERVISOR_AGENT_MODEL_DEPLOYMENT = os.getenv("SUPERVISOR_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# =============================================================================
# SPECIALIST AGENT A2A URLS
# =============================================================================
ACCOUNT_AGENT_A2A_URL = os.getenv("ACCOUNT_AGENT_A2A_URL", "http://localhost:9001")
TRANSACTION_AGENT_A2A_URL = os.getenv("TRANSACTION_AGENT_A2A_URL", "http://localhost:9002")
PAYMENT_AGENT_A2A_URL = os.getenv("PAYMENT_AGENT_A2A_URL", "http://localhost:9003")
PRODINFO_FAQ_AGENT_A2A_URL = os.getenv("PRODINFO_FAQ_AGENT_A2A_URL", "http://localhost:9004")
AI_MONEY_COACH_AGENT_A2A_URL = os.getenv("AI_MONEY_COACH_AGENT_A2A_URL", "http://localhost:9005")
ESCALATION_AGENT_A2A_URL = os.getenv("ESCALATION_AGENT_A2A_URL", "http://localhost:9006")

# =============================================================================
# A2A SERVER CONFIGURATION
# =============================================================================
A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "0.0.0.0")
A2A_SERVER_PORT = int(os.getenv("A2A_SERVER_PORT", "9000"))

# =============================================================================
# LOGGING
# =============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config():
    """Validate required configuration"""
    required = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
    }
    
    missing = [k for k, v in required.items() if not v]
    
    if missing:
        raise ValueError(f"Missing required config: {', '.join(missing)}")
    
    # Log specialist agent URLs
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Specialist Agent URLs:")
    logger.info(f"  Account: {ACCOUNT_AGENT_A2A_URL}")
    logger.info(f"  Transaction: {TRANSACTION_AGENT_A2A_URL}")
    logger.info(f"  Payment: {PAYMENT_AGENT_A2A_URL}")
    logger.info(f"  ProdInfoFAQ: {PRODINFO_FAQ_AGENT_A2A_URL}")
    logger.info(f"  AIMoneyCoach: {AI_MONEY_COACH_AGENT_A2A_URL}")
    logger.info(f"  Escalation: {ESCALATION_AGENT_A2A_URL}")
