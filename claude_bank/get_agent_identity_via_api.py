"""
Get Agent Identity Mapping via Azure REST APIs
Uses both ARM API and AI Foundry REST API to find the identity linkage
"""

import os
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.core.rest import HttpRequest
from azure.core.pipeline import PipelineResponse
import httpx


async def query_arm_api(credential, subscription_id, resource_group, project_name):
    """Query Azure Resource Manager API for AI Foundry project details"""
    
    print("\n" + "="*100)
    print("METHOD 1: Azure Resource Manager (ARM) API")
    print("="*100 + "\n")
    
    # Get access token for ARM
    token = credential.get_token("https://management.azure.com/.default")
    
    # ARM API endpoint for AI Hub/Project
    arm_endpoint = f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        print(f"Querying ARM API: {arm_endpoint}")
        print(f"API Version: 2024-04-01-preview\n")
        
        # Query with latest API version
        response = await client.get(
            f"{arm_endpoint}?api-version=2024-04-01-preview",
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            workspace_data = response.json()
            
            print("✅ Successfully retrieved workspace data\n")
            print("="*100)
            print("WORKSPACE IDENTITY INFORMATION")
            print("="*100 + "\n")
            
            # Check for identity in workspace
            if "identity" in workspace_data:
                identity = workspace_data["identity"]
                print("Workspace Identity:")
                print(json.dumps(identity, indent=2))
                print()
            
            # Check properties for agent-related information
            if "properties" in workspace_data:
                props = workspace_data["properties"]
                
                # Look for agent-related properties
                agent_keys = [k for k in props.keys() if 'agent' in k.lower() or 'identity' in k.lower()]
                if agent_keys:
                    print("Agent-related properties:")
                    for key in agent_keys:
                        print(f"  {key}: {props[key]}")
                    print()
                
                # Show all properties for analysis
                print("All Workspace Properties:")
                print(json.dumps(props, indent=2))
                print()
            
            # Save full response for inspection
            output_file = Path(__file__).parent / "arm_workspace_response.json"
            with open(output_file, "w") as f:
                json.dump(workspace_data, f, indent=2)
            print(f"💾 Full response saved to: {output_file}\n")
            
            return workspace_data
        else:
            print(f"❌ ARM API Error: {response.status_code}")
            print(f"Response: {response.text}\n")
            return None


async def query_foundry_rest_api(credential, foundry_endpoint, agent_name):
    """Query Azure AI Foundry REST API directly for agent details"""
    
    print("\n" + "="*100)
    print("METHOD 2: Azure AI Foundry REST API")
    print("="*100 + "\n")
    
    # Get access token for AI Services (correct scope for Azure AI)
    token = credential.get_token("https://ai.azure.com/.default")
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    # Try to query agent directly via REST API
    agent_endpoint = f"{foundry_endpoint}/agents/{agent_name}"
    
    async with httpx.AsyncClient() as client:
        print(f"Querying Foundry API: {agent_endpoint}")
        print(f"API Version: 2024-08-01-preview\n")
        
        response = await client.get(
            agent_endpoint,
            headers=headers,
            params={"api-version": "2024-08-01-preview"},
            timeout=30.0
        )
        
        if response.status_code == 200:
            agent_data = response.json()
            
            print("✅ Successfully retrieved agent data\n")
            print("="*100)
            print(f"AGENT: {agent_name}")
            print("="*100 + "\n")
            
            # Look for identity information
            identity_keys = [k for k in agent_data.keys() if 'identity' in k.lower() or 'principal' in k.lower() or 'blueprint' in k.lower()]
            
            if identity_keys:
                print("🎯 Identity Information Found:")
                for key in identity_keys:
                    print(f"  {key}: {agent_data[key]}")
                print()
            else:
                print("⚠️  No direct identity keys found in agent data\n")
            
            # Show all agent properties
            print("All Agent Properties:")
            print(json.dumps(agent_data, indent=2))
            print()
            
            # Save full response
            output_file = Path(__file__).parent / f"foundry_agent_{agent_name}_response.json"
            with open(output_file, "w") as f:
                json.dump(agent_data, f, indent=2)
            print(f"💾 Full response saved to: {output_file}\n")
            
            return agent_data
        else:
            print(f"❌ Foundry API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Try alternative endpoint (list all agents and filter)
            print("\nTrying alternative endpoint (list agents)...\n")
            
            list_endpoint = f"{foundry_endpoint}/agents"
            response = await client.get(
                list_endpoint,
                headers=headers,
                params={"api-version": "2024-08-01-preview"},
                timeout=30.0
            )
            
            if response.status_code == 200:
                agents_list = response.json()
                print("✅ Retrieved agents list\n")
                
                # Find our agent
                if "value" in agents_list:
                    for agent in agents_list["value"]:
                        if agent.get("name") == agent_name or agent.get("id") == agent_name:
                            print(f"Found agent: {agent.get('name', agent.get('id'))}")
                            print(json.dumps(agent, indent=2))
                            print()
                            
                            # Save this too
                            output_file = Path(__file__).parent / f"foundry_agent_{agent_name}_from_list.json"
                            with open(output_file, "w") as f:
                                json.dump(agent, f, indent=2)
                            print(f"💾 Saved to: {output_file}\n")
                            
                            return agent
                
                # Save full list
                output_file = Path(__file__).parent / "foundry_all_agents_response.json"
                with open(output_file, "w") as f:
                    json.dump(agents_list, f, indent=2)
                print(f"💾 Full agents list saved to: {output_file}\n")
            else:
                print(f"❌ List agents also failed: {response.status_code}\n")
            
            return None


async def query_agent_resource_directly(credential, subscription_id, resource_group, project_name, agent_name):
    """Try to query agent as an ARM sub-resource"""
    
    print("\n" + "="*100)
    print("METHOD 3: Agent as ARM Sub-Resource")
    print("="*100 + "\n")
    
    token = credential.get_token("https://management.azure.com/.default")
    
    # Try different possible resource paths
    possible_paths = [
        f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}/agents/{agent_name}",
        f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{project_name}/inferenceEndpoints/{agent_name}",
        f"https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.CognitiveServices/accounts/{project_name}/deployments/{agent_name}",
    ]
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        for i, path in enumerate(possible_paths, 1):
            print(f"Attempt {i}: {path}")
            
            response = await client.get(
                f"{path}?api-version=2024-04-01-preview",
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                print(f"✅ Success!\n")
                data = response.json()
                print(json.dumps(data, indent=2))
                print()
                
                output_file = Path(__file__).parent / f"arm_agent_{agent_name}_response.json"
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
                print(f"💾 Saved to: {output_file}\n")
                
                return data
            else:
                print(f"   Status: {response.status_code}\n")
        
        print("⚠️  No direct agent resource found via ARM\n")
        return None


async def main():
    """Main execution"""
    
    print("\n" + "="*100)
    print("Azure AI Foundry Agent Identity Mapper - REST API Approach")
    print("="*100 + "\n")
    
    # Load environment
    env_file = Path(__file__).parent / "app" / "copilot" / ".env"
    load_dotenv(env_file, override=True)
    
    # Configuration
    foundry_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    connection_string = os.getenv("FOUNDRY_PROJECT_CONNECTION_STRING")
    tenant_id = os.getenv("AZURE_AUTH_TENANT_ID")
    agent_name = "AccountAgent"  # Target agent to investigate
    
    # Extract resource name and project name from endpoint
    # Format:https://banking-new-resources.services.ai.azure.com/api/projects/banking-new
    resource_name = None
    project_name = None
    if foundry_endpoint:
        import re
        match = re.match(r'https://([^.]+)\.services\.ai\.azure\.com/api/projects/([^/]+)', foundry_endpoint)
        if match:
            resource_name = match.group(1)  # banking-new-resource
            project_name = match.group(2)   # banking-new
    
    # Get subscription/resource group - try to find via Azure CLI or use connection string
    subscription_id = None
    resource_group = None
    
    # Try from connection string first
    if connection_string:
        parts = connection_string.split(';')
        if len(parts) == 4:
            subscription_id = parts[1]
            resource_group = parts[2]
    
    # Try to get from Azure CLI if not in connection string
    if not subscription_id or not resource_group:
        try:
            import subprocess
            result = subprocess.run(
                ["az", "account", "show", "--query", "{subscription:id,tenant:tenantId}", "-o", "json"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                import json as builtin_json
                account_info = builtin_json.loads(result.stdout)
                if not subscription_id:
                    subscription_id = account_info.get("subscription")
        except Exception:
            pass
    
    print("Configuration:")
    print(f"  Foundry Endpoint: {foundry_endpoint}")
    print(f"  Resource Name: {resource_name}")
    print(f"  Project Name: {project_name}")
    print(f"  Subscription: {subscription_id}")
    print(f"  Resource Group: {resource_group}")
    print(f"  Tenant: {tenant_id}")
    print(f"  Target Agent: {agent_name}")
    
    if not subscription_id:
        print("\n⚠️  Warning: Subscription ID not found. ARM API calls will be limited.")
        print("   Run: az login")
        print("   Then try again")
    
    if not resource_group and subscription_id:
        # Try to find resource group by searching for the resource
        print(f"\n🔍 Searching for resource group of '{resource_name}'...")
        try:
            import subprocess
            result = subprocess.run(
                ["az", "resource", "list", "--name", resource_name, "--query", "[0].resourceGroup", "-o", "tsv"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                resource_group = result.stdout.strip()
                print(f"   ✅ Found resource group: {resource_group}")
        except Exception as e:
            print(f"   ⚠️  Could not search: {e}")
    
    # Create credential
    credential = DefaultAzureCredential()
    
    try:
        # Method 1: ARM API
        workspace_data = await query_arm_api(credential, subscription_id, resource_group, project_name)
        
        # Method 2: Foundry REST API
        agent_data = await query_foundry_rest_api(credential, foundry_endpoint, agent_name)
        
        # Method 3: Agent as ARM sub-resource
        agent_resource = await query_agent_resource_directly(credential, subscription_id, resource_group, project_name, agent_name)
        
        # Summary
        print("\n" + "="*100)
        print("SUMMARY")
        print("="*100 + "\n")
        
        print("✅ Methods completed. Check the generated JSON files for full details:")
        print("   - arm_workspace_response.json")
        print(f"   - foundry_agent_{agent_name}_response.json")
        print("   - foundry_all_agents_response.json")
        print()
        print("💡 Look for these fields in the JSON files:")
        print("   - identity.principalId")
        print("   - identity.tenantId")
        print("   - properties.managedIdentity")
        print("   - properties.agentIdentity")
        print("   - systemData.createdBy")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
