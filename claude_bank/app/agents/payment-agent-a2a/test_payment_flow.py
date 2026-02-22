"""
Test Payment Agent MCP Tool Execution
This test reproduces the exact scenario where Payment Agent returns fake data
"""

import asyncio
import httpx
import json
from datetime import datetime


class PaymentAgentTester:
    def __init__(self):
        self.base_url = "http://localhost:9003"
        self.user_email = "nattaporn@bankxthb.onmicrosoft.com"
        self.customer_id = "CUST-002"
        
    def print_header(self, text: str):
        print("\n" + "="*80)
        print(f"  {text}")
        print("="*80 + "\n")
    
    def print_step(self, step: str):
        print(f"\n{'─'*80}")
        print(f"🔹 {step}")
        print('─'*80)
    
    def print_success(self, text: str):
        print(f"✅ {text}")
    
    def print_error(self, text: str):
        print(f"❌ {text}")
    
    def print_info(self, text: str):
        print(f"ℹ️  {text}")
    
    async def test_agent_card(self):
        """Test 1: Verify agent is accessible"""
        self.print_step("TEST 1: Verify Agent Card")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/.well-known/agent.json")
                response.raise_for_status()
                agent_card = response.json()
                
                self.print_success("Agent card retrieved")
                print(f"   Name: {agent_card.get('name')}")
                print(f"   Version: {agent_card.get('version')}")
                return True
        except Exception as e:
            self.print_error(f"Agent card failed: {e}")
            return False
    
    async def test_balance_query(self):
        """Test 2: Query account balance (exact user scenario)"""
        self.print_step("TEST 2: Balance Query Test")
        self.print_info(f"User: {self.user_email}")
        self.print_info("Expected: Call getAccountsByUserName → should return CHK-002 with balance 74,270 THB")
        
        query = f"My user ID is {self.user_email}. What is my account balance?"
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "messages": [{"role": "user", "content": query}],
                    "customer_id": self.customer_id,
                    "stream": False
                }
                
                print(f"\n📤 Sending: '{query}'")
                
                response = await client.post(
                    f"{self.base_url}/a2a/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract response content
                if "messages" in result and len(result["messages"]) > 0:
                    content = result["messages"][-1].get("content", "")
                elif "content" in result:
                    content = result["content"]
                else:
                    content = str(result)
                
                print(f"\n📥 Agent Response:")
                print("─" * 80)
                print(content)
                print("─" * 80)
                
                # Check if response contains real data
                if "74,270" in content or "74270" in content:
                    self.print_success("REAL DATA RETURNED - MCP tools are working! ✨")
                    return True
                elif "15,000" in content or "15000" in content:
                    self.print_error("FAKE DATA RETURNED - MCP tools NOT being called!")
                    self.print_info("Agent is hallucinating balance instead of calling tools")
                    return False
                elif "CHK-002" in content:
                    self.print_success("Account ID found - MCP might be working")
                    return True
                else:
                    self.print_error("No balance information found in response")
                    self.print_info("Response might be generic or error")
                    return False
                    
        except Exception as e:
            self.print_error(f"Balance query failed: {e}")
            return False
    
    async def test_transfer_request(self):
        """Test 3: Request money transfer (full flow)"""
        self.print_step("TEST 3: Transfer Request Test")
        self.print_info("Testing if agent calls: getRegisteredBeneficiaries + getAccountsByUserName + getAccountDetails")
        
        query = """My user ID is nattaporn@bankxthb.onmicrosoft.com. 
I want to transfer 500 THB to Somchai. Can you help me?"""
        
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                payload = {
                    "messages": [{"role": "user", "content": query}],
                    "customer_id": self.customer_id,
                    "stream": False
                }
                
                print(f"\n📤 Sending: '{query}'")
                
                response = await client.post(
                    f"{self.base_url}/a2a/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract response content
                if "messages" in result and len(result["messages"]) > 0:
                    content = result["messages"][-1].get("content", "")
                elif "content" in result:
                    content = result["content"]
                else:
                    content = str(result)
                
                print(f"\n📥 Agent Response:")
                print("─" * 80)
                print(content)
                print("─" * 80)
                
                # Check if response shows tool execution
                real_data_indicators = [
                    "74,270",  # Real balance
                    "74270",
                    "CHK-001",  # Somchai's account
                    "338-617-716",  # Somchai's account number
                    "beneficiaries",  # Should call getRegisteredBeneficiaries
                ]
                
                fake_data_indicators = [
                    "15,000",
                    "15000",
                ]
                
                has_real_data = any(indicator in content for indicator in real_data_indicators)
                has_fake_data = any(indicator in content for indicator in fake_data_indicators)
                
                if has_real_data:
                    self.print_success("REAL DATA FOUND - MCP tools executed! 🎉")
                    return True
                elif has_fake_data:
                    self.print_error("FAKE DATA FOUND - MCP tools NOT executed!")
                    return False
                else:
                    self.print_info("No definitive data markers found")
                    self.print_info("Check response manually above")
                    return None
                    
        except Exception as e:
            self.print_error(f"Transfer request failed: {e}")
            return False
    
    async def run_all_tests(self):
        """Run complete test suite"""
        self.print_header("Payment Agent MCP Tool Execution Test Suite")
        
        print(f"Testing agent at: {self.base_url}")
        print(f"User: {self.user_email}")
        print(f"Customer ID: {self.customer_id}")
        print(f"Expected real balance: 74,270 THB (from CHK-002)")
        
        results = {}
        
        # Test 1: Agent Card
        results['agent_card'] = await self.test_agent_card()
        
        if not results['agent_card']:
            self.print_error("Agent not accessible - stopping tests")
            return
        
        # Wait a bit between tests
        await asyncio.sleep(2)
        
        # Test 2: Balance Query
        results['balance_query'] = await self.test_balance_query()
        
        # Wait before next test
        await asyncio.sleep(3)
        
        # Test 3: Transfer Request
        results['transfer_request'] = await self.test_transfer_request()
        
        # Summary
        self.print_header("Test Results Summary")
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL" if result is False else "⚠️  UNKNOWN"
            print(f"{status} - {test_name}")
        
        print("\n")
        
        # Diagnosis
        if results.get('balance_query') is False or results.get('transfer_request') is False:
            self.print_header("🔍 DIAGNOSIS")
            print("Payment Agent is NOT calling MCP tools. Possible causes:")
            print()
            print("1. ❌ Agent in Azure AI Foundry has stale/cached configuration")
            print("   Fix: Delete and recreate agent in Foundry")
            print()
            print("2. ❌ Agent instructions don't trigger tool calls")
            print("   Fix: Update system prompt to be more explicit about tool usage")
            print()
            print("3. ❌ Tools not properly registered in Foundry UI")
            print("   Fix: Verify 'Execute Tools' is enabled in agent settings")
            print()
            print("4. ❌ Agent deployment version mismatch")
            print("   Fix: Deploy latest agent version")
        else:
            self.print_header("🎉 SUCCESS")
            print("Payment Agent is correctly calling MCP tools!")


async def main():
    tester = PaymentAgentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("  Payment Agent MCP Tool Execution Diagnostic Test")
    print("="*80)
    print()
    print("This test will:")
    print("  1. Check if payment agent is accessible")
    print("  2. Test balance query (should call getAccountsByUserName)")
    print("  3. Test transfer request (should call getRegisteredBeneficiaries)")
    print()
    print("Expected: Agent should return real balance (74,270 THB)")
    print("Problem:  Agent returns fake balance (15,000 THB)")
    print()
    
    asyncio.run(main())
