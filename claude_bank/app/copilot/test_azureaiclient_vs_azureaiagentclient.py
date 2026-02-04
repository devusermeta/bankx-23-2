"""
Test if AzureAIClient works with new agent format (vs AzureAIAgentClient)
"""
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from agent_framework.azure import AzureAIClient  # ← Different from AzureAIAgentClient!

# Load environment
load_dotenv(Path(__file__).parent / ".env")

FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")

print("="*80)
print("Testing AzureAIClient (vs AzureAIAgentClient) with new agent format")
print("="*80)
print()

async def test_azure_ai_client():
    """Test using AzureAIClient like the sample code does"""
    
    async with (
        AzureCliCredential() as credential,
        AIProjectClient(endpoint=FOUNDRY_PROJECT_ENDPOINT, credential=credential) as project_client
    ):
        # Get agent using AIProjectClient
        print("Step 1: Get agent from AIProjectClient")
        print("-" * 80)
        agent = await project_client.agents.get_version('AIMoneyCoachAgent', '2')
        print(f"✅ Agent retrieved: {agent.id}")
        print(f"   Name: {agent.name}")
        print(f"   Version: {agent.version}")
        print()
        
        # Create AzureAIClient (what the sample uses)
        print("Step 2: Create AzureAIClient with agent name and version")
        print("-" * 80)
        print("Note: Using AzureAIClient, NOT AzureAIAgentClient")
        
        chat_client = AzureAIClient(
            project_client=project_client,
            agent_name=agent.name,
            agent_version=agent.version
        )
        print(f"✅ AzureAIClient created")
        print(f"   Type: {type(chat_client)}")
        print()
        
        # Create agent instance using create_agent()
        print("Step 3: Use create_agent() method to get ChatAgent")
        print("-" * 80)
        
        async with chat_client.create_agent(
            name=agent.name,
            instructions="You are a helpful financial advisor."
        ) as chat_agent:
            print(f"✅ ChatAgent created via create_agent()")
            print(f"   Type: {type(chat_agent)}")
            print(f"   Name: {chat_agent.name}")
            print()
            
            # Test the agent
            print("Step 4: Test agent with a query")
            print("-" * 80)
            query = "What is financial planning?"
            print(f"User: {query}")
            
            response = await chat_agent.run(query)
            print(f"\n✅ Agent Response:")
            print(f"{response.text}")
            print()
        
        print("="*80)
        print("🎉 SUCCESS! AzureAIClient works with new agent format!")
        print("="*80)
        print()
        print("KEY DIFFERENCE:")
        print("❌ Your code uses: AzureAIAgentClient(agent_id='AIMoneyCoachAgent:2')")
        print("✅ Sample uses:    AzureAIClient(agent_name='AIMoneyCoachAgent', agent_version='2')")
        print()
        print("AzureAIClient.create_agent() internally handles the new format correctly!")

if __name__ == "__main__":
    try:
        asyncio.run(test_azure_ai_client())
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
