"""
Create AccountAgent in Azure AI Foundry with A2A support

This script creates the AccountAgent in Azure AI Foundry (cloud service) and configures it
for A2A (Agent-to-Agent) communication.

Prerequisites:
- Azure AI Foundry project created
- Model deployment configured (GPT-4 or similar)
- Azure CLI authenticated: run `az login`
- .env file with AZURE_AI_PROJECT_ENDPOINT and AZURE_AI_MODEL_DEPLOYMENT_NAME

Run this ONCE to create the agent in Foundry:
    uv run python create_account_agent_in_foundry.py
"""

import asyncio
import os
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv


async def create_account_agent():
    """Create AccountAgent in Azure AI Foundry"""
    
    # Load environment variables
    load_dotenv()
    
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    if not project_endpoint or not model_deployment:
        raise ValueError(
            "Missing required environment variables:\n"
            "  AZURE_AI_PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com\n"
            "  AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4\n"
        )
    
    # Load instructions from markdown file
    instructions_file = Path(__file__).parent / "prompts" / "account_agent.md"
    if instructions_file.exists():
        with open(instructions_file, "r", encoding="utf-8") as f:
            instructions = f.read()
    else:
        instructions = """You are AccountAgent, a specialized banking assistant for account management.

You help customers with:
- Account balance inquiries
- Account details and information
- Payment method management
- Transaction limits

You have access to MCP tools for:
- Account data (balances, details, payment methods)
- Transaction limits (daily limits, remaining balance)

Always be helpful, accurate, and professional when handling customer inquiries."""
    
    print("=== Creating AccountAgent in Azure AI Foundry ===\n")
    print(f"Project: {project_endpoint}")
    print(f"Model: {model_deployment}\n")
    
    # Initialize Azure credentials and project client
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
    ):
        # Create versioned agent in Foundry
        agent_name = "AccountAgent"
        
        print(f"Creating agent '{agent_name}'...")
        
        azure_agent = await project_client.agents.create_version(
            agent_name=agent_name,
            definition=PromptAgentDefinition(
                model=model_deployment,
                instructions=instructions,
            ),
        )
        
        # Display agent details
        print("\n✅ Agent Created Successfully!")
        print(f"  Name: {azure_agent.name}")
        print(f"  Version: {azure_agent.version}")
        print(f"  ID: {azure_agent.id}")
        
        print("\n=== Next Steps ===")
        print("1. Update your .env file with:")
        print(f"   ACCOUNT_AGENT_NAME={azure_agent.name}")
        print(f"   ACCOUNT_AGENT_VERSION={azure_agent.version}")
        print("")
        print("2. Start the A2A service:")
        print("   uv run python main.py")
        print("")
        print("3. Test the agent:")
        print("   curl http://localhost:9001/agent-card")
        
        return azure_agent


async def main():
    """Entry point"""
    try:
        await create_account_agent()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Run 'az login' to authenticate")
        print("2. Check your .env file has correct values")
        print("3. Verify your Azure account has access to the Foundry project")
        raise


if __name__ == "__main__":
    asyncio.run(main())
