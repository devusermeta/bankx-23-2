"""
Agent Handler - Manages the lifecycle of the Account Agent
Uses Azure AI Foundry to reference existing agent and connect MCP tools
"""

import logging
from typing import List, Dict, Any, Optional
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from agent_framework.azure import AzureAIClient

from config import get_settings

settings = get_settings()
logger = logging.getLogger("account-agent")


# Global singleton instance
_agent_handler: Optional['AccountAgentHandler'] = None


class AccountAgentHandler:
    """Handler for Account Agent with singleton pattern"""
    
    def __init__(self):
        self.agent: Optional[ChatAgent] = None
        self.credential: Optional[AzureCliCredential] = None
        self.mcp_tool: Optional[MCPStreamableHTTPTool] = None
        self.project_client: Optional[AIProjectClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the agent (called once on startup)"""
        if self._initialized:
            logger.warning("⚠️ Agent handler already initialized")
            return
        
        print("\n" + "=" * 80)
        print("🔧 Initializing Account Agent Handler")
        print("=" * 80)
        logger.info("🔧 Initializing Account Agent Handler")
        logger.info(f"📋 Configuration:")
        logger.info(f"   Agent: {settings.account_agent_name}:{settings.account_agent_version}")
        logger.info(f"   Model: {settings.azure_ai_model_deployment_name}")
        logger.info(f"   Endpoint: {settings.azure_ai_project_endpoint}")
        logger.info(f"   MCP URL: {settings.account_mcp_server_url}")
        
        try:
            # Create credential
            print("🔑 Creating Azure CLI credential...")
            self.credential = AzureCliCredential()
            print("✅ Azure CLI credential created")
            logger.info("✅ Azure CLI credential created")
            
            # Create MCP tool connection
            print(f"🔌 Connecting to MCP server at {settings.account_mcp_server_url}...")
            self.mcp_tool = MCPStreamableHTTPTool(
                name="account_mcp",
                url=settings.account_mcp_server_url,
            )
            print("✅ MCP tool connected")
            logger.info(f"✅ MCP tool connected to {settings.account_mcp_server_url}")
            
            # Create AIProjectClient
            print("🏗️ Creating AIProjectClient...")
            self.project_client = AIProjectClient(
                endpoint=settings.azure_ai_project_endpoint,
                credential=self.credential
            )
            print("✅ AIProjectClient created")
            logger.info(f"✅ AIProjectClient created for {settings.azure_ai_project_endpoint}")
            
            # Create AzureAIClient that references the EXISTING Foundry agent
            print(f"🤖 Creating AzureAIClient for agent {settings.account_agent_name}:{settings.account_agent_version}...")
            azure_client = AzureAIClient(
                project_client=self.project_client,
                agent_name=settings.account_agent_name,
                agent_version=settings.account_agent_version,
            )
            print("✅ AzureAIClient created (references existing Foundry agent)")
            logger.info(f"✅ AzureAIClient created - referencing agent {settings.account_agent_name}:{settings.account_agent_version}")
            
            # Create ChatAgent with MCP tools added dynamically
            # Add strict instructions to FORCE tool usage (anti-hallucination)
            print("🔧 Building ChatAgent with MCP tools...")
            
            agent_instructions = """You are an Account Agent for a banking system. You have access to real-time banking data through MCP tools.

CRITICAL RULES - MANDATORY TOOL USAGE:
1. You MUST ALWAYS use the available MCP tools to retrieve account information
2. NEVER provide account details, balances, limits, or transaction information from memory or general knowledge
3. NEVER make up or guess account numbers, balances, or limits
4. For EVERY query about accounts, balances, limits, or transactions:
   - ALWAYS call the appropriate tool FIRST
   - ONLY respond based on the tool's actual results
   - If a tool returns no data, say "I could not find that information"

Available Tools and When to Use Them:
- getAccountsByUserName: When user provides email address to find their accounts
- getAccountDetails: When you need account balance and details for a specific account ID
- getPaymentMethodDetails: When you need payment method information for an account
- checkLimits: When you need to verify if a transaction amount is allowed
- getAccountLimits: When you need to show transaction limits for an account

Example Workflows:
- "What accounts does user@example.com have?" → MUST call getAccountsByUserName
- "What is the balance of CHK-001?" → MUST call getAccountDetails
- "Can I transfer 5000 from CHK-001?" → MUST call checkLimits
- "What are my limits?" → MUST call getAccountLimits

If you cannot determine which tool to call or need clarification from the user, ask for the specific information needed (email, account ID, amount, etc.).

NEVER respond with generic banking information. ALWAYS use the tools to get real data."""

            self.agent = azure_client.create_agent(
                name=settings.account_agent_name,
                tools=[self.mcp_tool],
                instructions=agent_instructions,
            )
            print("✅ ChatAgent created")
            print(f"   Agent Name: {self.agent.name}")
            print(f"   Chat Client Type: {type(self.agent.chat_client).__name__}")
            print(f"   MCP Tools: Added dynamically")
            
            print("=" * 80)
            print(f"📋 Agent Details:")
            print(f"   Name: {settings.account_agent_name}")
            print(f"   Version: {settings.account_agent_version}")
            print(f"   MCP Server: {settings.account_mcp_server_url}")
            print(f"   Model: {settings.azure_ai_model_deployment_name}")
            print("=" * 80 + "\n")
            
            logger.info(f"✅ ChatAgent created successfully")
            logger.info(f"   Agent Name: {self.agent.name}")
            logger.info(f"   MCP Tools: Connected")
            
            self._initialized = True
            
        except Exception as e:
            print(f"❌ INITIALIZATION FAILED: {str(e)}")
            print("=" * 80 + "\n")
            logger.error(f"❌ Failed to initialize agent: {e}", exc_info=True)
            raise
    
    async def process_message(
        self,
        messages: List[Dict[str, str]],
        thread_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Process a message using the Account Agent
        
        Args:
            messages: List of conversation messages
            thread_id: Thread ID for conversation continuity
            customer_id: Customer identifier
            stream: Whether to stream the response
        
        Returns:
            Response dictionary with role, content, and agent name
        """
        if not self._initialized:
            raise RuntimeError("Agent handler not initialized. Call initialize() first.")
        
        # Extract the latest user message
        user_message = messages[-1]["content"] if messages else ""
        
        print("\n" + "=" * 80)
        print("💬 Processing User Message")
        print("=" * 80)
        print(f"📝 User Query: {user_message}")
        print(f"🧵 Thread ID: {thread_id or 'None (new thread)'}")
        print(f"👤 Customer ID: {customer_id or 'None'}")
        print("=" * 80)
        
        logger.info(f"Processing message - Thread: {thread_id}, Customer: {customer_id}")
        logger.info(f"User message: {user_message}")
        
        try:
            # Run the agent with the user message
            print("\n🤖 Calling agent.run()...")
            print("   (This should call the MCP tools for account/limits data)")
            logger.info("🤖 Invoking agent.run()")
            
            response = await self.agent.run(user_message)
            
            print("✅ Agent execution completed")
            print(f"📊 Response Type: {type(response).__name__}")
            logger.info(f"✅ Agent execution completed")
            logger.info(f"📊 Response Type: {type(response).__name__}")
            
            # Extract text from AgentRunResponse object
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            print(f"💡 Response Length: {len(response_text)} characters")
            print(f"📤 Response Preview: {response_text[:200]}..." if len(response_text) > 200 else f"📤 Response: {response_text}")
            print("=" * 80 + "\n")
            
            logger.info(f"💡 Response length: {len(response_text)} characters")
            logger.info(f"📤 Response: {response_text[:500]}..." if len(response_text) > 500 else f"📤 Response: {response_text}")
            logger.info("=" * 80)
            
            return {
                "role": "assistant",
                "content": response_text,
                "agent_name": settings.account_agent_name,
                "agent_version": settings.account_agent_version,
                "thread_id": thread_id
            }
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            print(f"\n❌ {error_msg}")
            print("=" * 80 + "\n")
            logger.error(error_msg, exc_info=True)
            raise
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up Account Agent Handler")
        if self.credential:
            await self.credential.close()
        if self.project_client:
            await self.project_client.close()
        logger.info("✅ Cleanup complete")


async def get_agent_handler() -> AccountAgentHandler:
    """Get or create the global agent handler instance"""
    global _agent_handler
    
    if _agent_handler is None:
        _agent_handler = AccountAgentHandler()
        await _agent_handler.initialize()
    
    return _agent_handler
