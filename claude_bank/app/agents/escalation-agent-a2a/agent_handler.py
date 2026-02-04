"""
Escalation Agent Handler for A2A Communication

Handles ticket management through Azure AI Foundry agent with Escalation MCP tools.
"""

import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator, Optional

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential

from config import (
    AZURE_AI_PROJECT_ENDPOINT,
    ESCALATION_AGENT_NAME,
    ESCALATION_AGENT_VERSION,
    ESCALATION_AGENT_MODEL_DEPLOYMENT,
    ESCALATION_COMMS_MCP_SERVER_URL,
    LOG_LEVEL,
)
from audited_mcp_tool import AuditedMCPTool

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# Reduce Azure SDK logging verbosity
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)


class EscalationAgentHandler:
    """Handler for Escalation Agent with MCP tools integration"""

    def __init__(self):
        self._cached_agents: dict[str, ChatAgent] = {}

    async def _create_escalation_tools(self, customer_id: str, thread_id: str):
        """Create Escalation MCP tools for ticket management"""
        if not ESCALATION_COMMS_MCP_SERVER_URL:
            logger.warning("Escalation MCP URL not configured")
            return []

        try:
            # Escalation MCP provides: create_ticket, get_tickets, get_ticket_details, update_ticket, close_ticket
            escalation_tool = AuditedMCPTool(
                name="Escalation MCP Server",
                url=ESCALATION_COMMS_MCP_SERVER_URL,
                customer_id=customer_id,
                thread_id=thread_id,
                mcp_server_name="escalation",
                headers={},
                description="Manage customer support tickets including creation, viewing, updating, and closing tickets",
            )
            await escalation_tool.connect()

            logger.info(f"Created Escalation MCP tool for customer {customer_id}")
            return [escalation_tool]

        except Exception as e:
            logger.error(f"Failed to create Escalation MCP tool: {e}")
            return []

    async def get_agent(
        self,
        thread_id: str,
        customer_id: str,
        current_date_time: str,
    ) -> ChatAgent:
        """
        Get or create Escalation Agent with MCP tools

        Args:
            thread_id: Conversation thread ID
            customer_id: Customer identifier
            current_date_time: Current timestamp

        Returns:
            ChatAgent: Configured agent instance
        """
        # Check cache first (agent is cached per thread for performance)
        if thread_id in self._cached_agents:
            logger.debug(f"Returning cached agent for thread {thread_id}")
            return self._cached_agents[thread_id]

        logger.info(f"Creating new EscalationAgent for thread {thread_id}")

        try:
            # Load instructions
            instructions_path = "prompts/escalation_agent.md"
            try:
                with open(instructions_path, "r", encoding="utf-8") as f:
                    instructions = f.read()
            except Exception as e:
                logger.warning(f"Could not load instructions from {instructions_path}: {e}")
                instructions = "You are an Escalation Agent for BankX. Help customers manage support tickets."

            # Inject customer_id and current_date_time into instructions
            instructions = f"{instructions}\n\n## CURRENT CONTEXT\n\n**Customer ID**: {customer_id}\n**Current Date/Time**: {current_date_time}\n\n⚠️ **USE THE CUSTOMER ID ABOVE** - This is the customer you are helping. Pass this exact value to MCP tools."

            # Create MCP tools
            mcp_tools = await self._create_escalation_tools(customer_id, thread_id)

            # Create Azure AI Agent Client (load from Foundry like UC2/UC3 pattern)
            # This provides better thread management and governance
            credential = AzureCliCredential()
            
            azure_client = AzureAIAgentClient(
                project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
                credential=credential,
                agent_name=ESCALATION_AGENT_NAME,       # Load from Foundry
                agent_version=ESCALATION_AGENT_VERSION,  # Load from Foundry
                model_deployment_name=ESCALATION_AGENT_MODEL_DEPLOYMENT,
            )

            # Create ChatAgent with Foundry agent + local MCP tools
            # Note: Instructions from Foundry agent, MCP tools added locally
            agent = ChatAgent(
                name="EscalationAgent",
                chat_client=azure_client,
                instructions=instructions,  # Override Foundry instructions with context
                tools=mcp_tools,
            )

            logger.info(f"✅ Created Foundry EscalationAgent v{ESCALATION_AGENT_VERSION} with {len(mcp_tools)} MCP tools")

            # Cache the agent
            self._cached_agents[thread_id] = agent

            return agent

        except Exception as e:
            logger.error(f"Failed to create EscalationAgent: {e}")
            raise

    async def process_message(
        self,
        messages: list,
        thread_id: str,
        customer_id: str,
        stream: bool = False,
    ) -> AsyncIterator[str]:
        """
        Process messages and return agent response

        Args:
            messages: List of conversation messages [{"role": "user", "content": "..."}]
            thread_id: Conversation thread ID
            customer_id: Customer identifier
            stream: Whether to stream the response

        Returns:
            AsyncIterator[str]: Response generator (streaming or single chunk)
        """
        current_date_time = datetime.now().isoformat()

        try:
            # Debug logging
            logger.info(f"📥 Received {len(messages)} message(s) for thread {thread_id}")
            for i, msg in enumerate(messages):
                if hasattr(msg, 'role'):
                    logger.info(f"  Message {i+1}: role={msg.role}, content={msg.content[:80]}...")
                else:
                    logger.info(f"  Message {i+1}: {msg}")
            
            # Get agent
            agent = await self.get_agent(
                thread_id=thread_id,
                customer_id=customer_id,
                current_date_time=current_date_time,
            )

            # Convert messages to format expected by agent.run()
            # For multi-turn conversations, combine into context
            if len(messages) == 1:
                # Single message
                msg = messages[0]
                user_input = msg.content if hasattr(msg, 'content') else msg.get("content", "")
                logger.info(f"📤 Single message input: {user_input[:100]}...")
            else:
                # Multi-turn: format as conversation history + current message
                conversation = []
                for msg in messages:
                    # Handle both ChatMessage objects and dicts
                    if hasattr(msg, 'role'):
                        role = msg.role
                        content = msg.content
                    else:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                    
                    if role == "user":
                        conversation.append(f"User: {content}")
                    elif role == "assistant":
                        conversation.append(f"Assistant: {content}")
                
                # Combine into single context string with clear history
                user_input = "\n\n".join(conversation)
                logger.info(f"📤 Multi-turn conversation ({len(messages)} messages):")
                logger.info(f"   Combined input: {user_input[:200]}...")

            # if stream:
            #     # Streaming response
            #     async def response_generator():
            #         async for chunk in agent.run_stream(user_input):
            #             if hasattr(chunk, 'text') and chunk.text:
            #                 yield chunk.text

            #     return response_generator()
            # else:
            #     # Non-streaming response
            #     async def response_generator():
            #         result = await agent.run(user_input)
            #         yield result.text
                    
            #     return response_generator()


            # Track response metrics
            import time
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
            from a2a_banking_telemetry import get_a2a_telemetry
            telemetry = get_a2a_telemetry("EscalationAgent")
            start_time = time.time()
            full_response = ""
            
            try:
                if stream:
                    # Streaming response
                    async def response_generator():
                        nonlocal full_response
                        async for chunk in agent.run_stream(user_input):
                            if hasattr(chunk, 'text') and chunk.text:
                                full_response += chunk.text
                                yield chunk.text
                        
                        # Log after streaming complete
                        duration = time.time() - start_time
                        telemetry.log_agent_decision(
                            thread_id=thread_id,
                            user_query=user_input,
                            triage_rule="UC6_ESCALATION_AGENT",
                            reasoning="Escalation query routed to EscalationAgent via A2A",
                            tools_considered=["createTicket", "notifyHumanAgent"],
                            tools_invoked=[{"tool": "escalation_mcp", "status": "success"}],
                            result_status="success",
                            result_summary=f"Response generated ({len(full_response)} chars)",
                            duration_seconds=duration,
                            context={"customer_id": customer_id, "mode": "a2a"}
                        )
                        telemetry.log_user_message(
                            thread_id=thread_id,
                            user_query=user_input,
                            response_text=full_response,
                            duration_seconds=duration
                        )

                    return response_generator()
                else:
                    # Non-streaming response
                    async def response_generator():
                        nonlocal full_response
                        result = await agent.run(user_input)
                        full_response = result.text
                        yield result.text
                        
                        # Log after run complete
                        duration = time.time() - start_time
                        telemetry.log_agent_decision(
                            thread_id=thread_id,
                            user_query=user_input,
                            triage_rule="UC6_ESCALATION_AGENT",
                            reasoning="Escalation query routed to EscalationAgent via A2A",
                            tools_considered=["createTicket", "notifyHumanAgent"],
                            tools_invoked=[{"tool": "escalation_mcp", "status": "success"}],
                            result_status="success",
                            result_summary=f"Response generated ({len(full_response)} chars)",
                            duration_seconds=duration,
                            context={"customer_id": customer_id, "mode": "a2a"}
                        )
                        telemetry.log_user_message(
                            thread_id=thread_id,
                            user_query=user_input,
                            response_text=full_response,
                            duration_seconds=duration
                        )
                    
                    return response_generator()
                    
            except Exception as agent_error:
                # Log error case
                duration = time.time() - start_time
                logger.error(f"❌ Error during agent execution: {str(agent_error)}")
                telemetry.log_agent_decision(
                    thread_id=thread_id,
                    user_query=user_input,
                    triage_rule="UC6_ESCALATION_AGENT",
                    reasoning="Escalation query routed to EscalationAgent via A2A",
                    tools_considered=["createTicket", "notifyHumanAgent"],
                    tools_invoked=[],
                    result_status="error",
                    result_summary=f"Error: {str(agent_error)}",
                    duration_seconds=duration,
                    context={"customer_id": customer_id, "mode": "a2a", "error": str(agent_error)}
                )
                raise


        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_msg = f"I apologize, but I encountered an error processing your request: {str(e)}"
            
            async def error_generator():
                yield error_msg
            return error_generator()
