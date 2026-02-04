"""
List all agents in Azure AI Foundry with their actual IDs.
Run this to get the asst_* IDs for agents created in the new portal.
"""
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential, DefaultAzureCredential
from app.config.settings import settings

def list_agents():
    """List all agents and their IDs"""
    print("=" * 80)
    print("Fetching agents from Azure AI Foundry...")
    print("=" * 80)
    
    # Use synchronous credential
    try:
        credential = AzureCliCredential()
    except:
        credential = DefaultAzureCredential()
    
    client = AIProjectClient(
        credential=credential,
        endpoint=settings.FOUNDRY_PROJECT_ENDPOINT
    )
    
    print(f"\nProject Endpoint: {settings.FOUNDRY_PROJECT_ENDPOINT}\n")
    
    # List all agents (synchronous iterator)
    agents_list = list(client.agents.list())
    
    print("AGENTS FOUND:")
    print("-" * 80)
    print(f"{'Name':<40} {'ID (asst_*)':<45}")
    print("-" * 80)
    
    for agent in agents_list:
        print(f"{agent.name:<40} {agent.id:<45}")
    
    print("-" * 80)
    print("\n✅ Copy the 'asst_*' ID for AIMoneyCoachAgent and use it in container_foundry.py")
    print("\nExample:")
    print('  agent_id="asst_XYZ123..."  # Replace with actual ID from above')
    print("=" * 80)

if __name__ == "__main__":
    list_agents()
