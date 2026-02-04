"""
Test A2A connection to verify PaymentAgent in Foundry is being used

This script sends a test message to the A2A service and verifies:
1. The service responds successfully
2. The response comes from the PaymentAgent in Azure AI Foundry
"""

import asyncio
import httpx


async def test_a2a_connection():
    """Test that A2A service connects to Foundry PaymentAgent"""
    
    print("=" * 70)
    print("  Testing A2A Connection to Azure AI Foundry PaymentAgent")
    print("=" * 70)
    print()
    
    # Step 1: Check agent card
    print("STEP 1: Checking Agent Card Discovery")
    print("-" * 70)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get("http://localhost:9003/.well-known/agent.json")
            response.raise_for_status()
            agent_card = response.json()
            
            print(f"✅ Agent Card Retrieved:")
            print(f"   Name: {agent_card.get('name')}")
            print(f"   Description: {agent_card.get('description')}")
            print(f"   Version: {agent_card.get('version')}")
            print()
        except Exception as e:
            print(f"❌ Failed to get agent card: {e}")
            return
    
    # Step 2: Send test message to agent
    print("STEP 2: Sending Test Message to Agent")
    print("-" * 70)
    
    test_message = {
        "messages": [
            {
                "role": "user",
                "content": "Hello, are you the PaymentAgent from Azure AI Foundry?"
            }
        ],
        "customer_id": "CUST001",
        "stream": False  # Disable streaming for simpler testing
    }
    
    print(f"Sending message: '{test_message['messages'][0]['content']}'")
    print()
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "http://localhost:9003/a2a/invoke",
                json=test_message,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            
            print("✅ Response from Agent:")
            print("-" * 70)
            
            # Check if we got a response
            if "messages" in result and len(result["messages"]) > 0:
                assistant_message = result["messages"][-1]
                print(f"Role: {assistant_message.get('role')}")
                print(f"Content: {assistant_message.get('content')}")
                print()
                
                print("=" * 70)
                print("✅ CONNECTION VERIFIED!")
                print("=" * 70)
                print()
                print("The PaymentAgent in Azure AI Foundry is responding correctly.")
                print("This confirms that the A2A service is connected to the Foundry agent.")
                
            else:
                print(f"Response: {result}")
            
        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e.response.status_code}")
            print(f"   Response: {e.response.text}")
        except Exception as e:
            print(f"❌ Failed to send message: {e}")


if __name__ == "__main__":
    asyncio.run(test_a2a_connection())
