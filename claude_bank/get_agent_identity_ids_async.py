"""
Retrieve Agent Identity details from Microsoft Entra ID (ASYNC VERSION)
Extracts Blueprint ID and Object ID for Azure AI Foundry agent identities
"""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from azure.identity.aio import DefaultAzureCredential
from msgraph import GraphServiceClient
from msgraph.generated.service_principals.service_principals_request_builder import ServicePrincipalsRequestBuilder


async def get_agent_identities():
    """Retrieve agent identity details from Microsoft Entra ID"""
    
    print("\n" + "="*100)
    print("Microsoft Entra ID - Agent Identity Details Retrieval (ASYNC)")
    print("="*100 + "\n")
    
    # Load environment
    env_file = Path(__file__).parent / "app" / "copilot" / ".env"
    load_dotenv(env_file, override=True)
    
    # Configuration
    TENANT_ID = os.getenv("AZURE_AUTH_TENANT_ID")
    
    if not TENANT_ID:
        print("❌ AZURE_AUTH_TENANT_ID not found in .env file")
        print("Please add: AZURE_AUTH_TENANT_ID=your-tenant-id")
        return
    
    print(f"Tenant ID: {TENANT_ID}\n")
    
    try:
        # Create async credential
        credential = DefaultAzureCredential()
        
        # Create Graph client
        scopes = ['https://graph.microsoft.com/.default']
        client = GraphServiceClient(credentials=credential, scopes=scopes)
        
        print("✅ Connected to Microsoft Graph API\n")
        print("Fetching agent identities (service principals)...\n")
        
        # Query service principals with filter for agent identities
        # Note: Using startswith only as 'contains' is not supported by Graph API
        query_params = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetQueryParameters(
            filter="startswith(displayName, 'banking-new')",
            select=['id', 'appId', 'displayName', 'servicePrincipalType', 'tags']
        )
        request_config = ServicePrincipalsRequestBuilder.ServicePrincipalsRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )
        
        # AWAIT the async call
        service_principals = await client.service_principals.get(request_configuration=request_config)
        
        if not service_principals or not service_principals.value:
            print("❌ No agent identities found with current filter")
            print("\nTrying to list all service principals (this may take a moment)...")
            
            # Fallback: Get all service principals
            all_sps = await client.service_principals.get()
            
            if all_sps and all_sps.value:
                print(f"\nFound {len(all_sps.value)} service principals. Filtering for agent identities...")
                
                agent_identities = [
                    sp for sp in all_sps.value 
                    if sp.display_name and ('AgentIdentity' in sp.display_name or 'banking-new' in sp.display_name)
                ]
                
                if agent_identities:
                    print(f"Filtered to {len(agent_identities)} agent identities\n")
                    service_principals.value = agent_identities
                else:
                    print("❌ No agent identities found in service principals")
                    return
            else:
                print("❌ Could not retrieve service principals")
                return
        
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
                print(f"\n💡 This appears to be an agent identity for the project")
            
            print(f"\n📋 Configuration for A2A Agent Card:")
            print(f"   blueprint_id: {sp.app_id}")
            print(f"   object_id: {sp.id}")
        
        print(f"\n{'='*100}\n")
        print("✅ Successfully retrieved agent identity details")
        print("\n💡 Use these IDs in your A2A agent card configuration")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n💡 Troubleshooting:")
        print("1. Ensure you have Microsoft Graph API permissions")
        print("2. Run: az login --tenant <your-tenant-id>")
        print("3. Ensure your account has permission to read service principals")
        print("4. Required permissions: Application.Read.All or Directory.Read.All")


if __name__ == "__main__":
    asyncio.run(get_agent_identities())
