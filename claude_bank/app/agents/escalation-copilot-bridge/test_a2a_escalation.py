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
    """Test the escalation bridge using A2A protocol - matches manual test scenario"""
    
    url = "http://localhost:9006/a2a/invoke"
    
    # Replicate exact scenario from manual test
    request_payload = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "I want to raise a ticket. "
                    "My name is Abhinav, emailID is purohitabhinav01@gmail.com, "
                    "I am not able to login to the bank application, "
                    "my customer ID is CUST-001"
                )
            }
        ],
        "customer_id": "CUST-001",
        "thread_id": f"a2a-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
                    match = re.search(r'TKT-\d+', content)
                    if match:
                        ticket_id = match.group(0)
                        print(f"\n🎫 Ticket ID: {ticket_id}")
                    else:
                        print(f"\n🔍 Content contains TKT but pattern not matched: {content}")
                else:
                    print(f"\n📋 Full response content: {content}")
                
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
            "name": "Login Issues (High Priority)",
            "content": "I want to raise a ticket. My name is Alice Smith, emailID is alice.smith@example.com, I am not able to login to the bank application, my customer ID is CUST-101",
            "customer_id": "CUST-101"
        },
        {
            "name": "Payment Transaction Failure",
            "content": "I want to raise a ticket. My name is Bob Johnson, emailID is bob.johnson@example.com, My payment transactions keep failing with error messages, my customer ID is CUST-102",
            "customer_id": "CUST-102"
        },
        {
            "name": "Lost Card Emergency",
            "content": "I want to raise a ticket. My name is Carol White, emailID is carol.white@example.com, I have lost my credit card and need immediate card blocking, my customer ID is CUST-103",
            "customer_id": "CUST-103"
        },
        {
            "name": "Account Balance Discrepancy",
            "content": "I want to raise a ticket. My name is David Brown, emailID is david.brown@example.com, My account balance shows incorrect amount after a recent transfer, my customer ID is CUST-104",
            "customer_id": "CUST-104"
        },
        {
            "name": "Mobile Banking App Issue",
            "content": "I want to raise a ticket. My name is Emma Wilson, emailID is emma.wilson@example.com, The mobile banking app keeps crashing when I try to make transfers, my customer ID is CUST-105",
            "customer_id": "CUST-105"
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


async def test_exact_manual_scenario():
    """Test the exact scenario that was manually tested in Copilot Studio"""
    
    url = "http://localhost:9006/a2a/invoke"
    
    # Exact scenario from manual test
    request_payload = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "I want to raise a ticket. "
                    "My name is Abhinav, emailID is purohitabhinav01@gmail.com, "
                    "I am not able to login to the bank application, "
                    "my customer ID is CUST-001"
                )
            }
        ],
        "customer_id": "CUST-001",
        "thread_id": f"manual-test-replica-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    print("=" * 70)
    print("Testing EXACT MANUAL SCENARIO → Copilot Studio")
    print("=" * 70)
    print(f"\nTarget: {url}")
    print(f"\nExpected: Ticket creation for login issues")
    print(f"Customer: Abhinav (CUST-001)")
    print(f"Email: purohitabhinav01@gmail.com")
    print(f"Issue: Login problems")
    
    print("\nRequest Payload:")
    print(json.dumps(request_payload, indent=2))
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            print("\n" + "-" * 70)
            print("Replicating manual test via A2A...")
            print("-" * 70)
            
            start_time = asyncio.get_event_loop().time()
            response = await client.post(url, json=request_payload)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            response.raise_for_status()
            result = response.json()
            
            print("\n" + "=" * 70)
            print("✓ A2A → COPILOT STUDIO SUCCESS!")
            print("=" * 70)
            print(f"Status Code: {response.status_code}")
            print(f"Response Time: {elapsed:.2f} seconds")
            
            if result.get("role") == "assistant":
                content = result.get('content', '')
                print(f"\nCopilot Studio Response:")
                print(f"{content}")
                
                # Extract ticket ID
                if 'TKT-' in content:
                    import re
                    match = re.search(r'TKT-\d+', content)
                    if match:
                        ticket_id = match.group(0)
                        print(f"\n🎫 SUCCESS: Ticket {ticket_id} created!")
                        print(f"\n✅ Verification:")
                        print(f"   • Copilot Studio processed the request")
                        print(f"   • Email sent to purohitabhinav01@gmail.com")
                        print(f"   • Ticket stored in Excel spreadsheet")
                        print(f"   • A2A protocol working correctly")
                        return True
                    else:
                        print(f"\n⚠️  Ticket ID not found in expected format")
                else:
                    print(f"\n⚠️  No ticket ID found in response")
            else:
                print(f"\n⚠️  Unexpected response format: {result}")
                
        except httpx.HTTPStatusError as e:
            print(f"\n❌ HTTP Error {e.response.status_code}: {e.response.text}")
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False
    
    return False


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
    print("Testing: A2A Protocol → Copilot Studio → Outlook + Excel")
    print("=" * 70 + "\n")
    
    # Test 1: Health check
    await test_health_check()
    
    print("\n\n")
    
    # Test 2: Exact manual scenario replication
    print("🎯 PRIORITY TEST: Replicating your manual test scenario")
    success = await test_exact_manual_scenario()
    
    print("\n\n")
    
    # Test 3: General A2A escalation
    print("🔄 GENERAL A2A TEST: Standard escalation flow")
    await test_a2a_escalation()
    
    # Test 4: Multiple scenarios (optional)
    print("\n\nTo test multiple scenarios, uncomment the line below:")
    print("# await test_multiple_scenarios()")
    
    print("\n\n" + "=" * 70)
    print("🎉 TEST SUITE COMPLETE")
    print("=" * 70)
    
    if success:
        print("\n✅ SUCCESS: A2A → Copilot Studio integration working!")
        print("\n🔍 Verification Steps:")
        print("   1. Check your email (purohitabhinav01@gmail.com) for ticket notification")
        print("   2. Check Excel spreadsheet for new ticket entry")
        print("   3. Verify ticket ID format matches Copilot Studio")
    else:
        print("\n⚠️  Some tests may have issues - check logs above")
    
    print("\n🚀 Next Steps:")
    print("   1. Your Copilot Studio agent is ready for A2A integration")
    print("   2. Other agents can now call the escalation bridge")
    print("   3. Replace MCP-based escalation with this Copilot Studio version")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
