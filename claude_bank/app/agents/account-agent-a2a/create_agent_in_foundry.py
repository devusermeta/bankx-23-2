"""
One-time script to create AccountAgent in Azure AI Foundry WITHOUT MCP tools

Run this script ONCE to create the agent in your Azure AI Foundry project.
After creation, the agent_handler.py will reference this agent and add MCP tools dynamically.

Usage:
    cd claude_bank/app/agents/account-agent-a2a
    python create_agent_in_foundry.py
"""

import asyncio
import os
import sys
from pathlib import Path
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent))
from config import AZURE_AI_PROJECT_ENDPOINT, ACCOUNT_AGENT_MODEL_DEPLOYMENT, ACCOUNT_AGENT_NAME

# Load environment variables
load_dotenv(override=True)

# Read agent instructions from prompts file
PROMPTS_PATH = Path(__file__).parent / "prompts" / "account_agent.md"
try:
    with open(PROMPTS_PATH, "r", encoding="utf-8-sig") as f:
        AGENT_INSTRUCTIONS = f.read()
except UnicodeDecodeError:
    # Fallback to latin-1 if utf-8 fails
    with open(PROMPTS_PATH, "r", encoding="latin-1") as f:
        AGENT_INSTRUCTIONS = f.read()


async def create_account_agent():
    """Create AccountAgent in Azure AI Foundry WITHOUT MCP tools"""
    
    if not AZURE_AI_PROJECT_ENDPOINT or not ACCOUNT_AGENT_MODEL_DEPLOYMENT:
        raise ValueError(
            "Missing required environment variables:\n"
            "  - AZURE_AI_PROJECT_ENDPOINT\n"
            "  - ACCOUNT_AGENT_MODEL_DEPLOYMENT\n"
            "Please ensure .env file is configured correctly."
        )
    
    print("=" * 80)
    print("🚀 Creating AccountAgent in Azure AI Foundry")
    print("=" * 80)
    print(f"Project Endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Model Deployment: {ACCOUNT_AGENT_MODEL_DEPLOYMENT}")
    print(f"Agent Name: {ACCOUNT_AGENT_NAME}")
    print("=" * 80)
    
    # Create AI Project Client with Azure CLI authentication
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=credential
        ) as project_client
    ):
        print("\n📝 Creating agent WITHOUT MCP tools...")
        print("   (Tools will be added dynamically in agent_handler.py)")
        
        # Create agent definition WITHOUT any tools
        # MCP tools will be added dynamically in the handler to avoid duplication
        agent_definition = PromptAgentDefinition(
            model=ACCOUNT_AGENT_MODEL_DEPLOYMENT,
            instructions=AGENT_INSTRUCTIONS,
            # No tools here - they'll be added in agent_handler.py
        )
        
        # Create or update agent version
        agent = await project_client.agents.create_version(
            agent_name=ACCOUNT_AGENT_NAME,
            definition=agent_definition
        )
        
        print("\n✅ Agent created successfully!")
        print("=" * 80)
        print(f"Agent ID: {agent.id}")
        print(f"Agent Name: {agent.name}")
        print(f"Agent Version: {agent.version}")
        print(f"Created At: {agent.created_at}")
        print("=" * 80)
        
        print("\n📋 Next Steps:")
        print("1. Update .env file with the new version (if different):")
        print(f"   ACCOUNT_AGENT_VERSION={agent.version}")
        print("\n2. The agent_handler.py will now add MCP tools dynamically")
        print("\n3. Start the MCP servers:")
        print("   cd claude_bank/app/business-api/python/account && python main.py")
        print("   cd claude_bank/app/business-api/python/limits && python main.py")
        print("\n4. Start the Account Agent A2A server:")
        print("   cd claude_bank/app/agents/account-agent-a2a && python main.py")
        print("=" * 80)
        
        return agent


if __name__ == "__main__":
    try:
        asyncio.run(create_account_agent())
    except Exception as e:
        print(f"\n❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
