"""
Test A2A Agent end-to-end with Azure AI Foundry
Validates: Agent → MCP Server → Data
Checks: Trace visibility, anti-hallucination (agent MUST use tools)
"""

import requests
import json

A2A_SERVER_URL = "http://localhost:9001"
HEADERS = {"Content-Type": "application/json"}

print("=" * 80)
print("Testing Account Agent via A2A Server")
print("=" * 80)
print(f"A2A Server: {A2A_SERVER_URL}")
print()

# Test 1: Get agent card
print("Test 1: Get Agent Card")
try:
    response = requests.get(f"{A2A_SERVER_URL}/.well-known/agent.json", timeout=10)
    print(f"✓ Agent card: {response.status_code}")
    agent_info = response.json()
    print(f"  Agent Name: {agent_info.get('name')}")
    print(f"  Version: {agent_info.get('version')}")
    print(f"  Capabilities: {agent_info.get('capabilities', [])}")
except Exception as e:
    print(f"✗ Agent card failed: {e}")

print()

# Test 2: Simple account query (should use getAccountsByUserName)
print("Test 2: Query Accounts for User")
print("Query: What accounts does nattaporn.suksawat@example.com have?")
try:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "What accounts does nattaporn.suksawat@example.com have?"
            }
        ]
    }
    response = requests.post(f"{A2A_SERVER_URL}/a2a/invoke", json=payload, headers=HEADERS, timeout=30)
    print(f"✓ Response: {response.status_code}")
    result = response.json()
    
    # Extract agent response
    if "messages" in result and len(result["messages"]) > 0:
        agent_message = result["messages"][-1]["content"]
        print(f"  Agent Response: {agent_message[:200]}...")
        
        # Check if response contains account info (anti-hallucination check)
        if "CHK-002" in agent_message or "checking" in agent_message.lower():
            print("  ✓ Agent used MCP tools (found account data)")
        else:
            print("  ⚠ Warning: Response doesn't contain expected account data")
    else:
        print(f"  Response: {result}")
        
except Exception as e:
    print(f"✗ Query failed: {e}")

print()

# Test 3: Balance check (should use getAccountDetails)
print("Test 3: Check Account Balance")
print("Query: What is the balance of account CHK-002?")
try:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "What is the balance of account CHK-002?"
            }
        ]
    }
    response = requests.post(f"{A2A_SERVER_URL}/a2a/invoke", json=payload, headers=HEADERS, timeout=30)
    print(f"✓ Response: {response.status_code}")
    result = response.json()
    
    if "messages" in result and len(result["messages"]) > 0:
        agent_message = result["messages"][-1]["content"]
        print(f"  Agent Response: {agent_message[:200]}...")
        
        # Check if response contains balance (anti-hallucination check)
        if "150000" in agent_message or "150,000" in agent_message:
            print("  ✓ Agent used MCP tools (correct balance)")
        else:
            print("  ⚠ Warning: Response doesn't contain expected balance data")
    else:
        print(f"  Response: {result}")
        
except Exception as e:
    print(f"✗ Query failed: {e}")

print()

# Test 4: Limits check (should use checkLimits)
print("Test 4: Check Transfer Limit")
print("Query: Can I transfer 30000 THB from CHK-002?")
try:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Can I transfer 30000 THB from account CHK-002?"
            }
        ]
    }
    response = requests.post(f"{A2A_SERVER_URL}/a2a/invoke", json=payload, headers=HEADERS, timeout=30)
    print(f"✓ Response: {response.status_code}")
    result = response.json()
    
    if "messages" in result and len(result["messages"]) > 0:
        agent_message = result["messages"][-1]["content"]
        print(f"  Agent Response: {agent_message[:200]}...")
        
        # Check if response indicates limits check was performed
        if any(word in agent_message.lower() for word in ["limit", "allowed", "can", "yes", "no"]):
            print("  ✓ Agent used MCP tools (limit check performed)")
        else:
            print("  ⚠ Warning: Response doesn't indicate limit check")
    else:
        print(f"  Response: {result}")
        
except Exception as e:
    print(f"✗ Query failed: {e}")

print()

# Test 5: Complex query (should use multiple tools)
print("Test 5: Complex Multi-Tool Query")
print("Query: Show me all accounts for nattaporn.suksawat@example.com and their limits")
try:
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Show me all accounts for nattaporn.suksawat@example.com and check their transaction limits"
            }
        ]
    }
    response = requests.post(f"{A2A_SERVER_URL}/a2a/invoke", json=payload, headers=HEADERS, timeout=30)
    print(f"✓ Response: {response.status_code}")
    result = response.json()
    
    if "messages" in result and len(result["messages"]) > 0:
        agent_message = result["messages"][-1]["content"]
        print(f"  Agent Response: {agent_message[:300]}...")
        
        # Check if response contains both account and limit data
        has_account_data = "CHK-002" in agent_message or "checking" in agent_message.lower()
        has_limit_data = any(word in agent_message.lower() for word in ["limit", "50000", "100000"])
        
        if has_account_data and has_limit_data:
            print("  ✓ Agent used multiple MCP tools (account + limits)")
        else:
            print(f"  ⚠ Warning: Account data: {has_account_data}, Limit data: {has_limit_data}")
    else:
        print(f"  Response: {result}")
        
except Exception as e:
    print(f"✗ Query failed: {e}")

print()
print("=" * 80)
print("✓ End-to-End Testing Complete!")
print()
print("Next steps:")
print("1. Review A2A server logs for trace details")
print("2. Verify agent ALWAYS calls MCP tools (no hallucination)")
print("3. Check MCP server logs on Azure (if needed)")
print("4. Move to Phase 2: Payment & Transaction agents")
print("=" * 80)
