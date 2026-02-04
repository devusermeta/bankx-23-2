"""
Configuration for Escalation Agent A2A Service

Loads configuration from .env file using python-dotenv pattern.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Azure AI Foundry Settings
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AZURE_AI_MODEL_DEPLOYMENT_NAME = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")

# Agent Settings
ESCALATION_AGENT_NAME = os.getenv("ESCALATION_AGENT_NAME", "escalation-a2a")
ESCALATION_AGENT_VERSION = int(os.getenv("ESCALATION_AGENT_VERSION", "1"))
ESCALATION_AGENT_MODEL_DEPLOYMENT = os.getenv("ESCALATION_AGENT_MODEL_DEPLOYMENT", "gpt-5-mini")

# MCP Server URL
ESCALATION_COMMS_MCP_SERVER_URL = os.getenv("ESCALATION_COMMS_MCP_SERVER_URL")

# A2A Server Settings
A2A_SERVER_HOST = os.getenv("A2A_SERVER_HOST", "0.0.0.0")
A2A_SERVER_PORT = int(os.getenv("A2A_SERVER_PORT", "9006"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def validate_config():
    """Validate required configuration"""
    required_vars = {
        "AZURE_AI_PROJECT_ENDPOINT": AZURE_AI_PROJECT_ENDPOINT,
        "ESCALATION_COMMS_MCP_SERVER_URL": ESCALATION_COMMS_MCP_SERVER_URL,
    }
    
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


# Validate on import
validate_config()
