"""
Payment Agent v2 Handler - Azure AI Foundry with Agent Framework

Uses agent-framework (PyPI packages) to create Payment Agent in Foundry with:
- Azure AI Foundry V2 (azure-ai-projects)
- Unified MCP Tool for payment operations (with audit logging)
- A2A protocol support for supervisor routing
"""

import logging
from typing import AsyncGenerator

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIClient  # Use AzureAIClient to reference existing Foundry agent
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

from audited_mcp_tool import AuditedMCPTool  # Audit wrapper for compliance
from config import (
    AZURE_AI_PROJECT_ENDPOINT,
    PAYMENT_AGENT_NAME,
    PAYMENT_AGENT_VERSION,
    PAYMENT_AGENT_MODEL_DEPLOYMENT,
    PAYMENT_UNIFIED_MCP_URL,
    PAYMENT_AGENT_CONFIG,
)

logger = logging.getLogger(__name__)


class PaymentAgentHandler:
    """
    Payment Agent Handler using Agent Framework with Azure AI Foundry
    
    Pattern based on: agent-framework-1/python/samples/getting_started/agents/a2a/
    
    Architecture:
    - Agent created in Azure AI Foundry (cloud service)
    - Agent Framework provides Python SDK wrapper
    - Unified MCP tool connects to payment business logic
    - A2A protocol enables supervisor routing
    """

    # Thread state storage (shared across all handler instances)
    thread_store: dict[str, dict[str, any]] = {}

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
        """Create unified MCP tool instance with audit logging"""
        logger.info(f"Creating MCP connection for thread={thread_id}")

        # Unified Payment MCP Tool (with audit logging)
        mcp_tool = AuditedMCPTool(
            name="Payment Unified MCP Server",
            url=PAYMENT_UNIFIED_MCP_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="payment-unified",
            headers={},
            description="Unified payment operations: accounts, beneficiaries, limits, transfers",
        )
        await mcp_tool.connect()
        
        logger.info("✅ MCP connection established (unified server)")

        return mcp_tool

    async def _get_user_email(self, customer_id: str) -> str:
        """Get user email from customer_id using UserMapper (dynamic lookup)"""
        # Try to use UserMapper for dynamic customer lookup
        try:
            # Import here to avoid circular dependencies
            import sys
            from pathlib import Path
            
            # Add copilot to path to access user_mapper
            copilot_path = Path(__file__).parent.parent.parent / "copilot"
            if str(copilot_path) not in sys.path:
                sys.path.insert(0, str(copilot_path))
            
            from app.auth.user_mapper import get_user_mapper
            
            user_mapper = get_user_mapper()
            customer_info = user_mapper.get_customer_info(customer_id)
            
            if customer_info:
                user_mail = customer_info.get("email")
                logger.info(f"📧 [UserMapper] {customer_id} → {user_mail}")
                return user_mail
            else:
                logger.warning(f"⚠️ [UserMapper] No customer found for {customer_id}, using fallback")
        except Exception as e:
            logger.warning(f"⚠️ [UserMapper] Error looking up customer: {e}, using fallback")
        
        # Fallback to static mapping if UserMapper fails
        customer_email_map = {
            "CUST-001": "somchai@bankxthb.onmicrosoft.com",
            "CUST-002": "nattaporn@bankxthb.onmicrosoft.com",
            "CUST-003": "pimchanok@bankxthb.onmicrosoft.com",
            "CUST-004": "anan@bankxthb.onmicrosoft.com",
        }
        
        user_mail = customer_email_map.get(customer_id, "somchai@bankxthb.onmicrosoft.com")
        logger.info(f"📧 [Fallback] {customer_id} → {user_mail}")
        return user_mail

    async def get_agent(self, thread_id: str, customer_id: str) -> ChatAgent:
        """
        Get or create ChatAgent for this thread with shared MCP tool
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

        # Get user email for instructions
        user_email = await self._get_user_email(customer_id)
        full_instructions = self.instructions.replace("{user_mail}", user_email)

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
            model=PAYMENT_AGENT_MODEL_DEPLOYMENT,
            tools=[mcp_tool],
            instructions=full_instructions,
        )
        
        # Note: Azure creates thread on first message - thread ID available after first run

        # Cache the agent using the local thread_id for lookup
        # Note: We use local thread_id as cache key, but agent uses Azure's thread internally
        self._cached_agents[thread_id] = chat_agent
        logger.info(f"💾 [CACHE STORED] PaymentAgent cached for thread={thread_id}")

        return chat_agent

    async def process_message(
        self, 
        message: str, 
        thread_id: str, 
        customer_id: str,
        user_email: str | None = None,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Process a message using the PaymentAgent with thread continuity
        Returns streaming response
        """
        import time
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
        from a2a_banking_telemetry import get_a2a_telemetry
        
        start_time = time.time()
        logger.info(f"Processing message for thread={thread_id}, customer={customer_id}, stream={stream}")
        
        # Initialize telemetry
        telemetry = get_a2a_telemetry("PaymentAgent")
        
        # Get or create agent for this thread
        agent = await self.get_agent(thread_id=thread_id, customer_id=customer_id)

        # Get or create thread object for conversation continuity
        if thread_id in PaymentAgentHandler.thread_store:
            # Resume existing thread with conversation history
            logger.info(f"⚡ [THREAD RESUME] Restoring thread={thread_id} with conversation history")
            current_thread = agent.get_new_thread()
            await current_thread.update_from_thread_state(PaymentAgentHandler.thread_store[thread_id])
        else:
            # Create new thread
            logger.info(f"🆕 [NEW THREAD] Creating new thread={thread_id}")
            current_thread = agent.get_new_thread()

        # Track response metrics
        full_response = ""
        
        try:
            # Process message with streaming
            if stream:
                async for chunk in agent.run_stream(message, thread=current_thread):
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        yield chunk.text
            else:
                result = await agent.run(message, thread=current_thread)
                full_response = result.text
                yield result.text
            
            # Save thread state for next request
            PaymentAgentHandler.thread_store[thread_id] = await current_thread.serialize()
            logger.info(f"💾 [THREAD SAVED] Thread state saved for thread={thread_id}")
            
            # Log successful execution
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC4_PAYMENT_AGENT",
                reasoning="Payment query routed to PaymentAgent via A2A",
                tools_considered=["payment-unified-mcp"],
                tools_invoked=[{"tool": "payment-unified-mcp", "status": "success"}],
                result_status="success",
                result_summary=f"Response generated ({len(full_response)} chars)",
                duration_seconds=duration,
                context={"customer_id": customer_id}
            )
            
        except Exception as e:
            # Log failed execution
            duration = time.time() - start_time
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC4_PAYMENT_AGENT",
                reasoning="Payment query failed in PaymentAgent",
                tools_considered=["payment-unified-mcp"],
                tools_invoked=[{"tool": "payment-unified-mcp", "status": "error", "error": str(e)}],
                result_status="error",
                result_summary=str(e),
                duration_seconds=duration,
                context={"customer_id": customer_id, "error": str(e)}
            )
            yield f"I apologize, but I encountered an error: {str(e)}"

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up resources")
        
        try:
            # Close MCP connection if exists
            if self._mcp_tool_cache:
                # MCP tool cleanup if needed
                pass
            
            # Clear caches
            self._cached_agents.clear()
            self._mcp_tool_cache = None
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.warning(f"⚠️ Cleanup error: {e}")
