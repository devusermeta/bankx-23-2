"""
Verify that AccountAgent exists in Azure AI Foundry

This script checks if the AccountAgent was successfully created by listing all agents
and attempting to retrieve it.
"""

import asyncio
import os
from dotenv import load_dotenv
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential


async def verify_agent():
    """Check if AccountAgent exists in Foundry"""
    
    # Load environment variables
    load_dotenv()
    
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    
    if not project_endpoint:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT not found in .env")
    
    print("=== Verifying AccountAgent in Azure AI Foundry ===\n")
    print(f"Project: {project_endpoint}\n")
    
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(endpoint=project_endpoint, credential=credential) as project_client,
    ):
        try:
            # Try to list all agent versions
            print("Listing all agent versions...")
            agent_name = "AccountAgent"
            
            # Get specific version
            try:
                agent_version = await project_client.agents.get_version(
                    agent_name=agent_name,
                    agent_version=1
                )
                print(f"\n✅ Found agent: {agent_version.name} version {agent_version.version}")
                print(f"   ID: {agent_version.id}")
                print(f"   Model: {agent_version.model}")
                return True
            except Exception as e:
                print(f"\n❌ Agent '{agent_name}' version 1 not found")
                print(f"   Error: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error accessing project: {e}")
            return False


if __name__ == "__main__":
    asyncio.run(verify_agent())
