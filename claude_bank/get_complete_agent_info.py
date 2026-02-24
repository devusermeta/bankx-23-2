"""
Get complete agent information including:
1. Agent ID (from Azure AI Foundry)
2. Blueprint ID and Object ID (from project-level identity or published identity)
3. Create a consolidated JSON file for agent cards
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import httpx

def get_agents_from_foundry(endpoint, credential):
    """Get all agents from Azure AI Foundry"""
    client = AIProjectClient(endpoint, credential=credential)
    agents = list(client.agents.list())
    return agents

def get_published_agents(subscription_id, resource_group, resource_name, project_name, credential):
    """Try to get published agent identities from ARM API"""
    token = credential.get_token("https://management.azure.com/.default")
    
    applications_url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{resource_name}/projects/{project_name}/applications"
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    params = {"api-version": "2025-10-01-preview"}
    
    try:
        response = httpx.get(applications_url, headers=headers, params=params, timeout=30.0)
        if response.status_code == 200:
            data = response.json()
            return data.get("value", [])
        else:
            print(f"⚠️  Could not fetch published agents: {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️  Error fetching published agents: {e}")
        return []

def main():
    print("\n" + "="*100)
    print("COMPLETE AGENT INFORMATION COLLECTOR")
    print("="*100 + "\n")
    
    # Load environment
    env_file = Path(__file__).parent / "app" / "copilot" / ".env"
    load_dotenv(env_file, override=True)
    
    # Configuration
    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    
    # Extract resource info from endpoint
    # Format: https://banking-new-resources.services.ai.azure.com/api/projects/banking-new
    import re
    match = re.match(r'https://([^.]+)\.services\.ai\.azure\.com/api/projects/([^/]+)', endpoint)
    if not match:
        print("❌ Could not parse endpoint")
        return
    
    resource_name = match.group(1)  # banking-new-resources
    project_name = match.group(2)   # banking-new
    
    # Hardcoded Azure details (from your setup)
    subscription_id = "e0783b50-4ca5-4059-83c1-524f39faa624"
    resource_group = "rg-banking-new"
    
    # Project-level identity (default for unpublished agents)
    project_identity_blueprint_id = "94a6c115-546a-4911-ba15-dc67cb85c4fc"
    
    print(f"Configuration:")
    print(f"  Endpoint: {endpoint}")
    print(f"  Resource: {resource_name}")
    print(f"  Project: {project_name}")
    print(f"  Subscription: {subscription_id}")
    print(f"  Resource Group: {resource_group}")
    print(f"  Project Identity (Blueprint): {project_identity_blueprint_id}")
    print()
    
    # Create credential
    credential = DefaultAzureCredential()
    
    # Get agents from Foundry
    print("📋 Fetching agents from Azure AI Foundry...")
    agents = get_agents_from_foundry(endpoint, credential)
    print(f"✅ Found {len(agents)} agents\n")
    
    # Try to get published agents
    print("🔍 Checking for published agent identities...")
    published_agents = get_published_agents(subscription_id, resource_group, resource_name, project_name, credential)
    
    if published_agents:
        print(f"✅ Found {len(published_agents)} published agents with dedicated identities\n")
    else:
        print("ℹ️  No published agents found - using project-level identity for all agents\n")
    
    # Build agent info dictionary
    agent_info = {}
    
    for agent in agents:
        agent_id = agent.id
        agent_name = agent.name
        
        # Check if this agent is published
        published_info = None
        for pub_agent in published_agents:
            pub_name = pub_agent.get("name", "")
            if pub_name == agent_name:
                published_info = pub_agent.get("properties", {})
                break
        
        if published_info:
            # Use published agent's dedicated identity
            blueprint = published_info.get("agentIdentityBlueprint", {})
            instance = published_info.get("defaultInstanceIdentity", {})
            
            blueprint_id = blueprint.get("clientId") or blueprint.get("principalId")
            object_id = instance.get("clientId") or instance.get("principalId")
            base_url = published_info.get("baseUrl", "")
            
            agent_info[agent_name] = {
                "agent_id": agent_id,
                "blueprint_id": blueprint_id,
                "object_id": object_id,
                "endpoint": base_url,
                "status": "published"
            }
        else:
            # Use project-level identity
            agent_info[agent_name] = {
                "agent_id": agent_id,
                "blueprint_id": project_identity_blueprint_id,
                "object_id": project_identity_blueprint_id,  # For unpublished agents, both are the same
                "endpoint": f"{endpoint.rstrip('/')}/agents/{agent_id}",
                "status": "unpublished (using project identity)"
            }
    
    # Display results
    print("="*100)
    print("AGENT INFORMATION")
    print("="*100 + "\n")
    
    for agent_name, info in agent_info.items():
        print(f"{agent_name}:")
        print(f"  Agent ID:     {info['agent_id']}")
        print(f"  Blueprint ID: {info['blueprint_id']}")
        print(f"  Object ID:    {info['object_id']}")
        print(f"  Status:       {info['status']}")
        print(f"  Endpoint:     {info['endpoint']}")
        print()
    
    # Save to JSON file
    output_file = Path(__file__).parent / "agent_identities_updated.json"
    
    # Create clean version without status for agent cards
    clean_info = {}
    for agent_name, info in agent_info.items():
        clean_info[agent_name] = {
            "agent_id": info["agent_id"],
            "blueprint_id": info["blueprint_id"],
            "object_id": info["object_id"],
            "endpoint": info["endpoint"]
        }
    
    with open(output_file, "w") as f:
        json.dump(clean_info, f, indent=2)
    
    print("="*100)
    print(f"✅ Agent information saved to: {output_file}")
    print("="*100)
    print()
    print("💡 NEXT STEPS:")
    print()
    if not published_agents:
        print("⚠️  Your agents are not published yet. They're using the project-level identity.")
        print("   This means ALL agents share the same blueprint_id and object_id.")
        print()
        print("   To create dedicated identities for each agent:")
        print("   1. Go to Azure AI Foundry Portal")
        print("   2. Select your agent")
        print("   3. Click 'Publish' or 'Enable A2A'")
        print("   4. This will create a unique identity for that agent")
        print("   5. Re-run this script to get the updated identities")
        print()
    else:
        print("✅ Your agents are published with dedicated identities!")
        print("   You can now use these IDs in your agent cards.")
    
    print("="*100)

if __name__ == "__main__":
    main()
