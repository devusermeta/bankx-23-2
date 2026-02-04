"""
Find the mapping between Azure AI Foundry Agents and their Entra ID Identities
Uses multiple approaches to establish the relationship
"""

import os
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from azure.ai.projects import AIProjectClient
from msgraph import GraphServiceClient
from msgraph.generated.service_principals.service_principals_request_builder import ServicePrincipalsRequestBuilder


async def get_foundry_agents_with_timestamps(project_client):
    """Get all agents from Azure AI Foundry with creation timestamps"""
    agents = []
    for agent in project_client.agents.list():
        agent_dict = agent.as_dict()
        
        # Extract creation timestamp from latest version
        latest_version = agent_dict.get('versions', {}).get('latest', {})
        created_at_unix = latest_version.get('created_at')
        
        if created_at_unix:
            created_at = datetime.fromtimestamp(created_at_unix)
        else:
            created_at = None
        
        agents.append({
            'name': agent_dict.get('name'),
            'id': agent_dict.get('id'),
            'version': latest_version.get('version'),
            'created_at': created_at,
            'created_at_unix': created_at_unix
        })
    
    return agents


async def get_entra_identities_with_timestamps(credential):
    """Get all agent identities from Entra ID with creation timestamps"""
    scopes = ['https://graph.microsoft.com/.default']
    client = GraphServiceClient(credentials=credential, scopes=scopes)
    
    query_params = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
        filter="startswith(displayName, 'banking-new')",
        select=['id', 'appId', 'displayName', 'servicePrincipalType', 'tags', 'appDisplayName']
    )
    request_config = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetRequestConfiguration(
        query_parameters=query_params
    )
    
    service_principals = await client.service_principals.get(request_configuration=request_config)
    
    identities = []
    if service_principals and service_principals.value:
        for sp in service_principals.value:
            identities.append({
                'display_name': sp.display_name,
                'object_id': sp.id,
                'blueprint_id': sp.app_id,
                'type': sp.service_principal_type,
                'tags': sp.tags if sp.tags else [],
                'created_at': None,  # Creation time not available via Graph API
                'app_display_name': sp.app_display_name if hasattr(sp, 'app_display_name') else None
            })
    
    return identities


def match_by_timestamp(agents, identities, tolerance_seconds=300):
    """Match agents to identities by creation timestamp (within tolerance)"""
    matches = []
    
    for agent in agents:
        if not agent['created_at']:
            continue
        
        for identity in identities:
            if not identity['created_at']:
                continue
            
            # Calculate time difference
            time_diff = abs((agent['created_at'] - identity['created_at']).total_seconds())
            
            if time_diff <= tolerance_seconds:
                matches.append({
                    'agent_name': agent['name'],
                    'agent_created': agent['created_at'],
                    'identity_name': identity['display_name'],
                    'identity_created': identity['created_at'],
                    'object_id': identity['object_id'],
                    'blueprint_id': identity['blueprint_id'],
                    'time_diff_seconds': time_diff,
                    'confidence': 'HIGH' if time_diff < 60 else 'MEDIUM'
                })
    
    return matches


def match_by_name_heuristics(agents, identities):
    """Try to match by name patterns"""
    matches = []
    
    for agent in agents:
        agent_name_lower = agent['name'].lower()
        
        for identity in identities:
            identity_name_lower = identity['display_name'].lower()
            
            # Check if agent name appears in identity name
            if agent_name_lower in identity_name_lower:
                matches.append({
                    'agent_name': agent['name'],
                    'identity_name': identity['display_name'],
                    'object_id': identity['object_id'],
                    'blueprint_id': identity['blueprint_id'],
                    'match_type': 'NAME_IN_IDENTITY'
                })
    
    return matches


def identify_project_identity(identities):
    """Identify the project-level managed identity"""
    for identity in identities:
        tags = identity.get('tags', [])
        if 'AgentCreatedBy:Foundry' in tags and 'AgenticInstance' in tags:
            return identity
    return None


async def query_azure_activity_log():
    """Query Azure Activity Log for agent publish events"""
    print("\n📋 Querying Azure Activity Log...")
    print("⚠️  Note: This requires Azure Monitor permissions\n")
    
    try:
        import subprocess
        
        # Get activity log for the last 7 days
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        
        cmd = [
            "az", "monitor", "activity-log", "list",
            "--resource-group", "rg-banking-new",
            "--start-time", start_time.isoformat(),
            "--end-time", end_time.isoformat(),
            "--query", "[?contains(operationName.value, 'Agent') || contains(operationName.value, 'Identity')].{time:eventTimestamp, operation:operationName.value, resource:resourceId, status:status.value}",
            "-o", "json"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            events = json.loads(result.stdout)
            print(f"✅ Found {len(events)} relevant events\n")
            return events
        else:
            print(f"❌ Failed to query activity log: {result.stderr}\n")
            return []
    except Exception as e:
        print(f"❌ Error querying activity log: {e}\n")
        return []


async def main():
    print("\n" + "="*100)
    print("AGENT → IDENTITY MAPPING DISCOVERY")
    print("="*100 + "\n")
    
    # Load environment
    env_file = Path(__file__).parent / "app" / "copilot" / ".env"
    load_dotenv(env_file, override=True)
    
    foundry_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    
    # Create credentials
    sync_credential = DefaultAzureCredential()
    async_credential = AsyncDefaultAzureCredential()
    
    try:
        # Step 1: Get Azure AI Foundry agents
        print("STEP 1: Fetching Azure AI Foundry Agents")
        print("-" * 100)
        project_client = AIProjectClient(endpoint=foundry_endpoint, credential=sync_credential)
        agents = await get_foundry_agents_with_timestamps(project_client)
        
        print(f"✅ Found {len(agents)} agents:\n")
        for agent in agents:
            created = agent['created_at'].strftime('%Y-%m-%d %H:%M:%S') if agent['created_at'] else 'Unknown'
            print(f"   • {agent['name']:<20} Created: {created}")
        
        # Step 2: Get Entra ID identities
        print("\n\nSTEP 2: Fetching Entra ID Agent Identities")
        print("-" * 100)
        identities = await get_entra_identities_with_timestamps(async_credential)
        
        print(f"✅ Found {len(identities)} identities:\n")
        for identity in identities:
            created = identity['created_at'].strftime('%Y-%m-%d %H:%M:%S') if identity['created_at'] else 'Unknown'
            print(f"   • {identity['display_name']:<50} Created: {created}")
        
        # Step 3: Identify project-level identity
        print("\n\nSTEP 3: Identifying Project-Level Managed Identity")
        print("-" * 100)
        project_identity = identify_project_identity(identities)
        
        if project_identity:
            print(f"✅ Project Identity: {project_identity['display_name']}")
            print(f"   Object ID: {project_identity['object_id']}")
            print(f"   Blueprint ID: {project_identity['blueprint_id']}")
            print(f"   Type: {project_identity['type']}")
            print(f"   Tags: {', '.join(project_identity['tags'])}")
            print(f"\n   💡 This identity is used by ALL agents by default")
        else:
            print("⚠️  No project-level identity found")
        
        # Step 4: Match by timestamp
        print("\n\nSTEP 4: Matching Agents to Identities by Creation Time")
        print("-" * 100)
        timestamp_matches = match_by_timestamp(agents, identities)
        
        if timestamp_matches:
            print(f"✅ Found {len(timestamp_matches)} potential matches:\n")
            for match in timestamp_matches:
                print(f"🔗 {match['agent_name']} → {match['identity_name']}")
                print(f"   Agent Created:    {match['agent_created']}")
                print(f"   Identity Created: {match['identity_created']}")
                print(f"   Time Difference:  {match['time_diff_seconds']:.1f} seconds")
                print(f"   Object ID:        {match['object_id']}")
                print(f"   Blueprint ID:     {match['blueprint_id']}")
                print(f"   Confidence:       {match['confidence']}")
                print()
        else:
            print("⚠️  No timestamp-based matches found")
            print("   This likely means agents use the project-level identity\n")
        
        # Step 5: Match by name heuristics
        print("\nSTEP 5: Matching by Name Patterns")
        print("-" * 100)
        name_matches = match_by_name_heuristics(agents, identities)
        
        if name_matches:
            print(f"✅ Found {len(name_matches)} name-based matches:\n")
            for match in name_matches:
                print(f"🔗 {match['agent_name']} → {match['identity_name']}")
                print(f"   Object ID:    {match['object_id']}")
                print(f"   Blueprint ID: {match['blueprint_id']}")
                print()
        else:
            print("⚠️  No name-based matches found\n")
        
        # Step 6: Query activity log
        print("\nSTEP 6: Azure Activity Log Analysis")
        print("-" * 100)
        activity_events = await query_azure_activity_log()
        
        if activity_events:
            for event in activity_events[:10]:  # Show first 10
                print(f"   {event['time']} | {event['operation']} | {event['status']}")
        
        # Final recommendations
        print("\n\n" + "="*100)
        print("RECOMMENDATIONS")
        print("="*100 + "\n")
        
        print("Based on the analysis:")
        print()
        
        if project_identity:
            print(f"1. DEFAULT IDENTITY (used by all agents):")
            print(f"   Object ID:    {project_identity['object_id']}")
            print(f"   Blueprint ID: {project_identity['blueprint_id']}")
            print(f"   → Use this for A2A agent cards unless you have agent-specific identities")
            print()
        
        if timestamp_matches:
            print(f"2. AGENT-SPECIFIC IDENTITIES found:")
            for match in timestamp_matches:
                if match['confidence'] == 'HIGH':
                    print(f"   {match['agent_name']}:")
                    print(f"      Object ID:    {match['object_id']}")
                    print(f"      Blueprint ID: {match['blueprint_id']}")
            print()
        
        print("3. TO VERIFY IN AZURE PORTAL:")
        print("   • Go to Azure AI Foundry → Your Agent → Settings/Identity")
        print("   • Check which identity is assigned")
        print("   • This is the authoritative source")
        print()
        
        print("4. FOR A2A CONFIGURATION:")
        print("   • If no agent-specific identities found → Use project identity")
        print("   • If agent-specific identities exist → Use those for each agent")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
