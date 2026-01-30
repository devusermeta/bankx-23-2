"""
One-time script to create AccountAgent in Azure AI Foundry WITHOUT tools

Run this script ONCE to create the agent in your Azure AI Foundry project.
After creation, add MCP tools via the Foundry portal UI.

Usage:
    cd a2a-agent
    python create_agent_in_foundry_no_tools.py
"""

import asyncio
import os
from pathlib import Path
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read agent instructions from prompts file
PROMPTS_PATH = Path(__file__).parent.parent / "prompts" / "account_agent.md"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    AGENT_INSTRUCTIONS = f.read()


async def create_account_agent():
    """Create AccountAgent in Azure AI Foundry without tools (tools added via portal)"""
    
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    agent_name = os.getenv("ACCOUNT_AGENT_NAME", "AccountAgent")
    
    if not project_endpoint or not model_deployment:
        raise ValueError(
            "Missing required environment variables:\n"
            "  - AZURE_AI_PROJECT_ENDPOINT\n"
            "  - AZURE_AI_MODEL_DEPLOYMENT_NAME\n"
            "Please ensure .env file is configured correctly."
        )
    
    print("=" * 80)
    print("🚀 Creating AccountAgent in Azure AI Foundry (WITHOUT tools)")
    print("=" * 80)
    print(f"Agent Name: {agent_name}")
    print(f"Project Endpoint: {project_endpoint}")
    print(f"Model Deployment: {model_deployment}")
    print("=" * 80)
    
    # Create AI Project Client with Azure CLI authentication
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=project_endpoint,
            credential=credential
        ) as project_client
    ):
        print("\n📝 Creating agent WITHOUT tools...")
        print("   (Tools will be added via Foundry portal UI)")
        
        # Create agent definition WITHOUT tools
        agent_definition = PromptAgentDefinition(
            model=model_deployment,
            instructions=AGENT_INSTRUCTIONS,
            tools=[]  # No tools - will be added via portal UI
        )
        
        # Create or update agent version
        agent = await project_client.agents.create_version(
            agent_name=agent_name,
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
        print("1. Update .env file with these values:")
        print(f"   ACCOUNT_AGENT_NAME={agent.name}")
        print(f"   ACCOUNT_AGENT_VERSION={agent.version}")
        print("\n2. Go to Azure AI Foundry portal:")
        print("   https://ai.azure.com")
        print(f"   Navigate to: Agents → {agent.name}")
        print("\n3. Add MCP server connection in portal:")
        print("   - Click 'Add MCP Server' or 'Add Tools'")
        print("   - Server Label: account-mcp")
        print("   - Server URL: http://localhost:8070/mcp")
        print("   - Select all 5 tools:")
        print("     • getAccountsByUserName")
        print("     • getAccountDetails")
        print("     • getPaymentMethodDetails")
        print("     • checkLimits")
        print("     • getAccountLimits")
        print("   - Approval: 'Never' (auto-approve)")
        print("\n4. Ensure MCP server is running:")
        print("   cd ../mcp-server")
        print("   python main.py")
        print("\n5. Start the A2A server:")
        print("   cd ../a2a-agent")
        print("   python main.py")
        print("\n6. Test the agent:")
        print("   curl http://localhost:9001/.well-known/agent.json")
        print("=" * 80)
        
        return agent


if __name__ == "__main__":
    try:
        asyncio.run(create_account_agent())
    except Exception as e:
        print(f"\n❌ Error creating agent: {e}")
        print("\nPlease ensure:")
        print("  1. You are logged in to Azure CLI: az login")
        print("  2. Your .env file has correct AZURE_AI_PROJECT_ENDPOINT")
        print("  3. You have permissions to create agents in the project")
        raise
