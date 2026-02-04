"""
Test Suite for AccountAgent A2A Microservice
Tests standalone A2A service before full integration
"""

import asyncio
import httpx
import json
import sys
from pathlib import Path

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class A2ATestRunner:
    """Test runner for AccountAgent A2A microservice"""
    
    def __init__(self, base_url: str = "http://localhost:9001"):
        self.base_url = base_url
        self.tests_passed = 0
        self.tests_failed = 0
    
    def print_header(self, text: str):
        """Print a test section header"""
        print(f"\n{BLUE}{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}{RESET}\n")
    
    def print_success(self, text: str):
        """Print success message"""
        print(f"{GREEN}✅ {text}{RESET}")
        self.tests_passed += 1
    
    def print_error(self, text: str, error: str = ""):
        """Print error message"""
        print(f"{RED}❌ {text}{RESET}")
        if error:
            print(f"{RED}   Error: {error}{RESET}")
        self.tests_failed += 1
    
    def print_info(self, text: str):
        """Print info message"""
        print(f"{YELLOW}ℹ️  {text}{RESET}")
    
    async def test_health_check(self) -> bool:
        """Test 1: Check if A2A service is running"""
        self.print_header("TEST 1: Health Check")
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    self.print_success(f"Service is running: {data.get('status')}")
                    self.print_info(f"Agent: {data.get('agent')}")
                    self.print_info(f"A2A Version: {data.get('a2a_version')}")
                    return True
                else:
                    self.print_error(f"Health check failed with status {response.status_code}")
                    return False
                    
        except httpx.ConnectError:
            self.print_error("Cannot connect to A2A service", 
                           f"Make sure the service is running at {self.base_url}")
            self.print_info("Run: cd app/agents/account-agent-a2a && python main.py")
            return False
        except Exception as e:
            self.print_error("Health check failed", str(e))
            return False
    
    async def test_agent_card_discovery(self) -> bool:
        """Test 2: Check agent card discovery endpoint"""
        self.print_header("TEST 2: Agent Card Discovery")
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/.well-known/agent.json")
                
                if response.status_code == 200:
                    card = response.json()
                    
                    # Validate required fields
                    required_fields = ["agent_id", "name", "description", "capabilities"]
                    missing = [f for f in required_fields if f not in card]
                    
                    if missing:
                        self.print_error(f"Agent card missing fields: {missing}")
                        return False
                    
                    self.print_success("Agent card endpoint accessible")
                    self.print_info(f"Agent ID: {card['agent_id']}")
                    self.print_info(f"Name: {card['name']}")
                    self.print_info(f"Capabilities: {', '.join(card['capabilities'])}")
                    
                    # Check for A2A invoke endpoint
                    if "capabilities" in card and "a2a_invoke" in card["capabilities"]:
                        self.print_success("A2A invoke capability advertised")
                    else:
                        self.print_error("A2A invoke capability not found in agent card")
                        return False
                    
                    return True
                else:
                    self.print_error(f"Agent card request failed with status {response.status_code}")
                    return False
                    
        except Exception as e:
            self.print_error("Agent card discovery failed", str(e))
            return False
    
    async def test_simple_chat(self) -> bool:
        """Test 3: Send a simple chat message"""
        self.print_header("TEST 3: Simple Chat Interaction")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "messages": [
                        {"role": "user", "content": "Hello, what can you help me with?"}
                    ],
                    "thread_id": "test-thread-001",
                    "stream": False
                }
                
                self.print_info("Sending test message...")
                response = await client.post(
                    f"{self.base_url}/a2a/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if "content" in result:
                        self.print_success("Received response from agent")
                        self.print_info(f"Response preview: {result['content'][:150]}...")
                        return True
                    else:
                        self.print_error("Response missing 'content' field")
                        return False
                else:
                    self.print_error(f"Chat request failed with status {response.status_code}")
                    self.print_info(f"Response: {response.text}")
                    return False
                    
        except httpx.ReadTimeout:
            self.print_error("Chat request timed out (30s)", 
                           "Check if Azure AI Foundry agent is properly configured")
            return False
        except Exception as e:
            self.print_error("Chat interaction failed", str(e))
            return False
    
    async def test_mcp_tool_usage(self) -> bool:
        """Test 4: Test MCP tool usage (requires MCP servers running)"""
        self.print_header("TEST 4: MCP Tool Usage")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "messages": [
                        {"role": "user", "content": "What is my current account balance?"}
                    ],
                    "thread_id": "test-thread-002",
                    "customer_id": "CUST-001",
                    "stream": False
                }
                
                self.print_info("Sending query that requires MCP tools...")
                response = await client.post(
                    f"{self.base_url}/a2a/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result.get("content", "")
                    
                    # Check if response contains balance information
                    if any(keyword in content.lower() for keyword in ["balance", "account", "thb", "baht"]):
                        self.print_success("Agent successfully used MCP tools")
                        self.print_info(f"Response contains account data")
                        return True
                    else:
                        self.print_error("Response doesn't contain expected account data")
                        self.print_info(f"Response: {content[:200]}...")
                        return False
                else:
                    self.print_error(f"MCP tool test failed with status {response.status_code}")
                    return False
                    
        except httpx.ReadTimeout:
            self.print_error("MCP tool test timed out (60s)")
            self.print_info("Check if MCP servers are running:")
            self.print_info("  - Account MCP: http://localhost:8070")
            self.print_info("  - Limits MCP: http://localhost:8073")
            return False
        except Exception as e:
            self.print_error("MCP tool usage test failed", str(e))
            return False
    
    async def test_environment_config(self) -> bool:
        """Test 5: Verify environment configuration"""
        self.print_header("TEST 5: Environment Configuration")
        
        try:
            # Check if .env file exists
            env_path = Path(__file__).parent / ".env"
            
            if not env_path.exists():
                self.print_error(".env file not found")
                self.print_info("Create .env from .env.example: cp .env.example .env")
                return False
            
            self.print_success(".env file exists")
            
            # Read and validate key variables
            with open(env_path, "r") as f:
                env_content = f.read()
            
            required_vars = [
                "AZURE_AI_PROJECT_ENDPOINT",
                "AZURE_AI_PROJECT_API_KEY",
                "ACCOUNT_AGENT_NAME",
                "ACCOUNT_MCP_SERVER_URL",
            ]
            
            missing_vars = []
            placeholder_vars = []
            
            for var in required_vars:
                if var not in env_content:
                    missing_vars.append(var)
                elif "your-" in env_content or "your_" in env_content:
                    # Check if this specific var has placeholder
                    for line in env_content.split("\n"):
                        if var in line and ("your-" in line or "your_" in line):
                            placeholder_vars.append(var)
                            break
            
            if missing_vars:
                self.print_error(f"Missing environment variables: {', '.join(missing_vars)}")
                return False
            
            if placeholder_vars:
                self.print_error(f"Variables still have placeholders: {', '.join(placeholder_vars)}")
                self.print_info("Update .env with actual Azure credentials")
                return False
            
            self.print_success("All required environment variables are set")
            return True
            
        except Exception as e:
            self.print_error("Environment configuration check failed", str(e))
            return False
    
    async def test_streaming_response(self) -> bool:
        """Test 6: Test streaming response"""
        self.print_header("TEST 6: Streaming Response")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "messages": [
                        {"role": "user", "content": "Tell me about my account"}
                    ],
                    "thread_id": "test-thread-003",
                    "stream": True
                }
                
                self.print_info("Testing streaming response...")
                
                async with client.stream(
                    "POST",
                    f"{self.base_url}/a2a/invoke",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if response.status_code != 200:
                        self.print_error(f"Streaming request failed with status {response.status_code}")
                        return False
                    
                    chunk_count = 0
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            chunk_count += 1
                    
                    if chunk_count > 0:
                        self.print_success(f"Streaming working ({chunk_count} chunks received)")
                        return True
                    else:
                        self.print_error("No streaming chunks received")
                        return False
                        
        except Exception as e:
            self.print_error("Streaming test failed", str(e))
            return False
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{BLUE}{'='*70}")
        print(f"  TEST SUMMARY")
        print(f"{'='*70}{RESET}\n")
        
        total = self.tests_passed + self.tests_failed
        
        if self.tests_failed == 0:
            print(f"{GREEN}✅ ALL TESTS PASSED ({self.tests_passed}/{total}){RESET}")
            print(f"\n{GREEN}🎉 AccountAgent A2A is ready for integration!{RESET}")
            print(f"\n{YELLOW}Next Steps:{RESET}")
            print(f"  1. Set USE_A2A_FOR_ACCOUNT_AGENT=true in main .env")
            print(f"  2. Restart backend: cd app/copilot && python -m uvicorn app.main:app --reload")
            print(f"  3. Test via frontend: http://localhost:8081")
        else:
            print(f"{RED}❌ {self.tests_failed} TEST(S) FAILED{RESET}")
            print(f"{GREEN}✅ {self.tests_passed} test(s) passed{RESET}")
            print(f"\n{YELLOW}Fix the failing tests before proceeding to integration.{RESET}")
        
        print()
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"\n{BLUE}{'='*70}")
        print(f"  AccountAgent A2A Integration Test Suite")
        print(f"  Testing service at: {self.base_url}")
        print(f"{'='*70}{RESET}")
        
        # Test 1: Health Check (required for all other tests)
        if not await self.test_health_check():
            self.print_error("Service not running - skipping remaining tests")
            self.print_summary()
            return False
        
        # Test 2: Agent Card Discovery
        await self.test_agent_card_discovery()
        
        # Test 3: Environment Configuration
        await self.test_environment_config()
        
        # Test 4: Simple Chat
        await self.test_simple_chat()
        
        # Test 5: Streaming Response
        await self.test_streaming_response()
        
        # Test 6: MCP Tool Usage (may fail if MCP servers not running)
        self.print_info("MCP tool test requires Account and Limits MCP servers running")
        await self.test_mcp_tool_usage()
        
        # Print summary
        self.print_summary()
        
        return self.tests_failed == 0


async def main():
    """Main test entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test AccountAgent A2A Microservice")
    parser.add_argument(
        "--url",
        default="http://localhost:9001",
        help="A2A service URL (default: http://localhost:9001)"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only quick tests (skip MCP tool test)"
    )
    
    args = parser.parse_args()
    
    runner = A2ATestRunner(base_url=args.url)
    success = await runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
