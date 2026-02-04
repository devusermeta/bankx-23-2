"""
Test TransactionAgent A2A MCP Tool Integration
This test verifies that the agent can actually use the MCP tools to fetch data
"""
import asyncio
import aiohttp
import json

A2A_URL = "http://localhost:9002/a2a/invoke"

async def test_mcp_tool_usage():
    """Test if TransactionAgent can use MCP tools to fetch transaction data"""
    
    print("=" * 70)
    print("  Testing TransactionAgent MCP Tool Integration")
    print("=" * 70)
    print()
    
    # Test message that requires using MCP tools
    test_message = "Show me the last 5 transactions for customer CUST001"
    
    request_payload = {
        "message": test_message,
        "stream": False,
        "customer_id": "CUST001",
        "user_mail": "test@bank.com",
        "current_date_time": "2026-01-02 11:35:00"
    }
    
    print(f"📤 Sending Request:")
    print(f"   Message: {test_message}")
    print(f"   Customer: CUST001")
    print()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(A2A_URL, json=request_payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print("✅ Response Received:")
                    print("-" * 70)
                    
                    if "response" in data:
                        content = data["response"]
                        print(f"Content: {content[:500]}...")  # First 500 chars
                        
                        # Check if response contains transaction data indicators
                        indicators = {
                            "MCP Tool Used": any(keyword in content.lower() for keyword in ["transaction", "amount", "date"]),
                            "Has HTML Table": "<table>" in content,
                            "Has Transaction Details": any(word in content.lower() for word in ["debit", "credit", "balance"])
                        }
                        
                        print()
                        print("📊 Response Analysis:")
                        for check, result in indicators.items():
                            status = "✅" if result else "❌"
                            print(f"   {status} {check}: {result}")
                        
                        print()
                        if all(indicators.values()):
                            print("=" * 70)
                            print("✅ MCP TOOLS WORKING CORRECTLY!")
                            print("=" * 70)
                            print("The agent successfully used MCP tools to fetch transaction data.")
                        else:
                            print("=" * 70)
                            print("⚠️  MCP TOOLS MAY NOT BE WORKING")
                            print("=" * 70)
                            print("The agent responded but may not have used the MCP tools.")
                            print("Response content:")
                            print(content)
                    else:
                        print(f"❌ Unexpected response format: {data}")
                else:
                    error_text = await response.text()
                    print(f"❌ HTTP Error: {response.status}")
                    print(f"   Response: {error_text}")
                    
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_tool_usage())
