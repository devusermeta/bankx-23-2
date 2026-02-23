"""
Payment Agent v2 Handler - Simplified Transfer Agent

References existing Azure AI Foundry agent (created once by create_agent_in_foundry.py).
Uses unified Payment MCP Server for all transfer operations.
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
    Payment Agent v2 Handler - References existing Foundry agent
    
    Architecture:
    - Agent ALREADY EXISTS in Azure AI Foundry (created once by create_agent_in_foundry.py)
    - This handler REFERENCES that agent (never creates new ones)
    - MCP unified tool connects to payment-unified business logic
    - A2A protocol enables supervisor routing
    """

    def __init__(self):
        self.credential = None
        self.instructions: str = ""
        self.project_client = None
        
        # Agent caching (per thread)
        self._cached_agents: dict[str, ChatAgent] = {}
        
        # MCP tool caching (shared across threads)
        self._mcp_tool_cache: AuditedMCPTool | None = None
        
        logger.info("[PAYMENT AGENT V2] Handler initialized")

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
        
        logger.info("[PAYMENT AGENT V2] ✅ Initialized (credential + project client + instructions)")

    async def _create_mcp_tool(self, customer_id: str | None = None, thread_id: str | None = None) -> AuditedMCPTool:
        """Create unified MCP tool instance with audit logging"""
        logger.info(f"[PAYMENT AGENT V2] Creating unified MCP connection for thread={thread_id}")

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
        
        logger.info("[PAYMENT AGENT V2] ✅ MCP connection established (unified server)")

        return mcp_tool

    async def _get_user_email(self, customer_id: str) -> str:
        """Get user email from customer_id using UserMapper (dynamic lookup)"""
        try:
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
                user_email = customer_info.get("bankx_email") or customer_info.get("email")
                logger.info(f"[PAYMENT AGENT V2] 📧 {customer_id} → {user_email}")
                return user_email
            else:
                logger.warning(f"[PAYMENT AGENT V2] ⚠️ No customer found for {customer_id}")
        except Exception as e:
            logger.warning(f"[PAYMENT AGENT V2] ⚠️ Error looking up customer: {e}")
        
        # Fallback
        return "user@bankx.com"

    async def get_agent(self, thread_id: str, customer_id: str, user_email: str | None = None) -> ChatAgent:
        """
        Get or create ChatAgent for this thread
        REFERENCES existing agent in Azure AI Foundry (doesn't create new)
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"[PAYMENT AGENT V2] 🔧 GET_AGENT CALLED")
        logger.info(f"[PAYMENT AGENT V2]   thread_id: {thread_id}")
        logger.info(f"[PAYMENT AGENT V2]   customer_id: {customer_id}")
        logger.info(f"[PAYMENT AGENT V2]   user_email: {user_email}")
        logger.info(f"{'='*80}\n")
        
        # Check cache first
        if thread_id in self._cached_agents:
            logger.info(f"[PAYMENT AGENT V2] ⚡ Reusing cached agent for thread={thread_id}")
            return self._cached_agents[thread_id]

        logger.info(f"[PAYMENT AGENT V2] 🆕 Building NEW agent reference for thread={thread_id}, customer={customer_id}")

        # Reuse MCP tool if already created
        if self._mcp_tool_cache is None:
            logger.info("[PAYMENT AGENT V2] 🔧 Creating MCP connection (FIRST TIME)...")
            self._mcp_tool_cache = await self._create_mcp_tool(customer_id=customer_id, thread_id=thread_id)
            logger.info("[PAYMENT AGENT V2] ✅ MCP connection created and cached")
        else:
            logger.info("[PAYMENT AGENT V2] ⚡ Reusing CACHED MCP connection")
        
        mcp_tool = self._mcp_tool_cache

        # Get user email if not provided
        if not user_email:
            logger.info(f"[PAYMENT AGENT V2] 📧 Looking up user_email for customer={customer_id}...")
            user_email = await self._get_user_email(customer_id)
            logger.info(f"[PAYMENT AGENT V2] 📧 Found user_email: {user_email}")
        else:
            logger.info(f"[PAYMENT AGENT V2] 📧 Using provided user_email: {user_email}")

        # Inject customer context into instructions
        logger.info(f"[PAYMENT AGENT V2] 📝 Injecting customer context into instructions...")
        full_instructions = self.instructions + f"\n\n## Current Customer Context\n\n"
        full_instructions += f"- **Customer ID**: {customer_id}\n"
        full_instructions += f"- **Username (BankX Email)**: {user_email}\n"
        full_instructions += f"- **Thread ID**: {thread_id}\n"
        logger.info(f"[PAYMENT AGENT V2] 📝 Instructions prepared ({len(full_instructions)} chars)")

        # Create AzureAIClient that references the EXISTING Foundry agent
        # This does NOT create a new agent - it references the agent created by create_agent_in_foundry.py
        logger.info(f"[PAYMENT AGENT V2] 🔗 Creating AzureAIClient to reference existing agent...")
        logger.info(f"[PAYMENT AGENT V2]   Agent Name: {PAYMENT_AGENT_NAME}")
        logger.info(f"[PAYMENT AGENT V2]   Agent Version: {PAYMENT_AGENT_VERSION}")
        
        azure_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=PAYMENT_AGENT_NAME,
            agent_version=PAYMENT_AGENT_VERSION,
        )
        logger.info(f"[PAYMENT AGENT V2] ✅ Referencing existing agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")

        # Create ChatAgent with MCP tool added dynamically
        # Explicitly pass model deployment since framework may not fetch it from Foundry
        logger.info(f"[PAYMENT AGENT V2] 🤖 Creating ChatAgent wrapper with MCP tools...")
        chat_agent = azure_client.create_agent(
            name=PAYMENT_AGENT_NAME,
            tools=[mcp_tool],
            instructions=full_instructions,
        )
        logger.info(f"[PAYMENT AGENT V2] ✅ ChatAgent created successfully")

        # Cache the agent
        self._cached_agents[thread_id] = chat_agent
        logger.info(f"[PAYMENT AGENT V2] 💾 Agent cached for thread={thread_id}")
        logger.info(f"[PAYMENT AGENT V2] 📊 Total cached agents: {len(self._cached_agents)}")

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
        Process a message using the Payment Agent v2
        Returns streaming response
        """
        import time
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
        from a2a_banking_telemetry import get_a2a_telemetry
        
        start_time = time.time()
        logger.info(f"[PAYMENT AGENT V2] Processing message for thread={thread_id}, customer={customer_id}")
        
        # Initialize telemetry
        telemetry = get_a2a_telemetry("PaymentAgentV2")
        
        # Get or create agent for this thread
        agent = await self.get_agent(thread_id=thread_id, customer_id=customer_id, user_email=user_email)

        # Collect response for logging
        full_response = ""
        tools_invoked = []
        
        try:
            logger.info(f"[PAYMENT AGENT V2] 🚀 Starting agent.run() - stream={stream}")
            logger.info(f"[PAYMENT AGENT V2] 📝 User message: {message[:100]}...")
            
            # Process message with streaming
            if stream:
                logger.info(f"[PAYMENT AGENT V2] 📤 Streaming mode enabled")
                async for chunk in agent.run_stream(message):
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        logger.debug(f"[PAYMENT AGENT V2] 📦 Chunk received: {len(chunk.text)} chars")
                        yield chunk.text
            else:
                logger.info(f"[PAYMENT AGENT V2] 📥 Non-streaming mode")
                result = await agent.run(message)
                full_response = result.text
                logger.info(f"[PAYMENT AGENT V2] ✅ Got response: {len(full_response)} chars")
                yield result.text
            
            # Log successful decision
            duration = time.time() - start_time
            logger.info(f"[PAYMENT AGENT V2] ⏱️ Processing completed in {duration:.3f}s")
            logger.info(f"[PAYMENT AGENT V2] 📊 Logging telemetry data...")
            
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC4_PAYMENT_AGENT_V2",
                reasoning="Transfer request processed via Payment Agent v2",
                tools_considered=["payment-unified-mcp"],
                tools_invoked=[{"tool": "payment-unified-mcp", "status": "success"}],
                result_status="success",
                result_summary=f"Response generated ({len(full_response)} chars)",
                duration_seconds=duration,
                context={"customer_id": customer_id, "user_email": user_email}
            )
            
            logger.info(f"[PAYMENT AGENT V2] ✅ Request completed successfully")
            
        except Exception as e:
            # Log failed decision
            duration = time.time() - start_time
            logger.error(f"[PAYMENT AGENT V2] ❌ Error processing message: {e}", exc_info=True)
            logger.info(f"[PAYMENT AGENT V2] 📊 Logging error telemetry...")
            
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC4_PAYMENT_AGENT_V2",
                reasoning="Transfer request failed in Payment Agent v2",
                tools_considered=["payment-unified-mcp"],
                tools_invoked=[{"tool": "payment-unified-mcp", "status": "error", "error": str(e)}],
                result_status="error",
                result_summary=str(e),
                duration_seconds=duration,
                context={"customer_id": customer_id, "user_email": user_email, "error": str(e)}
            )
            
            yield f"I apologize, but I encountered an error: {str(e)}"

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("[PAYMENT AGENT V2] 🧹 Cleaning up resources")
        
        try:
            # Close MCP connection if exists
            if self._mcp_tool_cache:
                # MCP tool cleanup if needed
                pass
            
            # Clear caches
            self._cached_agents.clear()
            self._mcp_tool_cache = None
            
            logger.info("[PAYMENT AGENT V2] ✅ Cleanup completed")
            
        except Exception as e:
            logger.warning(f"[PAYMENT AGENT V2] ⚠️ Cleanup error: {e}")
