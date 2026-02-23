"""
List all agents in Azure AI Foundry project to verify what exists
"""
import asyncio
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import AzureCliCredential
from dotenv import load_dotenv
import os

load_dotenv()

async def list_agents():
    endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
    
    print("=" * 80)
    print("🔍 Listing All Agents in Azure AI Foundry Project")
    print("=" * 80)
    print(f"Project Endpoint: {endpoint}")
    print("=" * 80)
    
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as client
    ):
        print("\n📋 Fetching payment-agent-v2 versions...")
        
        try:
            # list_versions returns an AsyncItemPaged - iterate it
            versions_pager = client.agents.list_versions("payment-agent-v2")
            versions = []
            
            async for version in versions_pager:
                versions.append(version)
            
            if not versions:
                print("❌ No versions found for payment-agent-v2!")
                print("\n💡 You may need to run: python create_agent_in_foundry.py")
                return
            
            print(f"\n✅ Found {len(versions)} version(s) of payment-agent-v2:\n")
            
            for v in versions:
                print(f"Version {v.version}:")
                print(f"   ID: {v.id}")
                print(f"   Name: {v.name}")
                print(f"   Created: {v.created_at}")
                
                # Check if definition has model
                if hasattr(v, 'definition') and v.definition:
                    defn = v.definition
                    model = getattr(defn, 'model', None)
                    print(f"   Model: {model if model else '❌ NO MODEL CONFIGURED!'}")
                    instructions_len = len(getattr(defn, 'instructions', ''))
                    print(f"   Instructions: {instructions_len} chars")
                else:
                    print("   ❌ No definition found!")
                print()
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(list_agents())
