"""
Get the EXACT mapping between published agents and their Entra ID identities
Queries Agent Applications to retrieve agentIdentityBlueprint and defaultInstanceIdentity
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
import httpx


def main():
    print("\n" + "="*100)
    print("PUBLISHED AGENT → IDENTITY MAPPING")
    print("="*100 + "\n")
    
    # Load environment
    env_file = Path(__file__).parent / "app" / "copilot" / ".env"
    load_dotenv(env_file, override=True)
    
    # Get config
    foundry_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    
    # Extract details from endpoint
    # Format: https://banking-new-resources.services.ai.azure.com/api/projects/banking-new
    import re
    match = re.match(r'https://([^.]+)\.services\.ai\.azure\.com/api/projects/([^/]+)', foundry_endpoint)
    if not match:
        print("❌ Could not parse FOUNDRY_PROJECT_ENDPOINT")
        return
    
    resource_name = match.group(1)
    project_name = match.group(2)
    
    # Use hardcoded values based on arm_banking_new_resource.json
    # The connection string has wrong subscription!
    subscription_id = "e0783b50-4ca5-4059-83c1-524f39faa624"
    resource_group = "rg-banking-new"
    
    print(f"Configuration:")
    print(f"  Subscription: {subscription_id}")
    print(f"  Resource Group: {resource_group}")
    print(f"  Resource: {resource_name}")
    print(f"  Project: {project_name}")
    print()
    
    # Get access token for ARM
    credential = DefaultAzureCredential()
    token = credential.get_token("https://management.azure.com/.default")
    
    # ARM API endpoint for applications
    applications_url = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{resource_name}/projects/{project_name}/applications"
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "api-version": "2025-10-01-preview"
    }
    
    print("Querying Agent Applications...")
    print(f"URL: {applications_url}")
    print()
    
    try:
        response = httpx.get(applications_url, headers=headers, params=params, timeout=30.0)
        
        if response.status_code == 200:
            applications_data = response.json()
            
            if "value" in applications_data and len(applications_data["value"]) > 0:
                print(f"✅ Found {len(applications_data['value'])} published agent(s)\n")
                print("="*100)
                
                for i, app in enumerate(applications_data["value"], 1):
                    app_name = app.get("name", "Unknown")
                    properties = app.get("properties", {})
                    
                    # Get agents associated with this application
                    agents = properties.get("agents", [])
                    agent_names = [a.get("agentName", "Unknown") for a in agents]
                    
                    # Get identity information
                    identity_blueprint = properties.get("agentIdentityBlueprint", {})
                    default_identity = properties.get("defaultInstanceIdentity", {})
                    
                    print(f"\n{i}. Agent Application: {app_name}")
                    print(f"   {'='*96}")
                    
                    if agent_names:
                        print(f"   Associated Agent(s): {', '.join(agent_names)}")
                    
                    # Show Blueprint ID
                    if identity_blueprint:
                        blueprint_id = identity_blueprint.get("clientId") or identity_blueprint.get("principalId")
                        if blueprint_id:
                            print(f"\n   🔑 Blueprint ID (agentIdentityBlueprint):")
                            print(f"      {blueprint_id}")
                    
                    # Show Object ID
                    if default_identity:
                        object_id = default_identity.get("clientId") or default_identity.get("principalId")
                        if object_id:
                            print(f"\n   🆔 Object ID (defaultInstanceIdentity):")
                            print(f"      {object_id}")
                    
                    # Show base URL
                    base_url = properties.get("baseUrl")
                    if base_url:
                        print(f"\n   🌐 Endpoint: {base_url}")
                    
                    # Show full identity objects for debugging
                    if identity_blueprint:
                        print(f"\n   📋 Full Identity Blueprint:")
                        print(f"      {json.dumps(identity_blueprint, indent=6)}")
                    
                    if default_identity:
                        print(f"\n   📋 Full Default Instance Identity:")
                        print(f"      {json.dumps(default_identity, indent=6)}")
                    
                    print(f"\n   {'='*96}")
                
                # Save full response for inspection
                output_file = Path(__file__).parent / "agent_applications_response.json"
                with open(output_file, "w") as f:
                    json.dump(applications_data, f, indent=2)
                print(f"\n💾 Full response saved to: {output_file}\n")
                
                # Summary
                print("\n" + "="*100)
                print("SUMMARY")
                print("="*100 + "\n")
                
                for app in applications_data["value"]:
                    properties = app.get("properties", {})
                    agents = properties.get("agents", [])
                    identity_blueprint = properties.get("agentIdentityBlueprint", {})
                    default_identity = properties.get("defaultInstanceIdentity", {})
                    
                    for agent in agents:
                        agent_name = agent.get("agentName", "Unknown")
                        blueprint_id = identity_blueprint.get("clientId") or identity_blueprint.get("principalId") or "Not found"
                        object_id = default_identity.get("clientId") or default_identity.get("principalId") or "Not found"
                        
                        print(f"Agent: {agent_name}")
                        print(f"  Blueprint ID (agentIdentityBlueprint.clientId): {blueprint_id}")
                        print(f"  Object ID (defaultInstanceIdentity.clientId):   {object_id}")
                        print()
                
            else:
                print("⚠️  No published agents found")
                print("\nThis means:")
                print("  • No agents have been published yet")
                print("  • All agents are using the project-level identity")
                print(f"  • Project identity: 94a6c115-546a-4911-ba15-dc67cb85c4fc")
                print()
        
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 404:
                print("\nPossible reasons:")
                print("  • Agent Applications API endpoint may have changed")
                print("  • No applications exist yet")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
