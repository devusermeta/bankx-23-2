"""
Test using AgentsClient from azure-ai-agents directly with new agent format
"""
import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.ai.agents import AgentsClient
from azure.ai.projects import AIProjectClient

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")

print("="*80)
print("Testing AgentsClient with new agent format")
print("="*80)
print()

credential = AzureCliCredential()

# First, get the agent with AIProjectClient to confirm the ID
project_client = AIProjectClient(
    credential=credential,
    endpoint=FOUNDRY_PROJECT_ENDPOINT
)

agent = project_client.agents.get_version('AIMoneyCoachAgent', '2')
print(f"✅ Agent from AIProjectClient: {agent.id}")
print()

# Now try using AgentsClient directly
print("Testing AgentsClient with versioned agent ID...")
print("-" * 80)

# Extract the base endpoint (remove /api/projects/... part)
base_endpoint = FOUNDRY_PROJECT_ENDPOINT.split('/api/projects')[0]
print(f"Base endpoint: {base_endpoint}")

agents_client = AgentsClient(
    endpoint=base_endpoint + "/api",  # AgentsClient expects base endpoint
    credential=credential
)

print(f"Attempting to get agent with ID: {agent.id}")

try:
    retrieved_agent = agents_client.get_agent(agent.id)
    print(f"✅ SUCCESS! Retrieved agent: {retrieved_agent.id}")
    print(f"   Name: {retrieved_agent.name}")
    print(f"   Model: {retrieved_agent.model}")
    
    # Try to create a thread
    print()
    print("Testing thread creation...")
    thread = agents_client.create_thread()
    print(f"✅ Thread created: {thread.id}")
    
    # Try to create a message
    print()
    print("Testing message creation...")
    message = agents_client.create_message(
        thread_id=thread.id,
        role="user",
        content="What is financial planning?"
    )
    print(f"✅ Message created: {message.id}")
    
    # Try to create a run
    print()
    print("Testing run creation...")
    run = agents_client.create_run(
        thread_id=thread.id,
        assistant_id=agent.id  # Using the versioned ID
    )
    print(f"✅ Run created: {run.id}")
    print(f"   Status: {run.status}")
    
    print()
    print("="*80)
    print("🎉 SUCCESS! AgentsClient works with new agent format!")
    print("="*80)
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
