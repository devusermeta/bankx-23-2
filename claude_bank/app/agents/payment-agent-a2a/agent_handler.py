"""
Payment Agent Handler - Azure AI Foundry with Agent Framework

Uses agent-framework (PyPI packages) to create PaymentAgent in Foundry with:
- Azure AI Foundry V2 (azure-ai-projects)
- MCP Tools for account, transaction, payment, and contacts data (with audit logging)
- A2A protocol support for supervisor routing
"""

import logging
from typing import AsyncGenerator, Any

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
    ACCOUNT_MCP_SERVER_URL,
    TRANSACTION_MCP_SERVER_URL,
    PAYMENT_MCP_SERVER_URL,
    CONTACTS_MCP_SERVER_URL,
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
    - MCP tools connect to business logic microservices (4 servers)
    - A2A protocol enables supervisor routing
    """

    # Thread state storage (shared across all handler instances) 
    thread_store: dict[str, dict[str, Any]] = {}

    def __init__(self):
        self.credential = None
        self.instructions: str = ""
        self.project_client = None
        
        # Agent caching (per thread)
        self._cached_agents: dict[str, ChatAgent] = {}
        
        # MCP tool caching (shared across threads for performance)
        self._mcp_tools_cache: list | None = None
        
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

    async def _create_mcp_tools(self, customer_id: str | None = None, thread_id: str | None = None) -> list:
        """Create fresh MCP tool instances for each request with audit logging"""
        logger.info(f"Creating MCP connections for thread={thread_id}")

        # Account MCP Tool (with audit logging)
        account_mcp_tool = AuditedMCPTool(
            name="Account MCP Server",
            url=ACCOUNT_MCP_SERVER_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="account",
            headers={},
            description="Access customer account information including balances, account details, and payment methods",
        )
        await account_mcp_tool.connect()

        # Transaction MCP Tool (with audit logging)
        transaction_mcp_tool = AuditedMCPTool(
            name="Transaction MCP Server",
            url=TRANSACTION_MCP_SERVER_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="transaction",
            headers={},
            description="Access transaction history and details",
        )
        await transaction_mcp_tool.connect()

        # Payment MCP Tool (with audit logging)
        payment_mcp_tool = AuditedMCPTool(
            name="Payment MCP Server",
            url=PAYMENT_MCP_SERVER_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="payment",
            headers={},
            description="Process payments, manage beneficiaries, and handle payment operations",
        )
        await payment_mcp_tool.connect()

        # Contacts MCP Tool (with audit logging)
        contacts_mcp_tool = AuditedMCPTool(
            name="Contacts MCP Server",
            url=CONTACTS_MCP_SERVER_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="contacts",
            headers={},
            description="Manage beneficiaries and contact information for payments",
        )
        await contacts_mcp_tool.connect()
        
        logger.info("✅ MCP connections established (Account + Transaction + Payment + Contacts) with audit logging")

        return [account_mcp_tool, transaction_mcp_tool, payment_mcp_tool, contacts_mcp_tool]

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
        Get or create ChatAgent for this thread with shared MCP tools
        Implements agent caching per thread for performance
        MCP tools are shared across all threads for faster initialization
        """
        # Check cache first
        if thread_id in self._cached_agents:
            logger.info(f"⚡ [CACHE HIT] Reusing cached PaymentAgent for thread={thread_id}")
            return self._cached_agents[thread_id]

        logger.info(f"Building new PaymentAgent for thread={thread_id}, customer={customer_id}")

        # Reuse MCP tools if already created, otherwise create them once
        if self._mcp_tools_cache is None:
            logger.info("🔧 [MCP INIT] Creating MCP connections (first time)...")
            self._mcp_tools_cache = await self._create_mcp_tools(customer_id=customer_id, thread_id=thread_id)
            logger.info("✅ [MCP INIT] MCP connections created and cached")
        else:
            logger.info("⚡ [MCP CACHE] Reusing existing MCP connections")
        
        mcp_tools = self._mcp_tools_cache

        # Get user email for instructions
        user_email = await self._get_user_email(customer_id)
        full_instructions = self.instructions.replace("{user_mail}", user_email)

        # Create AzureAIClient that references the EXISTING Foundry agent
        azure_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=PAYMENT_AGENT_NAME,
            agent_version=PAYMENT_AGENT_VERSION,
        )
        logger.info(f"✅ AzureAIClient created - Referencing existing agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")

        # Create ChatAgent with MCP tools added dynamically
        chat_agent = azure_client.create_agent(
            name=PAYMENT_AGENT_NAME,
            tools=mcp_tools,
            instructions=full_instructions,
        )

        # Cache the agent
        self._cached_agents[thread_id] = chat_agent
        logger.info(f"💾 [CACHE STORED] PaymentAgent cached for thread={thread_id}")

        return chat_agent

    async def process_message(
        self, 
        message: str, 
        thread_id: str, 
        customer_id: str,
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
        
        # Initialize telemetry
        telemetry = get_a2a_telemetry("PaymentAgent")
        

        logger.info(f"Processing message for thread={thread_id}, customer={customer_id}, stream={stream}")
        
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

        # # Process message with streaming
        # if stream:
        #     async for chunk in agent.run_stream(message, thread=current_thread):
        #         if hasattr(chunk, 'text') and chunk.text:
        #             yield chunk.text
        # else:
        #     result = await agent.run(message, thread=current_thread)
        #     yield result.text
        
        # # Save thread state for next request
        # PaymentAgentHandler.thread_store[thread_id] = await current_thread.serialize()
        # logger.info(f"💾 [THREAD SAVED] Thread state saved for thread={thread_id}")

        # Track response metrics
        start_time = time.time()
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
                tools_considered=["createPayment", "getBeneficiaryByName"],
                tools_invoked=[{"tool": "payment_mcp", "status": "success"}],
                result_status="success",
                result_summary=f"Response generated ({len(full_response)} chars)",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a"}
            )
            
            # Log user message
            telemetry.log_user_message(
                thread_id=thread_id,
                user_query=message,
                response_text=full_response,
                duration_seconds=duration
            )
            
        except Exception as e:
            # Log error case
            duration = time.time() - start_time
            logger.error(f"❌ Error processing message: {str(e)}")
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC4_PAYMENT_AGENT",
                reasoning="Payment query routed to PaymentAgent via A2A",
                tools_considered=["createPayment", "getBeneficiaryByName"],
                tools_invoked=[],
                result_status="error",
                result_summary=f"Error: {str(e)}",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a", "error": str(e)}
            )
            raise


    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up PaymentAgentHandler resources")
        
        # Clear cached agents
        self._cached_agents.clear()
        
        # Close project client
        if self.project_client:
            await self.project_client.close()
            logger.info("✅ AIProjectClient closed")
        
        # Close credential
        if self.credential:
            await self.credential.close()
            logger.info("✅ Azure credential closed")


# Global handler instance
_handler: PaymentAgentHandler | None = None


async def get_payment_agent_handler() -> PaymentAgentHandler:
    """Get or create the global PaymentAgentHandler instance"""
    global _handler
    
    if _handler is None:
        _handler = PaymentAgentHandler()
        await _handler.initialize()
        logger.info("PaymentAgentHandler singleton initialized")
    
    return _handler


async def cleanup_handler():
    """Cleanup the global handler"""
    global _handler
    
    if _handler is not None:
        await _handler.cleanup()
        _handler = None
        logger.info("PaymentAgentHandler singleton cleaned up")
