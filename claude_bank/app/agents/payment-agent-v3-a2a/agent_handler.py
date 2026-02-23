"""
Payment Agent V3 Handler - Azure AI Foundry with Agent Framework

2-tool flow:
  1. prepareTransfer  → validates + returns all confirmation data (READ-ONLY)
  2. executeTransfer  → executes AFTER user says yes (WRITE)
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
    PAYMENT_AGENT_CONFIG,
)

logger = logging.getLogger(__name__)


class PaymentAgentV3Handler:
    """
    Payment Agent V3 Handler using Agent Framework with Azure AI Foundry.

    2-tool design:
    - prepareTransfer  : READ-ONLY, safe to auto-approve - validates and returns preview data
    - executeTransfer  : WRITE, requires explicit user approval - moves real money
    """

    def __init__(self):
        self.credential = None
        self.instructions: str = ""
        self.project_client = None

        # Agent caching (per thread)
        self._cached_agents: dict[str, ChatAgent] = {}

        # MCP tool caching (shared across threads)
        self._mcp_tools_cache: list | None = None

        logger.info("PaymentAgentV3Handler initialized")

    async def initialize(self):
        """Initialize Azure AI resources"""
        self.credential = AzureCliCredential()

        self.project_client = AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=self.credential
        )

        # Load instructions from prompts file
        with open("prompts/payment_agent.md", "r", encoding="utf-8") as f:
            self.instructions = f.read()

        logger.info("✅ PaymentAgentV3Handler initialized (credential + client + instructions loaded)")

    async def _create_mcp_tools(self, customer_id: str | None = None, thread_id: str | None = None) -> list:
        """Create MCP tool connection to payment-unified MCP server"""
        logger.info(f"Creating payment MCP connection for thread={thread_id}")

        payment_mcp_tool = AuditedMCPTool(
            name="Payment MCP Server",
            url=PAYMENT_UNIFIED_MCP_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="payment",
            headers={},
            description="Execute bank transfers using prepareTransfer and executeTransfer tools",
        )
        await payment_mcp_tool.connect()

        logger.info("✅ Payment MCP connection established")
        return [payment_mcp_tool]

    async def _get_user_email(self, customer_id: str) -> str:
        """Get user email from customer_id"""
        try:
            import sys
            from pathlib import Path

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
        except Exception as e:
            logger.warning(f"⚠️ [UserMapper] Error: {e}, using fallback")

        # Fallback static mapping
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
        """Get or create ChatAgent for this thread"""
        if thread_id in self._cached_agents:
            logger.info(f"⚡ [CACHE HIT] Reusing cached PaymentAgentV3 for thread={thread_id}")
            return self._cached_agents[thread_id]

        logger.info(f"Building new PaymentAgentV3 for thread={thread_id}, customer={customer_id}")

        # Reuse MCP tools if already created
        if self._mcp_tools_cache is None:
            logger.info("🔧 [MCP INIT] Creating MCP connection (first time)...")
            self._mcp_tools_cache = await self._create_mcp_tools(customer_id=customer_id, thread_id=thread_id)
            logger.info("✅ [MCP INIT] MCP connection created and cached")
        else:
            logger.info("⚡ [MCP CACHE] Reusing existing MCP connection")

        mcp_tools = self._mcp_tools_cache

        # Inject user email into instructions
        user_email = await self._get_user_email(customer_id)
        full_instructions = self.instructions.replace("{user_email}", user_email)

        # Reference the existing Foundry agent
        azure_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=PAYMENT_AGENT_NAME,
            agent_version=PAYMENT_AGENT_VERSION,
        )
        logger.info(f"✅ AzureAIClient referencing agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")

        chat_agent = azure_client.create_agent(
            name=PAYMENT_AGENT_NAME,
            tools=mcp_tools,
            instructions=full_instructions,
        )

        self._cached_agents[thread_id] = chat_agent
        logger.info(f"💾 [CACHE STORED] PaymentAgentV3 cached for thread={thread_id}")

        return chat_agent

    async def process_message(
        self,
        message: str,
        thread_id: str,
        customer_id: str,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """Process a message using the PaymentAgentV3"""
        import time
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
        from a2a_banking_telemetry import get_a2a_telemetry

        start_time = time.time()
        logger.info(f"Processing message for thread={thread_id}, customer={customer_id}")

        telemetry = get_a2a_telemetry("PaymentAgentV3")
        agent = await self.get_agent(thread_id=thread_id, customer_id=customer_id)

        full_response = ""

        try:
            if stream:
                async for chunk in agent.run_stream(message):
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        yield chunk.text
            else:
                result = await agent.run(message)
                full_response = result.text
                yield result.text

            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC2_PAYMENT_AGENT_V3",
                reasoning="Payment transfer routed to PaymentAgentV3 via A2A",
                tools_considered=["prepareTransfer", "executeTransfer"],
                tools_invoked=[{"tool": "payment_mcp", "status": "success"}],
                result_status="success",
                result_summary=f"Response generated ({len(full_response)} chars)",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a"}
            )

            telemetry.log_user_message(
                thread_id=thread_id,
                user_query=message,
                response_text=full_response,
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC2_PAYMENT_AGENT_V3",
                reasoning="Payment transfer routed to PaymentAgentV3 via A2A",
                tools_considered=["prepareTransfer", "executeTransfer"],
                tools_invoked=[],
                result_status="error",
                result_summary=f"Error: {str(e)}",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a", "error": str(e)}
            )
            raise

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up PaymentAgentV3Handler resources")
        self._cached_agents.clear()

        if self.project_client:
            await self.project_client.close()
            logger.info("✅ AIProjectClient closed")

        if self.credential:
            await self.credential.close()
            logger.info("✅ Azure credential closed")


# Global singleton
_handler: PaymentAgentV3Handler | None = None


async def get_payment_agent_v3_handler() -> PaymentAgentV3Handler:
    """Get or create the global PaymentAgentV3Handler instance"""
    global _handler

    if _handler is None:
        _handler = PaymentAgentV3Handler()
        await _handler.initialize()
        logger.info("PaymentAgentV3Handler singleton initialized")

    return _handler


async def cleanup_handler():
    """Cleanup the global handler"""
    global _handler

    if _handler is not None:
        await _handler.cleanup()
        _handler = None
        logger.info("PaymentAgentV3Handler singleton cleaned up")
