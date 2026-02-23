"""
One-time script to create Payment Agent v2 in Azure AI Foundry WITHOUT MCP tools

Run this script ONCE to create the agent in your Azure AI Foundry project.
After creation, the agent_handler.py will reference this agent and add MCP tools dynamically.

Usage:
    cd claude_bank/app/agents/payment-agent-v2-a2a
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
from config import AZURE_AI_PROJECT_ENDPOINT, PAYMENT_AGENT_MODEL_DEPLOYMENT, PAYMENT_AGENT_NAME

# Load environment variables
load_dotenv(override=True)

# Read agent instructions from prompts file
PROMPTS_PATH = Path(__file__).parent / "prompts" / "payment_agent.md"
try:
    with open(PROMPTS_PATH, "r", encoding="utf-8-sig") as f:
        AGENT_INSTRUCTIONS = f.read()
except UnicodeDecodeError:
    # Fallback to latin-1 if utf-8 fails
    with open(PROMPTS_PATH, "r", encoding="latin-1") as f:
        AGENT_INSTRUCTIONS = f.read()


async def create_payment_agent():
    """Create Payment Agent v2 in Azure AI Foundry WITHOUT MCP tools"""
    
    if not AZURE_AI_PROJECT_ENDPOINT or not PAYMENT_AGENT_MODEL_DEPLOYMENT:
        raise ValueError(
            "Missing required environment variables:\n"
            "  - AZURE_PROJECT_ENDPOINT\n"
            "  - AZURE_OPENAI_DEPLOYMENT\n"
            "Please ensure .env file is configured correctly."
        )
    
    print("=" * 80)
    print("🚀 Creating Payment Agent v2 in Azure AI Foundry")
    print("=" * 80)
    print(f"Project Endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Model Deployment: {PAYMENT_AGENT_MODEL_DEPLOYMENT}")
    print(f"Agent Name: {PAYMENT_AGENT_NAME}")
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
            model=PAYMENT_AGENT_MODEL_DEPLOYMENT,
            instructions=AGENT_INSTRUCTIONS,
            # No tools here - they'll be added in agent_handler.py
        )
        
        # Create or update agent version
        agent = await project_client.agents.create_version(
            agent_name=PAYMENT_AGENT_NAME,
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
        print(f"   PAYMENT_AGENT_VERSION={agent.version}")
        print("\n2. The agent_handler.py will now add MCP tools dynamically")
        print("\n3. Start the unified MCP server:")
        print("   cd claude_bank/app/business-api/python/payment-unified && python main.py")
        print("\n4. Start the Payment Agent v2 A2A server:")
        print("   cd claude_bank/app/agents/payment-agent-v2-a2a && python main.py")
        print("=" * 80)
        print("   ngrok http 8076")
        print("\n5. Update .env with ngrok URL:")
        print("   PAYMENT_UNIFIED_MCP_URL=https://your-ngrok-id.ngrok.io/mcp")
        print("\n6. Start the Payment Agent v2 A2A server:")
        print("   cd claude_bank/app/agents/payment-agent-v2-a2a && python main.py")
        print("=" * 80)

        return agent


if __name__ == "__main__":
    asyncio.run(create_payment_agent())
