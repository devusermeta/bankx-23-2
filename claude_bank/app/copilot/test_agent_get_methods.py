"""
Test using the correct get() and get_version() methods
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.ai.projects import AIProjectClient

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")

print("="*80)
print("Testing client.agents.get() and get_version() methods")
print("="*80)
print()

# Initialize client
credential = AzureCliCredential()
client = AIProjectClient(
    credential=credential,
    endpoint=FOUNDRY_PROJECT_ENDPOINT
)

print(f"Project Endpoint: {FOUNDRY_PROJECT_ENDPOINT}")
print()

# Method 1: Get agent by plain name using get()
print("Method 1: client.agents.get('AIMoneyCoachAgent')")
print("-" * 80)
try:
    agent = client.agents.get('AIMoneyCoachAgent')
    print(f"✅ SUCCESS!")
    print(f"Agent ID: {agent.id}")
    print(f"Agent Name: {agent.name}")
    print(f"Agent Type: {agent.object}")
    if hasattr(agent, 'versions'):
        print(f"Versions: {agent.versions.keys()}")
        latest_version_id = agent.versions['latest'].get('id')
        print(f"Latest Version ID: {latest_version_id}")
except Exception as e:
    print(f"❌ FAILED: {e}")
print()

# Method 2: Get specific version using get_version()
print("Method 2: client.agents.get_version('AIMoneyCoachAgent', '2')")
print("-" * 80)
try:
    agent_version = client.agents.get_version('AIMoneyCoachAgent', '2')
    print(f"✅ SUCCESS!")
    print(f"Version ID: {agent_version.id}")
    print(f"Version Name: {agent_version.name}")
    print(f"Version Number: {agent_version.version}")
    print(f"Model: {agent_version.definition.model if hasattr(agent_version, 'definition') else 'N/A'}")
    
    # This is the ID we should use!
    print()
    print(f"🎯 USE THIS ID IN YOUR CODE: {agent_version.id}")
except Exception as e:
    print(f"❌ FAILED: {e}")
print()

# Method 3: Try with AzureAIAgentClient directly
print("Method 3: Test if AzureAIAgentClient works with versioned ID")
print("-" * 80)
try:
    from azure.ai.agents import AzureAIAgentClient
    from azure.identity import get_bearer_token_provider
    from azure.identity._credentials.azure_cli import AzureCliCredential as AsyncAzureCliCredential
    
    # Create async credential for AzureAIAgentClient
    async_cred = AsyncAzureCliCredential()
    
    # Try with versioned ID
    agent_id = "AIMoneyCoachAgent:2"
    
    client_kwargs = {
        "thread_id": "test-thread",
        "project_endpoint": FOUNDRY_PROJECT_ENDPOINT,
        "async_credential": async_cred,
        "agent_id": agent_id,
        "model_deployment_name": os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
    }
    
    print(f"Attempting to create AzureAIAgentClient with agent_id='{agent_id}'...")
    agent_client = AzureAIAgentClient(**client_kwargs)
    print(f"✅ AzureAIAgentClient created successfully!")
    print(f"  Agent ID: {agent_client.agent_id}")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
print()

print("="*80)
print("CONCLUSION:")
print("="*80)
print("If get_version() works, we can use: AIMoneyCoachAgent:2")
print("Update container_foundry.py to use this format!")
