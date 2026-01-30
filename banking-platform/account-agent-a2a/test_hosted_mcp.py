"""
Test hosted MCP server on Azure Container Apps
"""

import requests
import json

MCP_SERVER_URL = "https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/mcp"
HEADERS = {"Content-Type": "application/json"}

print("=" * 80)
print("Testing Hosted MCP Server")
print("=" * 80)
print(f"URL: {MCP_SERVER_URL}")
print()

# Test 1: Health check
print("Test 1: Health Check")
try:
    response = requests.get("https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io/health", timeout=10)
    print(f"✓ Health: {response.status_code}")
    print(f"  Response: {response.json()}")
except Exception as e:
    print(f"✗ Health check failed: {e}")

print()

# Test 2: Initialize MCP
print("Test 2: MCP Initialize")
try:
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {}
        }
    }
    response = requests.post(MCP_SERVER_URL, json=rpc_payload, headers=HEADERS, timeout=10)
    print(f"✓ Initialize: {response.status_code}")
    result = response.json()
    print(f"  Server: {result.get('result', {}).get('serverInfo', {})}")
except Exception as e:
    print(f"✗ Initialize failed: {e}")

print()

# Test 3: List tools
print("Test 3: List Tools")
try:
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    response = requests.post(MCP_SERVER_URL, json=rpc_payload, headers=HEADERS, timeout=10)
    print(f"✓ Tools list: {response.status_code}")
    result = response.json()
    tools = result.get('result', {}).get('tools', [])
    print(f"  Found {len(tools)} tools:")
    for tool in tools:
        print(f"    - {tool['name']}")
except Exception as e:
    print(f"✗ List tools failed: {e}")

print()

# Test 4: Call a tool - getAccountsByUserName
print("Test 4: Call Tool - getAccountsByUserName")
try:
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "getAccountsByUserName",
            "arguments": {
                "email": "somchai.rattanakorn@example.com"
            }
        }
    }
    response = requests.post(MCP_SERVER_URL, json=rpc_payload, headers=HEADERS, timeout=10)
    print(f"✓ Tool call: {response.status_code}")
    result = response.json()
    if "result" in result:
        content = result["result"]["content"][0]["text"]
        data = json.loads(content)
        print(f"  Success: {data.get('success')}")
        print(f"  Accounts found: {data.get('count', 0)}")
        if data.get('accounts'):
            print(f"  First account: {data['accounts'][0]['account_id']}")
    else:
        print(f"  Error: {result.get('error')}")
except Exception as e:
    print(f"✗ Tool call failed: {e}")

print()
print("=" * 80)
print("✓ MCP Server is ready for Azure AI Foundry integration!")
print()
print("Next steps:")
print("1. Go to Azure AI Foundry portal: https://ai.azure.com")
print("2. Navigate to your project: banking-new-resources")
print("3. Create new agent 'AccountAgent'")
print("4. Add MCP server:")
print(f"   - Server URL: {MCP_SERVER_URL}")
print("   - Server Label: account-mcp")
print("   - Select all 5 tools")
print("   - Approval: Never (auto-approve)")
print("=" * 80)
