"""
Account Agent Handler - Azure AI Foundry with Agent Framework

Uses agent-framework (PyPI packages) to create AccountAgent in Foundry with:
- Azure AI Foundry V2 (azure-ai-projects)
- MCP Tools for account and limits data (with audit logging)
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
    ACCOUNT_AGENT_NAME,
    ACCOUNT_AGENT_VERSION,
    ACCOUNT_AGENT_MODEL_DEPLOYMENT,  # Add model deployment
    ACCOUNT_MCP_SERVER_URL,
    LIMITS_MCP_SERVER_URL,
    ACCOUNT_AGENT_CONFIG,
)

logger = logging.getLogger(__name__)


class AccountAgentHandler:
    """
    Account Agent Handler using Agent Framework with Azure AI Foundry
    
    Pattern based on: agent-framework-1/python/samples/getting_started/agents/a2a/
    
    Architecture:
    - Agent created in Azure AI Foundry (cloud service)
    - Agent Framework provides Python SDK wrapper
    - MCP tools connect to business logic microservices
    - A2A protocol enables supervisor routing
    """

    def __init__(self):
        self.credential = None
        self.instructions: str = ""
        self.project_client = None
        
        # Agent caching (per thread)
        self._cached_agents: dict[str, ChatAgent] = {}
        
        # MCP tool caching (shared across threads for performance)
        self._mcp_tools_cache: list | None = None
        
        logger.info("AccountAgentHandler initialized (Agent Framework + Foundry V2)")

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
        with open("prompts/account_agent.md", "r", encoding="utf-8") as f:
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

        # Limits MCP Tool (with audit logging)
        limits_mcp_tool = AuditedMCPTool(
            name="Limits MCP Server",
            url=LIMITS_MCP_SERVER_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="limits",
            headers={},
            description="Check transaction limits and daily limits for customers",
        )
        await limits_mcp_tool.connect()
        
        logger.info("✅ MCP connections established (Account + Limits) with audit logging")

        return [account_mcp_tool, limits_mcp_tool]

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
            logger.info(f"⚡ [CACHE HIT] Reusing cached AccountAgent for thread={thread_id}")
            return self._cached_agents[thread_id]

        logger.info(f"Building new AccountAgent for thread={thread_id}, customer={customer_id}")

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
        # This does NOT create a new agent - it references the agent created by create_agent_in_foundry.py
        azure_client = AzureAIClient(
            project_client=self.project_client,
            agent_name=ACCOUNT_AGENT_NAME,
            agent_version=ACCOUNT_AGENT_VERSION,
        )
        logger.info(f"✅ AzureAIClient created - Referencing existing agent: {ACCOUNT_AGENT_NAME}:{ACCOUNT_AGENT_VERSION}")

        # Create ChatAgent with MCP tools added dynamically
        # The Foundry agent has NO tools - we add them here to avoid duplication
        chat_agent = azure_client.create_agent(
            name=ACCOUNT_AGENT_NAME,
            tools=mcp_tools,
            instructions=full_instructions,
        )
        
        # Note: Azure creates thread on first message - thread ID available after first run

        # Cache the agent using the local thread_id for lookup
        # Note: We use local thread_id as cache key, but agent uses Azure's thread internally
        self._cached_agents[thread_id] = chat_agent
        logger.info(f"💾 [CACHE STORED] AccountAgent cached for thread={thread_id}")

        return chat_agent

    async def process_message(
        self, 
        message: str, 
        thread_id: str, 
        customer_id: str,
        stream: bool = True
    ) -> AsyncGenerator[str, None]:
        """
        Process a message using the AccountAgent
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
        telemetry = get_a2a_telemetry("AccountAgent")
        
        # Get or create agent for this thread
        agent = await self.get_agent(thread_id=thread_id, customer_id=customer_id)

        # Process message with streaming
        # if stream:
        #     async for chunk in agent.run_stream(message):
        #         if hasattr(chunk, 'text') and chunk.text:
        #             yield chunk.text
        # else:
        #     result = await agent.run(message)
        #     yield result.text

        # Collect response for logging
        full_response = ""
        
        try:
            # Process message with streaming
            if stream:
                async for chunk in agent.run_stream(message):
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        yield chunk.text
            else:
                result = await agent.run(message)
                full_response = result.text
                yield result.text
            
            # Log successful decision
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC1_ACCOUNT_AGENT",
                reasoning="Account query routed to AccountAgent via A2A",
                tools_considered=["getAccountsByUserName", "getAccountDetails"],
                tools_invoked=[{"tool": "account_mcp", "status": "success"}],
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
            # Log failed decision
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC1_ACCOUNT_AGENT",
                reasoning="Account query routed to AccountAgent via A2A",
                tools_considered=["getAccountsByUserName", "getAccountDetails"],
                tools_invoked=[],
                result_status="error",
                result_summary=f"Error: {str(e)}",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a", "error": str(e)}
            )
            raise


    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up AccountAgentHandler resources")
        
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
_handler: AccountAgentHandler | None = None


async def get_account_agent_handler() -> AccountAgentHandler:
    """Get or create the global AccountAgentHandler instance"""
    global _handler
    
    if _handler is None:
        _handler = AccountAgentHandler()
        await _handler.initialize()
        logger.info("AccountAgentHandler singleton initialized")
    
    return _handler


async def cleanup_handler():
    """Cleanup the global handler"""
    global _handler
    
    if _handler is not None:
        await _handler.cleanup()
        _handler = None
        logger.info("AccountAgentHandler singleton cleaned up")
