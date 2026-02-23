"""
Payment Agent v2 Handler - Azure AI Foundry with Agent Framework

Uses agent-framework to reference existing Payment Agent v2 in Foundry with:
- Azure AI Foundry V2 (azure-ai-projects)
- Unified Payment MCP tool for transfers
- A2A protocol support for supervisor routing

Pattern: Agent created ONCE in Azure AI Foundry via create_agent_in_foundry.py,
then REFERENCED here by name+version (not recreated on every request).
"""

import logging
from typing import AsyncGenerator

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

from audited_mcp_tool import AuditedMCPTool
from config import (
    AZURE_AI_PROJECT_ENDPOINT,
    PAYMENT_AGENT_NAME,
    PAYMENT_AGENT_VERSION,
    PAYMENT_AGENT_MODEL_DEPLOYMENT,
    PAYMENT_UNIFIED_MCP_URL,
)

logger = logging.getLogger(__name__)


class PaymentAgentHandler:
    """
    Payment Agent v2 Handler using Agent Framework with Azure AI Foundry
    
    Architecture:
    - Agent created in Azure AI Foundry (cloud service) via create_agent_in_foundry.py
    - Agent  Framework provides Python SDK wrapper
    - MCP tool connects to unified payment MCP server
    - A2A protocol enables supervisor routing
    """

    def __init__(self):
        self.credential = None
        self.instructions: str = ""
        self.project_client = None
        
        # Agent caching (per thread)
        self._cached_agents: dict[str, ChatAgent] = {}
        
        # MCP tool caching (shared across threads for performance)
        self._mcp_tool_cache: AuditedMCPTool | None = None
        
        logger.info("PaymentAgentHandler initialized (Agent Framework + Foundry V2)")

    async def initialize(self):
        """Initialize Azure AI resources"""
        # Create Azure CLI credential
        self.credential = AzureCliCredential()

        # Create AIProjectClient to reference existing Foundry agents
        self.project_client = AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=self.credential
        )

        # Load agent instructions from markdown file
        with open("prompts/payment_agent.md", "r", encoding="utf-8") as f:
            self.instructions = f.read()
        
        logger.info("✅ Handler initialized (Azure credential + AIProjectClient + instructions loaded)")

    async def _create_mcp_tool(self, customer_id: str | None = None, thread_id: str | None = None) -> AuditedMCPTool:
        """Create MCP tool instance for unified payment server with audit logging"""
        logger.info(f"Creating Payment MCP connection for thread={thread_id}")

        # Unified Payment MCP Tool (with audit logging)
        payment_mcp_tool = AuditedMCPTool(
            name="Payment Unified MCP Server",
            url=PAYMENT_UNIFIED_MCP_URL,
            customer_id=customer_id or "unknown",
            thread_id=thread_id or "unknown",
            mcp_server_name="payment-unified"
        )

        logger.info(f"✅ Payment MCP connection created: {PAYMENT_UNIFIED_MCP_URL}")
        return payment_mcp_tool

    async def get_agent(self, thread_id: str, customer_id: str, user_email: str) -> ChatAgent:
        """
        Get or create ChatAgent for this thread
        Implements agent caching per thread for performance
        MCP tool is shared across all threads for faster initialization
        """
        # Check cache first
        if thread_id in self._cached_agents:
            logger.info(f"⚡ [CACHE HIT] Reusing cached PaymentAgent for thread={thread_id}")
            return self._cached_agents[thread_id]

        logger.info(f"Building new PaymentAgent for thread={thread_id}, customer={customer_id}")

        # Reuse MCP tool if already created, otherwise create it once
        if self._mcp_tool_cache is None:
            logger.info("🔧 [MCP INIT] Creating MCP connection (first time)...")
            self._mcp_tool_cache = await self._create_mcp_tool(customer_id=customer_id, thread_id=thread_id)
            logger.info("✅ [MCP INIT] MCP connection created and cached")
        else:
            logger.info("⚡ [MCP CACHE] Reusing existing MCP connection")
        
        mcp_tool = self._mcp_tool_cache

        # Update instructions with customer context
        full_instructions = self.instructions + f"\n\n## Current Customer Context\n\n"
        full_instructions += f"- **Customer ID**: {customer_id}\n"
        full_instructions += f"- **Username (BankX Email)**: {user_email}\n"
        full_instructions += f"- **Thread ID**: {thread_id}\n"

        # Create AzureAIClient that references the EXISTING Foundry agent
        # This does NOT create a new agent - it references the agent created by create_agent_in_foundry.py
        azure_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=PAYMENT_AGENT_NAME,
            agent_version=PAYMENT_AGENT_VERSION,
        )
        logger.info(f"✅ AzureAIClient created - Referencing existing agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")

        # Create ChatAgent with MCP tool added dynamically
        # The Foundry agent has NO tools - we add them here to avoid duplication
        chat_agent = azure_client.create_agent(
            name=PAYMENT_AGENT_NAME,
            tools=[mcp_tool],
            instructions=full_instructions,
        )
        
        # Cache the agent
        self._cached_agents[thread_id] = chat_agent
        logger.info(f"💾 [CACHE STORED] PaymentAgent cached for thread={thread_id}")

        return chat_agent

    async def process_message(
        self, 
        user_message: str, 
        thread_id: str, 
        customer_id: str,
        user_email: str
    ) -> AsyncGenerator[str, None]:
        """
        Process a message and stream the response
        
        Args:
            user_message: User's message text
            thread_id: Conversation thread ID
            customer_id: Customer ID (e.g., "CUST-001")
            user_email: Customer's BankX email
            
        Yields:
            Response chunks as they're generated
        """
        logger.info(f"[PAYMENT V2] Processing message for {customer_id}: {user_message[:100]}...")
        
        try:
            # Get or create agent for this thread
            agent = await self.get_agent(thread_id, customer_id, user_email)
            
            # Stream response
            async for chunk in agent.run_stream(
                user_message=user_message,
                thread_id=thread_id
            ):
                yield chunk
            
            logger.info(f"[PAYMENT V2] ✅ Message processed successfully")
            
        except Exception as e:
            logger.error(f"[PAYMENT V2] ❌ Error processing message: {e}", exc_info=True)
            yield f"I apologize, but I encountered an error: {str(e)}"

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("[PAYMENT V2] 🧹 Cleaning up resources")
        
        try:
            if self.credential:
                await self.credential.close()
            
            # Clear caches
            self._cached_agents.clear()
            self._mcp_tool_cache = None
            
            logger.info("[PAYMENT V2] ✅ Cleanup completed")
            
        except Exception as e:
            logger.warning(f"[PAYMENT V2] ⚠️  Cleanup error: {e}")

    def __repr__(self):
        return f"PaymentAgentHandler(agent={PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION})"
