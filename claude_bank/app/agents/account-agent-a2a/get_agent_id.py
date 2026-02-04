"""Get the actual Azure agent ID for AccountAgent"""
import asyncio
import os
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

async def get_agent_id():
    load_dotenv()
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    
    async with (
        AzureCliCredential() as cred,
        AIProjectClient(endpoint=project_endpoint, credential=cred) as client
    ):
        # List all versions of AccountAgent
        agents = client.agents.list_versions("AccountAgent")
        
        async for agent in agents:
            print(f"\n✅ Found Agent:")
            print(f"   ID: {agent.id}")
            print(f"   Name: {agent.name}")
            print(f"   Version: {agent.version}")
            print(f"\nAdd this to your .env file:")
            print(f"ACCOUNT_AGENT_ID={agent.id}")
            break

if __name__ == "__main__":
    asyncio.run(get_agent_id())
