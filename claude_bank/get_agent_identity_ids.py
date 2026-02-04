"""
Retrieve Agent Identity details from Microsoft Entra ID
Extracts Blueprint ID and Object ID for Azure AI Foundry agent identities
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from msgraph import GraphServiceClient
from msgraph.generated.service_principals.service_principals_request_builder import ServicePrincipalsRequestBuilder

# Load environment
env_file = Path(__file__).parent / "app" / "copilot" / ".env"
load_dotenv(env_file, override=True)

print("\n" + "="*100)
print("Microsoft Entra ID - Agent Identity Details Retrieval")
print("="*100 + "\n")

# Configuration
TENANT_ID = os.getenv("AZURE_AUTH_TENANT_ID")

if not TENANT_ID:
    print("❌ AZURE_AUTH_TENANT_ID not found in .env file")
    print("Please add: AZURE_AUTH_TENANT_ID=your-tenant-id")
    exit(1)

print(f"Tenant ID: {TENANT_ID}\n")

try:
    # Create credential
    credential = DefaultAzureCredential()
    
    # Create Graph client
    scopes = ['https://graph.microsoft.com/.default']
    client = GraphServiceClient(credentials=credential, scopes=scopes)
    
    print("✅ Connected to Microsoft Graph API\n")
    print("Fetching agent identities (service principals)...\n")
    
    # Query service principals with filter for agent identities
    # Looking for service principals with "AgentIdentity" in the name
    query_params = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
        filter="startswith(displayName, 'banking-new-resource') or contains(displayName, 'AgentIdentity')",
        select=['id', 'appId', 'displayName', 'servicePrincipalType', 'tags']
    )
    request_config = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetRequestConfiguration(
        query_parameters=query_params
    )
    
    service_principals = client.service_principals.get(request_configuration=request_config)
    
    if not service_principals or not service_principals.value:
        print("❌ No agent identities found")
        print("\nTrying to list all service principals (this may take a moment)...")
        
        # Fallback: Get all service principals
        all_sps = client.service_principals.get()
        
        if all_sps and all_sps.value:
            print(f"\nFound {len(all_sps.value)} service principals. Filtering for agent identities...")
            
            agent_identities = [
                sp for sp in all_sps.value 
                if sp.display_name and ('AgentIdentity' in sp.display_name or 'banking-new' in sp.display_name)
            ]
            
            if agent_identities:
                service_principals.value = agent_identities
            else:
                print("❌ No agent identities found in service principals")
                exit(1)
        else:
            print("❌ Could not retrieve service principals")
            exit(1)
    
    print(f"Found {len(service_principals.value)} agent identity/identities:\n")
    print("="*100)
    
    for i, sp in enumerate(service_principals.value, 1):
        print(f"\n{'='*100}")
        print(f"Agent Identity {i}: {sp.display_name}")
        print(f"{'='*100}")
        print(f"Object ID (Principal ID):  {sp.id}")
        print(f"Blueprint ID (App ID):     {sp.app_id}")
        print(f"Service Principal Type:    {sp.service_principal_type}")
        
        if sp.tags:
            print(f"Tags:                      {', '.join(sp.tags)}")
        
        # Extract agent name if possible
        agent_name = sp.display_name
        if 'AgentIdentity' in agent_name:
            # Try to extract the actual agent name
            # e.g., "banking-new-resource-banking-new-AgentIdentity" -> extract meaningful part
            parts = agent_name.split('-')
            if 'AgentIdentity' in parts[-1]:
                # This is a generic agent identity
                print(f"\n💡 This appears to be a generic agent identity for the project")
        
        print(f"\n{'='*100}")
    
    # Print summary for .env configuration
    print(f"\n{'='*100}")
    print("📋 CONFIGURATION SUMMARY FOR A2A AGENT CARDS:")
    print(f"{'='*100}\n")
    
    for sp in service_principals.value:
        agent_name = sp.display_name.replace('banking-new-resource-', '').replace('-AgentIdentity', '')
        print(f"# {sp.display_name}")
        print(f"AGENT_IDENTITY_OBJECT_ID={sp.id}")
        print(f"AGENT_IDENTITY_BLUEPRINT_ID={sp.app_id}")
        print(f"AGENT_NAME={agent_name}")
        print()
    
    print("="*100)
    print("\n✅ Agent identity details retrieved successfully!")
    print("\n💡 Copy the Blueprint ID and Object ID to your A2A agent card configuration")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n💡 Troubleshooting:")
    print("1. Ensure you have Microsoft Graph API permissions")
    print("2. Run: az login --tenant <your-tenant-id>")
    print("3. Ensure your account has permission to read service principals")
    print("4. Required permissions: Application.Read.All or Directory.Read.All")
