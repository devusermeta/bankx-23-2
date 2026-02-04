"""
Test if portal agents (AIMoneyCoachAgent:2) work with newer API versions
or if there's a different method to access them.
"""

import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from dotenv import load_dotenv
from azure.identity import AzureCliCredential
from azure.ai.projects import AIProjectClient

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Get settings from env
FOUNDRY_PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")

print("="*80)
print("Testing New Agent Format Access Methods")
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

# Method 1: Try to get agent by versioned ID directly
print("Method 1: Get agent by versioned ID (AIMoneyCoachAgent:2)")
print("-" * 80)
try:
    # Try with the versioned ID format
    agent = client.agents.get_agent("AIMoneyCoachAgent:2")
    print(f"✅ SUCCESS!")
    print(f"Agent ID: {agent.id}")
    print(f"Agent Name: {agent.name}")
    print(f"Model: {getattr(agent, 'model', 'N/A')}")
except Exception as e:
    print(f"❌ FAILED: {e}")
print()

# Method 2: Try to get agent by plain name
print("Method 2: Get agent by plain name (AIMoneyCoachAgent)")
print("-" * 80)
try:
    agent = client.agents.get_agent("AIMoneyCoachAgent")
    print(f"✅ SUCCESS!")
    print(f"Agent ID: {agent.id}")
    print(f"Agent Name: {agent.name}")
except Exception as e:
    print(f"❌ FAILED: {e}")
print()

# Method 3: List agents and inspect their structure
print("Method 3: List agents and check for alternative access methods")
print("-" * 80)
try:
    agents_list = list(client.agents.list())
    ai_money_coach = next((a for a in agents_list if a.name == "AIMoneyCoachAgent"), None)
    
    if ai_money_coach:
        print(f"Found AIMoneyCoachAgent:")
        print(f"  ID: {ai_money_coach.id}")
        print(f"  Name: {ai_money_coach.name}")
        
        # Check if there's a versions attribute
        if hasattr(ai_money_coach, 'versions'):
            print(f"  Versions: {ai_money_coach.versions}")
            latest = ai_money_coach.versions.get('latest', {})
            print(f"  Latest Version ID: {latest.get('id')}")
            print(f"  Latest Version Number: {latest.get('version')}")
            
            # Try to access with version ID
            version_id = latest.get('id')
            if version_id:
                print()
                print(f"Attempting to get agent with version ID: {version_id}")
                try:
                    versioned_agent = client.agents.get_agent(version_id)
                    print(f"  ✅ SUCCESS with version ID!")
                    print(f"  Agent ID: {versioned_agent.id}")
                except Exception as e2:
                    print(f"  ❌ FAILED: {e2}")
except Exception as e:
    print(f"❌ FAILED: {e}")
print()

# Method 4: Check if there's a different client or API for accessing portal agents
print("Method 4: Check AgentsClient methods")
print("-" * 80)
try:
    print("Available methods on client.agents:")
    for method in dir(client.agents):
        if not method.startswith('_'):
            print(f"  - {method}")
except Exception as e:
    print(f"❌ FAILED: {e}")
print()

# Method 5: Try with API version parameter
print("Method 5: Trying different approaches with AgentClient parameters")
print("-" * 80)
try:
    from azure.ai.projects.models import Agent
    from azure.ai.agents import AzureAIAgentClient
    
    # Check if AzureAIAgentClient accepts version parameter
    print("Checking AzureAIAgentClient initialization parameters...")
    import inspect
    sig = inspect.signature(AzureAIAgentClient.__init__)
    print("  Parameters:")
    for param_name, param in sig.parameters.items():
        if param_name != 'self':
            print(f"    - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'}")
except Exception as e:
    print(f"❌ FAILED: {e}")
print()

print("="*80)
print("SUMMARY:")
print("="*80)
print("We need to find a way to:")
print("1. Either get agents with versioned IDs (AIMoneyCoachAgent:2)")
print("2. Or find the internal asst_* ID that portal agents might have")
print("3. Or use a newer API version that supports this format")
print("4. Or create agents programmatically to get asst_* IDs")
