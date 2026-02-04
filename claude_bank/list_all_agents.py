"""
List all agents in the Azure AI Foundry project
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Load environment
env_file = Path(__file__).parent / "app" / "copilot" / ".env"
load_dotenv(env_file, override=True)

print("\n" + "="*100)
print("List All Agents in Azure AI Foundry Project")
print("="*100 + "\n")

# Get configuration
endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")

print(f"Endpoint: {endpoint[:80]}...\n")

# Create client
credential = DefaultAzureCredential()
client = AIProjectClient(endpoint, credential=credential, logging_enable=True)

print("Fetching all agents...\n")

try:
    # List all agents
    agents = client.agents.list()
    
    agents_list = list(agents)
    print(f"Found {len(agents_list)} agents:\n")
    print("="*100)
    
    for i, agent in enumerate(agents_list, 1):
        print(f"\nAgent {i}:")
        print(f"  ID: {agent.id}")
        print(f"  Name: {agent.name}")
        print(f"  Model: {agent.model}")
        print(f"  Created: {agent.created_at}")
        
        # Check for file search tool
        has_file_search = False
        if agent.tools:
            has_file_search = any(t.get('type') == 'file_search' for t in agent.tools)
        
        print(f"  File Search: {'✅ YES' if has_file_search else '❌ NO'}")
        
        # Check for vector stores
        has_vector_stores = False
        if hasattr(agent, 'tool_resources') and agent.tool_resources:
            if hasattr(agent.tool_resources, 'file_search'):
                fs = agent.tool_resources.file_search
                if hasattr(fs, 'vector_store_ids') and fs.vector_store_ids:
                    has_vector_stores = True
                    print(f"  Vector Stores: {fs.vector_store_ids}")
        
        if has_file_search and not has_vector_stores:
            print(f"  ⚠️ Has file search but NO vector stores!")
        
        print(f"  {'-'*96}")
    
    print(f"\n" + "="*100)
    print("AGENT IDs FOR .env FILE:")
    print("="*100)
    
    for agent in agents_list:
        if "ProdInfo" in agent.name or "Product" in agent.name or "FAQ" in agent.name:
            print(f"PRODINFO_FAQ_AGENT_ID={agent.id}  # {agent.name}")
        elif "Money" in agent.name or "Coach" in agent.name:
            print(f"AI_MONEY_COACH_AGENT_ID={agent.id}  # {agent.name}")
        elif "Supervisor" in agent.name:
            print(f"SUPERVISOR_AGENT_ID={agent.id}  # {agent.name}")
        elif "Account" in agent.name and "Transaction" not in agent.name:
            print(f"ACCOUNT_AGENT_ID={agent.id}  # {agent.name}")
        elif "Transaction" in agent.name:
            print(f"TRANSACTION_AGENT_ID={agent.id}  # {agent.name}")
        elif "Payment" in agent.name:
            print(f"PAYMENT_AGENT_ID={agent.id}  # {agent.name}")
        elif "Escalation" in agent.name or "Comms" in agent.name:
            print(f"ESCALATION_COMMS_AGENT_ID={agent.id}  # {agent.name}")
    
    print("="*100 + "\n")
    
except Exception as e:
    print(f"❌ Error listing agents: {e}")
    import traceback
    traceback.print_exc()
