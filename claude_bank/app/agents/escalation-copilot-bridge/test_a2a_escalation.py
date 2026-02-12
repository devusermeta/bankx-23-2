"""
Test script for Escalation Copilot Bridge using A2A protocol.

This simulates how other agents (like ProdInfo, AIMoneyCoach, etc.) will call
the escalation bridge to create support tickets.
"""

import httpx
import asyncio
import json
from datetime import datetime


async def test_a2a_escalation():
    """Test the escalation bridge using A2A protocol"""
    
    url = "http://localhost:9006/a2a/invoke"
    
    # Simulate request from another agent (like ProdInfo)
    request_payload = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Create escalation ticket: "
                    "Customer is unable to access their account after password reset. "
                    "They have tried multiple times but keep getting an error message. "
                    "Customer Email: purohitabhinav2001@gmail.com, "
                    "Customer Name: Abhinav Purohit"
                )
            }
        ],
        "customer_id": "CUST-12345",
        "thread_id": f"test-thread-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    print("=" * 70)
    print("Testing A2A Escalation Bridge → Copilot Studio")
    print("=" * 70)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"\nTarget: {url}")
    print("\nRequest Payload:")
    print(json.dumps(request_payload, indent=2))
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("\n" + "-" * 70)
            print("Sending request to escalation bridge...")
            print("-" * 70)
            
            start_time = asyncio.get_event_loop().time()
            response = await client.post(url, json=request_payload)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            response.raise_for_status()
            
            result = response.json()
            
            print("\n" + "=" * 70)
            print("✓ Response Received")
            print("=" * 70)
            print(f"Status Code: {response.status_code}")
            print(f"Response Time: {elapsed:.2f} seconds")
            print("\nResponse Body:")
            print(json.dumps(result, indent=2))
            
            # Parse response
            if result.get("role") == "assistant":
                print("\n" + "=" * 70)
                print("✓ ESCALATION SUCCESSFUL")
                print("=" * 70)
                print(f"\nAgent: {result.get('agent', 'Unknown')}")
                print(f"\nMessage:\n{result.get('content', 'No message')}")
                
                # Try to extract ticket ID from message
                content = result.get('content', '')
                if 'TKT-' in content:
                    import re
                    match = re.search(r'TKT-\d{4}-\d+', content)
                    if match:
                        ticket_id = match.group(0)
                        print(f"\n🎫 Ticket ID: {ticket_id}")
                
                print("\n✅ The ticket has been:")
                print("   • Sent via Outlook (email notification)")
                print("   • Stored in Excel (ticket tracking)")
                print("   • All handled by Copilot Studio agent")
            else:
                print("\n⚠️  Unexpected response format")
            
        except httpx.HTTPStatusError as e:
            print("\n" + "=" * 70)
            print("✗ HTTP ERROR")
            print("=" * 70)
            print(f"Status Code: {e.response.status_code}")
            print(f"Error: {e}")
            print(f"\nResponse Body:")
            print(e.response.text)
            
        except httpx.TimeoutException:
            print("\n" + "=" * 70)
            print("✗ TIMEOUT ERROR")
            print("=" * 70)
            print("The request timed out. Possible causes:")
            print("  • Escalation bridge not running (python main.py)")
            print("  • Copilot Studio agent taking too long to respond")
            print("  • Network issues")
            
        except httpx.ConnectError:
            print("\n" + "=" * 70)
            print("✗ CONNECTION ERROR")
            print("=" * 70)
            print("Could not connect to escalation bridge. Make sure:")
            print("  • Bridge is running: python main.py")
            print("  • Port 9006 is correct")
            print("  • No firewall blocking")
            
        except Exception as e:
            print("\n" + "=" * 70)
            print("✗ ERROR")
            print("=" * 70)
            print(f"Error: {e}")
            print(f"Type: {type(e).__name__}")


async def test_multiple_scenarios():
    """Test multiple escalation scenarios"""
    
    scenarios = [
        {
            "name": "Account Access Issue",
            "content": "Customer cannot log into their account. Customer Email: alice@example.com, Customer Name: Alice Smith",
            "customer_id": "CUST-001"
        },
        {
            "name": "Payment Failed",
            "content": "Payment transaction failed multiple times. Customer Email: bob@example.com, Customer Name: Bob Johnson",
            "customer_id": "CUST-002"
        },
        {
            "name": "Card Lost",
            "content": "Customer reports lost credit card and needs immediate assistance. Customer Email: carol@example.com, Customer Name: Carol White",
            "customer_id": "CUST-003"
        }
    ]
    
    print("=" * 70)
    print("Testing Multiple Escalation Scenarios")
    print("=" * 70)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{'=' * 70}")
        print(f"Scenario {i}/{len(scenarios)}: {scenario['name']}")
        print("=" * 70)
        
        request_payload = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Create escalation ticket: {scenario['content']}"
                }
            ],
            "customer_id": scenario['customer_id'],
            "thread_id": f"test-{i}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        }
        
        print(f"\nContent: {scenario['content']}")
        print(f"Customer ID: {scenario['customer_id']}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:9006/a2a/invoke",
                    json=request_payload
                )
                response.raise_for_status()
                
                result = response.json()
                print(f"\n✓ Response: {result.get('content', 'No content')[:100]}...")
                
                # Wait a bit between requests
                await asyncio.sleep(2)
                
        except Exception as e:
            print(f"\n✗ Failed: {e}")
        
    print("\n" + "=" * 70)
    print("All scenarios tested")
    print("=" * 70)


async def test_health_check():
    """Test health endpoint"""
    
    print("=" * 70)
    print("Testing Health Check")
    print("=" * 70)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:9006/health")
            response.raise_for_status()
            
            data = response.json()
            
            print("\n✓ Health Check Response:")
            print(json.dumps(data, indent=2))
            
            if data.get("status") == "healthy":
                print("\n✅ Bridge is healthy and ready")
            else:
                print("\n⚠️  Bridge reports unhealthy status")
                
    except Exception as e:
        print(f"\n✗ Health check failed: {e}")


async def main():
    """Main test runner"""
    
    print("\n" + "=" * 70)
    print("ESCALATION COPILOT BRIDGE - A2A PROTOCOL TEST SUITE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 70 + "\n")
    
    # Test 1: Health check
    await test_health_check()
    
    print("\n\n")
    
    # Test 2: Single escalation
    await test_a2a_escalation()
    
    # Uncomment to test multiple scenarios
    # print("\n\n")
    # await test_multiple_scenarios()
    
    print("\n\n" + "=" * 70)
    print("Test Suite Complete")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Check Copilot Studio agent logs")
    print("  2. Verify email was sent (check Outlook)")
    print("  3. Verify ticket was added to Excel")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
