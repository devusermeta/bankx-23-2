"""
One-time script to create payment-agent-v3 in Azure AI Foundry.

Run this ONCE to register the agent. After creation, agent_handler.py
will reference this agent and add MCP tools dynamically at runtime.

Usage:
    cd claude_bank/app/agents/payment-agent-v3-a2a
    cp .env.example .env     # edit with your values
    python create_agent_in_foundry.py
"""

import asyncio
import sys
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from config import AZURE_AI_PROJECT_ENDPOINT, PAYMENT_AGENT_MODEL_DEPLOYMENT, PAYMENT_AGENT_NAME

load_dotenv(override=True)

PROMPTS_PATH = Path(__file__).parent / "prompts" / "payment_agent.md"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    AGENT_INSTRUCTIONS = f.read()


async def create_payment_agent_v3():
    """Create payment-agent-v3 in Azure AI Foundry WITHOUT MCP tools attached.
    
    Tools are added dynamically in agent_handler.py to avoid duplication.
    """
    if not AZURE_AI_PROJECT_ENDPOINT or not PAYMENT_AGENT_MODEL_DEPLOYMENT:
        raise ValueError(
            "Missing required environment variables:\n"
            "  - AZURE_AI_PROJECT_ENDPOINT\n"
            "  - PAYMENT_AGENT_MODEL_DEPLOYMENT\n"
            "Please ensure .env file is configured correctly."
        )

    print("=" * 80)
    print("🚀 Creating payment-agent-v3 in Azure AI Foundry")
    print("=" * 80)
    print(f"Project Endpoint : {AZURE_AI_PROJECT_ENDPOINT}")
    print(f"Model Deployment : {PAYMENT_AGENT_MODEL_DEPLOYMENT}")
    print(f"Agent Name       : {PAYMENT_AGENT_NAME}")
    print("=" * 80)

    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=credential
        ) as project_client
    ):
        print("\n📝 Creating agent WITHOUT MCP tools...")
        print("   (Tools are added dynamically in agent_handler.py)")

        agent_definition = PromptAgentDefinition(
            model=PAYMENT_AGENT_MODEL_DEPLOYMENT,
            instructions=AGENT_INSTRUCTIONS,
            # No tools here - added dynamically at runtime
        )

        agent = await project_client.agents.create_version(
            agent_name=PAYMENT_AGENT_NAME,
            definition=agent_definition
        )

        print(f"\n✅ Agent created successfully!")
        print(f"   Name    : {agent.name}")
        print(f"   Version : {agent.version}")
        print(f"   ID      : {agent.id}")
        print("\n📋 Next steps:")
        print(f"   1. Update .env: PAYMENT_AGENT_VERSION={agent.version}")
        print(f"   2. Run: python main.py")
        print(f"   3. Test: curl http://localhost:9004/health")

        return agent


if __name__ == "__main__":
    asyncio.run(create_payment_agent_v3())
