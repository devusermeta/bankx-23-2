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
            print("🔧 Building ChatAgent with MCP tools...")
            self.agent = azure_client.create_agent(
                name=settings.account_agent_name,
                tools=[self.mcp_tool],
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
            # Process with agent
            print("\n🤖 Calling Account Agent...")
            result = await self.agent.ask(user_message, thread_id=thread_id)
            
            # Extract response
            response_text = result.response.content if result.response else ""
            
            print("\n✅ Agent Response Received")
            print(f"📄 Response Length: {len(response_text)} characters")
            print("=" * 80 + "\n")
            
            logger.info(f"✅ Agent response received: {len(response_text)} characters")
            
            return {
                "role": "assistant",
                "content": response_text,
                "agent_name": settings.account_agent_name,
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
