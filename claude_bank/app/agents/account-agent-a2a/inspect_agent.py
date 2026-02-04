"""Inspect the full agent object structure"""
import asyncio
import os
import json
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv

async def inspect_agent():
    load_dotenv()
    project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
    
    async with (
        AzureCliCredential() as cred,
        AIProjectClient(endpoint=project_endpoint, credential=cred) as client
    ):
        # List agents
        agents = client.agents.list_versions("AccountAgent")
        
        async for agent in agents:
            print("\n=== Agent Object (all attributes) ===")
            print(f"ID: {agent.id}")
            print(f"Name: {agent.name}")
            print(f"Version: {agent.version}")
            
            # Check if there's an assistant_id or similar
            print(f"\nAll attributes:")
            for attr in dir(agent):
                if not attr.startswith('_'):
                    try:
                        value = getattr(agent, attr)
                        if not callable(value):
                            print(f"  {attr}: {value}")
                    except:
                        pass
            
            # Try to get as dict if possible
            try:
                if hasattr(agent, 'as_dict'):
                    print(f"\nas_dict():")
                    print(json.dumps(agent.as_dict(), indent=2))
            except:
                pass
            
            break

if __name__ == "__main__":
    asyncio.run(inspect_agent())
