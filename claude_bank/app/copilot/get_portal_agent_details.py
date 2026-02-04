"""
Try different methods to access portal agents and get their actual IDs
"""
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential, DefaultAzureCredential
from app.config.settings import settings
import json

def get_portal_agent_details():
    """Get details about portal agents"""
    
    print("=" * 80)
    print("Checking Portal Agents")
    print("=" * 80)
    
    try:
        credential = AzureCliCredential()
    except:
        credential = DefaultAzureCredential()
    
    client = AIProjectClient(
        credential=credential,
        endpoint=settings.FOUNDRY_PROJECT_ENDPOINT
    )
    
    print(f"\nProject Endpoint: {settings.FOUNDRY_PROJECT_ENDPOINT}\n")
    
    # List all agents
    agents_list = list(client.agents.list())
    
    print(f"Found {len(agents_list)} agents\n")
    
    for agent in agents_list:
        print("-" * 80)
        print(f"Name: {agent.name}")
        print(f"ID: {agent.id}")
        
        # Try to get full details
        try:
            # Check all attributes
            print("\nAll attributes:")
            for attr in dir(agent):
                if not attr.startswith('_'):
                    try:
                        value = getattr(agent, attr)
                        if not callable(value):
                            print(f"  {attr}: {value}")
                    except:
                        pass
        except Exception as e:
            print(f"  Error getting details: {e}")
        
        # Try to serialize to see all fields
        try:
            if hasattr(agent, 'as_dict'):
                print("\nFull object (as_dict):")
                print(json.dumps(agent.as_dict(), indent=2, default=str))
        except Exception as e:
            print(f"  Could not serialize: {e}")
        
        print()
    
    print("=" * 80)

if __name__ == "__main__":
    get_portal_agent_details()
