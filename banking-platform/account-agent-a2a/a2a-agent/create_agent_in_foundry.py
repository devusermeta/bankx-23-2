"""
One-time script to create AccountAgent in Azure AI Foundry

Run this script ONCE to create the agent in your Azure AI Foundry project.
After creation, the agent will be referenced by the A2A server.

Usage:
    cd a2a-agent
    python create_agent_in_foundry.py
"""

import asyncio
import os
from pathlib import Path
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, MCPTool
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read agent instructions from prompts file
PROMPTS_PATH = Path(__file__).parent.parent / "prompts" / "account_agent.md"
with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
    AGENT_INSTRUCTIONS = f.read()


async def create_account_agent():
    """Create AccountAgent in Azure AI Foundry"""
    
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    model_deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    mcp_url = os.getenv("ACCOUNT_MCP_SERVER_URL")
    
    if not project_endpoint or not model_deployment or not mcp_url:
        raise ValueError(
            "Missing required environment variables:\n"
            "  - AZURE_AI_PROJECT_ENDPOINT\n"
            "  - AZURE_AI_MODEL_DEPLOYMENT_NAME\n"
            "  - ACCOUNT_MCP_SERVER_URL\n"
            "Please ensure .env file is configured correctly."
        )
    
    print("=" * 80)
    print("🚀 Creating AccountAgent in Azure AI Foundry")
    print("=" * 80)
    print(f"Project Endpoint: {project_endpoint}")
    print(f"Model Deployment: {model_deployment}")
    print(f"MCP Server URL: {mcp_url}")
    print("=" * 80)
    
    # Create AI Project Client with Azure CLI authentication
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(
            endpoint=project_endpoint,
            credential=credential
        ) as project_client
    ):
        print("\n📝 Creating agent with MCP tools...")
        
        # Create MCP tool configuration
        mcp_tool = MCPTool(
            server_label="account-mcp",
            server_url=mcp_url,
            require_approval="never",  # Auto-approve tool calls
            allowed_tools=[
                "getAccountsByUserName",
                "getAccountDetails",
                "getPaymentMethodDetails",
                "checkLimits",
                "getAccountLimits"
            ]
        )
        
        # Create agent definition with MCP tools
        agent_definition = PromptAgentDefinition(
            model=model_deployment,
            instructions=AGENT_INSTRUCTIONS,
            tools=[mcp_tool]
        )
        
        # Create or update agent version
        agent = await project_client.agents.create_version(
            agent_name="AccountAgent",
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
        print("1. Update .env file with the following values:")
        print(f"   ACCOUNT_AGENT_NAME={agent.name}")
        print(f"   ACCOUNT_AGENT_VERSION={agent.version}")
        print("\n2. Initialize data (run once):")
        print("   cd ../../scripts")
        print("   python init_data.py")
        print("\n3. Start the MCP server:")
        print("   cd ../account-agent-a2a/mcp-server")
        print("   python main.py")
        print("\n4. Start the A2A server:")
        print("   cd ../a2a-agent")
        print("   python main.py")
        print("\n5. Test the agent:")
        print("   curl http://localhost:9001/.well-known/agent.json")
        print("\n6. Test queries:")
        print('   curl -X POST http://localhost:9001/a2a/invoke \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"messages": [{"role": "user", "content": "What is my account balance?"}]}\'')
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
        print("  4. The MCP server URL is correct (http://localhost:8070/mcp)")
        raise
