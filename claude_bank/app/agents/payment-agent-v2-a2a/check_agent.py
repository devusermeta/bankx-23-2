"""
Quick script to verify payment-agent-v2 exists in Azure AI Foundry and check its configuration
"""
import asyncio
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from dotenv import load_dotenv
import os

load_dotenv()

async def check_agent():
    endpoint = os.getenv('AZURE_PROJECT_ENDPOINT')
    print(f"Checking agents in: {endpoint}")
    print("="*80)
    
    async with AzureCliCredential() as cred:
        async with AIProjectClient(endpoint=endpoint, credential=cred) as client:
            print("\n🔍 Looking for payment-agent-v2...")
            try:
                agents = client.agents.list_versions(agent_name='payment-agent-v2')
                found = False
                async for agent in agents:
                    found = True
                    print(f"\n✅ Found Agent:")
                    print(f"   Name: {agent.name}")
                    print(f"   Version: {agent.version}")
                    print(f"   Model: {agent.model}")
                    print(f"   Created: {agent.created_at}")
                
                if not found:
                    print("\n❌ No versions found for payment-agent-v2")
                    print("\n💡 You may need to run: python create_agent_in_foundry.py")
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    print("="*80)

if __name__ == "__main__":
    asyncio.run(check_agent())
