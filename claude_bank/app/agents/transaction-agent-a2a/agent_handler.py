"""
TransactionAgent Handler - Manages agent lifecycle and MCP connections
"""

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential

from audited_mcp_tool import AuditedMCPTool
from config import (
    AZURE_AI_PROJECT_ENDPOINT,
    TRANSACTION_AGENT_NAME,
    TRANSACTION_AGENT_VERSION,
    TRANSACTION_AGENT_MODEL_DEPLOYMENT,
    ACCOUNT_MCP_SERVER_URL,
    TRANSACTION_MCP_SERVER_URL,
)

logger = logging.getLogger(__name__)


class TransactionAgentHandler:
    """Handles TransactionAgent lifecycle with Azure AI Foundry and MCP tools"""
    
    def __init__(self):
        self.credential = AzureCliCredential()
        self._cached_agents = {}  # Cache agents per thread_id
        self._mcp_tools_cache: list | None = None  # Cache MCP tools for performance
    
    async def _create_mcp_tools(self, customer_id: str, thread_id: str):
        """Create MCP tool connections with audit logging"""
        logger.info("Creating MCP connections...")
        
        # Account MCP (port 8070)
        account_mcp_tool = AuditedMCPTool(
            name="Account MCP server client",
            url=ACCOUNT_MCP_SERVER_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="account"
        )
        await account_mcp_tool.connect()
        logger.info(f"✅ Connected to Account MCP: {ACCOUNT_MCP_SERVER_URL}")
        
        # Transaction MCP (port 8071)
        transaction_mcp_tool = AuditedMCPTool(
            name="Transaction MCP server client",
            url=TRANSACTION_MCP_SERVER_URL,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="transaction"
        )
        await transaction_mcp_tool.connect()
        logger.info(f"✅ Connected to Transaction MCP: {TRANSACTION_MCP_SERVER_URL}")
        
        return [account_mcp_tool, transaction_mcp_tool]
    
    async def get_agent(self, thread_id: str, customer_id: str) -> ChatAgent:
        """Get or create TransactionAgent for this thread with MCP tools"""
        
        # Check cache first
        if thread_id in self._cached_agents:
            logger.info(f"💾 Using cached TransactionAgent for thread={thread_id}")
            return self._cached_agents[thread_id]
        
        logger.info(f"🔨 Building new TransactionAgent for thread={thread_id}, customer={customer_id}")
        
        # Load instructions from markdown file
        instructions_file = Path(__file__).parent / "prompts" / "transaction_agent.md"
        if instructions_file.exists():
            with open(instructions_file, "r", encoding="utf-8") as f:
                instructions_template = f.read()
        else:
            instructions_template = "You are TransactionAgent, a banking assistant specializing in transaction history."
        
        # Add user context (user_mail and timestamp would be added here if needed)
        full_instructions = instructions_template.format(
            user_mail=f"{customer_id}@example.com",  # Placeholder
            current_date_time="Current session"
        )
        
        # Reuse MCP tools if already created, otherwise create them once
        if self._mcp_tools_cache is None:
            logger.info("🔧 [MCP INIT] Creating MCP connections (first time)...")
            self._mcp_tools_cache = await self._create_mcp_tools(customer_id, thread_id)
            logger.info("✅ [MCP INIT] MCP connections created and cached")
        else:
            logger.info("⚡ [MCP CACHE] Reusing existing MCP connections")
        
        mcp_tools = self._mcp_tools_cache
        
        # Create Azure AI client
        azure_client = AzureAIAgentClient(
            project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=self.credential,
            agent_name=TRANSACTION_AGENT_NAME,
            agent_version=TRANSACTION_AGENT_VERSION,
            model_deployment_name=TRANSACTION_AGENT_MODEL_DEPLOYMENT,
        )
        
        # Create ChatAgent
        chat_agent = ChatAgent(
            name="TransactionAgent",
            chat_client=azure_client,
            instructions=full_instructions,
            tools=mcp_tools,
        )
        
        # Cache for future use
        self._cached_agents[thread_id] = chat_agent
        logger.info(f"💾 Cached TransactionAgent for thread={thread_id}")
        
        return chat_agent
    
    async def process_message(
        self,
        message: str,
        thread_id: str,
        customer_id: str,
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Process a message and stream back the response"""
        import time
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
        from a2a_banking_telemetry import get_a2a_telemetry
        
        # Initialize telemetry
        telemetry = get_a2a_telemetry("TransactionAgent")
        logger.info(f"📨 Processing message for thread={thread_id}: {message[:100]}...")
        
        # Get agent for this thread
        agent = await self.get_agent(thread_id, customer_id)
        
        # # Run agent with streaming
        # if stream:
        #     async for chunk in agent.run_stream(message):
        #         if hasattr(chunk, 'text') and chunk.text:
        #             yield chunk.text
        # else:
        #     result = await agent.run(message)
        #     yield result.text


        # Track response metrics
        start_time = time.time()
        full_response = ""
        
        try:
            # Run agent with streaming
            if stream:
                async for chunk in agent.run_stream(message):
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        yield chunk.text
            else:
                result = await agent.run(message)
                full_response = result.text
                yield result.text
            
            # Log successful execution
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC2_TRANSACTION_AGENT",
                reasoning="Transaction query routed to TransactionAgent via A2A",
                tools_considered=["getTransactionsByAccountId", "getTransactionDetails"],
                tools_invoked=[{"tool": "transaction_mcp", "status": "success"}],
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
                triage_rule="UC2_TRANSACTION_AGENT",
                reasoning="Transaction query routed to TransactionAgent via A2A",
                tools_considered=["getTransactionsByAccountId", "getTransactionDetails"],
                tools_invoked=[],
                result_status="error",
                result_summary=f"Error: {str(e)}",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a", "error": str(e)}
            )
            raise


    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Cleaning up TransactionAgent resources...")
        # Close credential
        await self.credential.close()
        logger.info("✅ Cleanup complete")


# Singleton instance
_handler_instance = None


async def get_transaction_agent_handler() -> TransactionAgentHandler:
    """Get singleton handler instance"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = TransactionAgentHandler()
    return _handler_instance


async def cleanup_handler():
    """Cleanup handler instance"""
    global _handler_instance
    if _handler_instance:
        await _handler_instance.cleanup()
        _handler_instance = None
