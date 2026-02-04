"""
Map Azure AI Foundry Agents to their Entra ID Identities
Shows the relationship between agents and their authentication identities
"""

import os
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from azure.ai.projects import AIProjectClient
from msgraph import GraphServiceClient


async def get_entra_identities(credential):
    """Get all agent identities from Entra ID"""
    from msgraph.generated.service_principals.service_principals_request_builder import ServicePrincipalsRequestBuilder
    
    scopes = ['https://graph.microsoft.com/.default']
    client = GraphServiceClient(credentials=credential, scopes=scopes)
    
    query_params = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
        filter="startswith(displayName, 'banking-new')",
        select=['id', 'appId', 'displayName', 'servicePrincipalType', 'tags']
    )
    request_config = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetRequestConfiguration(
        query_parameters=query_params
    )
    
    service_principals = await client.service_principals.get(request_configuration=request_config)
    return service_principals.value if service_principals else []


def get_foundry_agents(project_client):
    """Get all agents from Azure AI Foundry"""
    agents = []
    for agent in project_client.agents.list():
        agent_dict = agent.as_dict()
        agents.append(agent_dict)
    return agents


async def map_agents_to_identities():
    """Map Azure AI Foundry agents to Entra ID identities"""
    
    print("\n" + "="*100)
    print("Azure AI Foundry Agent → Entra ID Identity Mapping")
    print("="*100 + "\n")
    
    # Load environment
    env_file = Path(__file__).parent / "app" / "copilot" / ".env"
    load_dotenv(env_file, override=True)
    
    foundry_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    tenant_id = os.getenv("AZURE_AUTH_TENANT_ID")
    
    print(f"Project Endpoint: {foundry_endpoint}")
    print(f"Tenant ID: {tenant_id}\n")
    
    # Create credentials
    sync_credential = DefaultAzureCredential()
    async_credential = AsyncDefaultAzureCredential()
    
    try:
        # Get Azure AI Foundry agents
        print("📋 Fetching Azure AI Foundry agents...")
        project_client = AIProjectClient(
            endpoint=foundry_endpoint,
            credential=sync_credential
        )
        foundry_agents = get_foundry_agents(project_client)
        print(f"✅ Found {len(foundry_agents)} Azure AI Foundry agents\n")
        
        # Get Entra ID identities
        print("🔐 Fetching Entra ID agent identities...")
        entra_identities = await get_entra_identities(async_credential)
        print(f"✅ Found {len(entra_identities)} Entra ID identities\n")
        
        print("="*100)
        print("MAPPING RESULTS")
        print("="*100 + "\n")
        
        # Display all Foundry agents
        for agent in foundry_agents:
            agent_name = agent.get('name', 'Unknown')
            agent_id = agent.get('id', 'Unknown')
            
            print(f"{'='*100}")
            print(f"🤖 Azure AI Foundry Agent: {agent_name}")
            print(f"{'='*100}")
            print(f"Agent ID: {agent_id}")
            
            # Check if agent has identity information
            agent_versions = agent.get('versions', {})
            latest_version = agent_versions.get('latest', {})
            
            # Look for identity-related properties
            definition = latest_version.get('definition', {})
            metadata = latest_version.get('metadata', {})
            
            print(f"\nAgent Details:")
            print(f"  Model: {definition.get('model', 'N/A')}")
            print(f"  Version: {latest_version.get('version', 'N/A')}")
            print(f"  Created: {latest_version.get('created_at', 'N/A')}")
            
            # Check for identity metadata
            identity_found = False
            
            if metadata:
                print(f"\n  Metadata:")
                for key, value in metadata.items():
                    print(f"    {key}: {value}")
                    if 'identity' in key.lower() or 'blueprint' in key.lower():
                        identity_found = True
            
            # Look for identity in the full agent dict
            for key in agent.keys():
                if 'identity' in key.lower() or 'blueprint' in key.lower() or 'principal' in key.lower():
                    print(f"\n  {key}: {agent[key]}")
                    identity_found = True
            
            if not identity_found:
                print(f"\n  ⚠️  No direct identity mapping found in agent metadata")
            
            print(f"\n{'='*100}\n")
        
        # Display all Entra identities for reference
        print("\n" + "="*100)
        print("All Available Entra ID Agent Identities")
        print("="*100 + "\n")
        
        for i, identity in enumerate(entra_identities, 1):
            print(f"{i}. {identity.display_name}")
            print(f"   Object ID: {identity.id}")
            print(f"   Blueprint ID: {identity.app_id}")
            print(f"   Type: {identity.service_principal_type}")
            if identity.tags:
                print(f"   Tags: {', '.join(identity.tags)}")
            print()
        
        # Provide recommendations
        print("="*100)
        print("💡 RECOMMENDATIONS")
        print("="*100)
        print()
        print("Based on the findings:")
        print()
        print("1. Look for the identity with tags 'AgentCreatedBy:Foundry, AgenticInstance'")
        print("   → This is likely the managed identity for ALL agents in the project")
        print()
        print("2. Individual agent identities might be:")
        print("   → Created when you enable A2A for specific agents")
        print("   → Managed at the Azure AI Project level, not per-agent")
        print()
        print("3. For A2A configuration, you typically use ONE of these approaches:")
        print("   → Project-level managed identity (shared by all agents)")
        print("   → Agent-specific identity (created during A2A enablement)")
        print()
        print("4. To check agent identity in Azure AI Foundry Portal:")
        print("   → Go to your agent in the portal")
        print("   → Check 'Settings' or 'Identity' tab")
        print("   → Look for 'Managed Identity' or 'Agent Identity' section")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(map_agents_to_identities())
