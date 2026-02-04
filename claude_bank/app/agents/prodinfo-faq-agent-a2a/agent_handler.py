"""
ProdInfoFAQ Agent Handler - Azure AI Foundry with File Search

Uses agent-framework (PyPI packages) to create ProdInfoFAQAgent in Foundry with:
- Azure AI Foundry V2 (azure-ai-projects)
- Native file_search tool for product documentation (RAG)
- Escalation MCP Tool for ticket creation (optional)
- A2A protocol support for supervisor routing
"""

import logging
import httpx
from typing import AsyncGenerator

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

from config import (
    AZURE_AI_PROJECT_ENDPOINT,
    PRODINFO_FAQ_AGENT_NAME,
    PRODINFO_FAQ_AGENT_VERSION,
    PRODINFO_FAQ_AGENT_MODEL_DEPLOYMENT,
    ESCALATION_AGENT_A2A_URL,
)

logger = logging.getLogger(__name__)


def create_support_ticket_tool(handler_instance):
    """
    Create a support ticket creation tool that the agent can call
    
    This function returns a callable that the agent framework can invoke
    when the agent needs to create a ticket.
    """
    async def create_support_ticket(issue_description: str) -> str:
        """
        Create a support ticket for the customer's issue.
        
        Args:
            issue_description: Description of the customer's issue or question
            
        Returns:
            Confirmation message about ticket creation
        """
        logger.info(f"🎫 [TOOL CALLED] create_support_ticket: {issue_description[:100]}...")
        
        # Get customer info from handler instance context
        customer_id = getattr(handler_instance, '_current_customer_id', 'unknown')
        thread_id = getattr(handler_instance, '_current_thread_id', 'unknown')
        user_mail = getattr(handler_instance, '_current_user_mail', 'purohitabhinav2001@gmail.com')
        
        # Call escalation agent
        response = await handler_instance.call_escalation_agent(
            customer_id=customer_id,
            thread_id=thread_id,
            user_message=issue_description,
            user_mail=user_mail,
            customer_name="Customer"
        )
        
        return response
    
    # Set function metadata for the agent framework
    create_support_ticket.__name__ = "create_support_ticket"
    create_support_ticket.__doc__ = """Create a support ticket for the customer's issue.
    
Args:
    issue_description (str): Description of the customer's issue or question that needs specialist attention
    
Returns:
    str: Confirmation message about the ticket creation
    
Use this tool when:
- Customer asks a product question that is not in your knowledge base
- Customer confirms they want to create a ticket (says "yes", "confirm", etc.)
- You need to escalate an issue to a product specialist
"""
    
    return create_support_ticket


class ProdInfoFAQAgentHandler:
    """
    ProdInfoFAQ Agent Handler using Agent Framework with Azure AI Foundry
    
    Architecture:
    - Agent created in Azure AI Foundry with file_search tool enabled
    - Product documents uploaded to agent's vector store in Foundry portal
    - Calls Escalation Agent via A2A for ticket creation (port 9006)
    - No custom RAG MCP - uses native Foundry file_search
    - A2A protocol enables supervisor routing
    """

    def __init__(self):
        self.credential = None
        self.instructions: str = ""
        
        # Agent caching (per thread)
        self._cached_agents: dict[str, ChatAgent] = {}
        
        # Cache for Azure AI clients (keyed by thread_id) - needed for thread message extraction
        self._cached_clients: dict[str, AzureAIAgentClient] = {}
        
        # AIProjectClient for listing thread messages
        self._project_client: AIProjectClient | None = None
        
        # Context storage for tool execution
        self._current_customer_id = None
        self._current_thread_id = None
        self._current_user_mail = None
        
        logger.info("ProdInfoFAQAgentHandler initialized (Agent Framework + Foundry V2)")

    async def initialize(self):
        """Initialize Azure AI resources"""
        self.credential = AzureCliCredential()
        
        # Create AIProjectClient for listing thread messages
        self._project_client = AIProjectClient(
            endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=self.credential
        )
        
        # Get OpenAI-compatible client for thread message operations
        self._openai_client = self._project_client.get_openai_client()

        # Load agent instructions from markdown file
        with open("prompts/prodinfo_faq_agent.md", "r", encoding="utf-8") as f:
            self.instructions = f.read()
        
        logger.info("✅ Handler initialized (Azure credential + instructions loaded)")

    async def call_escalation_agent(self, customer_id: str, thread_id: str, user_message: str, user_mail: str = "purohitabhinav2001@gmail.com", customer_name: str = "Customer") -> str:
        """Call Escalation Agent via A2A to create ticket"""
        if not ESCALATION_AGENT_A2A_URL:
            logger.warning("⚠️  Escalation Agent URL not configured - ticket creation disabled")
            return "I apologize, but ticket creation is currently unavailable. Please contact support directly."
        
        logger.info(f"📞 Calling Escalation Agent via A2A for customer={customer_id}")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{ESCALATION_AGENT_A2A_URL}/a2a/invoke",
                    json={
                        "messages": [
                            {"role": "user", "content": f"Create a support ticket for this issue: {user_message}. Customer email: {user_mail}, Customer name: {customer_name}"}
                        ],
                        "customer_id": customer_id,
                        "thread_id": thread_id,
                        "stream": False
                    }
                )
                response.raise_for_status()
                result = response.json()
                logger.info(f"✅ Escalation Agent response received")
                return result.get("content", "Ticket creation request processed.")
        except Exception as e:
            logger.error(f"❌ Error calling Escalation Agent: {e}")
            return f"I apologize, but there was an error creating your support ticket. Please contact support directly at {user_mail}."

    async def get_agent(
        self,
        thread_id: str,
        customer_id: str | None = None,
        user_mail: str | None = None,
        current_date_time: str | None = None,
    ) -> ChatAgent:
        """
        Get or create ProdInfoFAQAgent with file_search tool (from Foundry)
        
        Agent is created in Azure AI Foundry with:
        - file_search tool enabled in portal
        - Product docs uploaded to vector store
        - create_support_ticket tool for escalations
        """
        
        # Check cache first
        if thread_id in self._cached_agents:
            logger.info(f"♻️  Using cached ProdInfoFAQAgent for thread={thread_id}")
            # Update context for cached agent
            self._current_customer_id = customer_id or "unknown"
            self._current_thread_id = thread_id
            self._current_user_mail = user_mail or "purohitabhinav2001@gmail.com"
            return self._cached_agents[thread_id]
        
        logger.info(f"🔨 Building new ProdInfoFAQAgent for thread={thread_id}, customer={customer_id}")
        
        # Store context for tool execution
        self._current_customer_id = customer_id or "unknown"
        self._current_thread_id = thread_id
        self._current_user_mail = user_mail or "purohitabhinav2001@gmail.com"
        
        # Prepare context-aware instructions
        instructions = self.instructions
        if user_mail:
            instructions = instructions.replace("{user_mail}", user_mail)
        if current_date_time:
            instructions = instructions.replace("{current_date_time}", current_date_time)
        
        # Create Azure AI Agent Client
        # NOTE: The agent MUST already exist in Azure AI Foundry with:
        #       - Name: ProdInfoFAQAgent, Version: 3
        #       - file_search tool enabled
        #       - Product documents uploaded to vector store
        azure_client = AzureAIAgentClient(
            project_endpoint=AZURE_AI_PROJECT_ENDPOINT,
            credential=self.credential,
            agent_name=PRODINFO_FAQ_AGENT_NAME,
            agent_version=PRODINFO_FAQ_AGENT_VERSION,
            model_deployment_name=PRODINFO_FAQ_AGENT_MODEL_DEPLOYMENT,
        )
        logger.info(f"✅ AzureAIAgentClient created - Agent: {PRODINFO_FAQ_AGENT_NAME} v{PRODINFO_FAQ_AGENT_VERSION}")
        
        # Create the ticket creation tool
        ticket_tool = create_support_ticket_tool(self)
        logger.info(f"🎫 Created create_support_ticket tool")
        
        # Create ChatAgent with ticket creation tool
        # Note: file_search tool is automatically included from Foundry agent definition
        agent = ChatAgent(
            name="ProdInfoFAQAgent",
            chat_client=azure_client,
            instructions=instructions,
            tools=[ticket_tool],  # Custom Python function for ticket creation
        )
        
        logger.info(f"💾 Cached ProdInfoFAQAgent for thread={thread_id} with ticket creation tool")
        self._cached_agents[thread_id] = agent
        self._cached_clients[thread_id] = azure_client  # Store client for thread message extraction
        
        return agent

    async def process_message(
        self,
        message: str,
        thread_id: str,
        customer_id: str | None = None,
        user_mail: str | None = None,
        current_date_time: str | None = None,
        stream: bool = True,
        messages_history: list[dict] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Process a message using ProdInfoFAQAgent
        
        Args:
            message: User's message
            thread_id: Thread identifier
            customer_id: Customer identifier
            user_mail: User's email address
            current_date_time: Current date/time string
            stream: Whether to stream the response
            messages_history: Full conversation history from A2A protocol
        """
        logger.info(f"📨 Processing message for thread={thread_id}: {message[:50]}...")
        logger.info(f"[DEBUG] Full message received: '{message}'")
        logger.info(f"[DEBUG] Thread ID: {thread_id}")
        logger.info(f"[DEBUG] Customer ID: {customer_id}")
        
        # Get agent (will create if needed, or use cached)
        agent = await self.get_agent(
            thread_id=thread_id,
            customer_id=customer_id,
            user_mail=user_mail,
            current_date_time=current_date_time,
        )
        logger.info(f"[DEBUG] Agent retrieved/created successfully")
        
        # Check if this is a confirmation message
        confirmation_keywords = ["yes", "confirm", "create ticket", "please", "ok", "sure"]
        is_confirmation = any(keyword in message.lower() for keyword in confirmation_keywords)
        logger.info(f"[DEBUG] Is confirmation check: {is_confirmation}")
        logger.info(f"[DEBUG] Message lowercase: '{message.lower()}'")
        logger.info(f"[DEBUG] Thread in cache: {thread_id in self._cached_agents}")
        
        processed_message = message
        if is_confirmation and thread_id in self._cached_agents:
            logger.info("🎫 Confirmation detected - extracting original question from message history")
            logger.info(f"[DEBUG] Starting message history extraction...")
            print("\n" + "="*80)
            print(f"[HANDLER DEBUG] 🎫 Confirmation detected - extracting original question")
            print(f"[HANDLER DEBUG] Thread ID: {thread_id}")
            print(f"[HANDLER DEBUG] Thread in cache: {thread_id in self._cached_agents}")
            print(f"[HANDLER DEBUG] messages_history provided: {messages_history is not None}")
            print(f"[HANDLER DEBUG] messages_history length: {len(messages_history) if messages_history else 0}")
            print("="*80 + "\n")
            try:
                # Extract original question from messages_history (A2A protocol provides full conversation)
                if not messages_history or len(messages_history) == 0:
                    logger.warning(f"[DEBUG] No message history provided")
                    print(f"[HANDLER DEBUG] ❌ ERROR: No message history provided!")
                    raise Exception("Message history not available")
                
                logger.info(f"[DEBUG] Found {len(messages_history)} messages in history")
                print(f"[HANDLER DEBUG] ✅ Found {len(messages_history)} messages in history")
                
                # Find the most recent user question (searching backwards from most recent)
                # This should be the question that triggered the ticket offer
                original_question = None
                print(f"[HANDLER DEBUG] Searching BACKWARDS through messages for most recent question...")
                print(f"[HANDLER DEBUG] Confirmation keywords: {confirmation_keywords}")
                
                # Iterate backwards through message history (most recent first)
                for idx in range(len(messages_history) - 1, -1, -1):
                    msg_dict = messages_history[idx]
                    role = msg_dict.get("role", "")
                    content = msg_dict.get("content", "")
                    logger.info(f"[DEBUG] Message {idx}: role={role}")
                    print(f"[HANDLER DEBUG] Checking message {idx} (reverse order):")
                    print(f"[HANDLER DEBUG]   Role: {role}")
                    print(f"[HANDLER DEBUG]   Content: '{content}'")
                    if role == "user":
                        msg_text = content
                        logger.info(f"[DEBUG]   User message text: '{msg_text[:100]}...'")
                        # Skip if it's a confirmation message
                        is_conf = any(kw in msg_text.lower() for kw in confirmation_keywords)
                        logger.info(f"[DEBUG]   Is confirmation: {is_conf}")
                        logger.info(f"[DEBUG]   Message length: {len(msg_text)}")
                        print(f"[HANDLER DEBUG]   Is confirmation: {is_conf}")
                        print(f"[HANDLER DEBUG]   Message length: {len(msg_text)}")
                        if not is_conf and len(msg_text) > 10:
                            original_question = msg_text
                            logger.info(f"✅ Found original question: {original_question[:100]}...")
                            logger.info(f"[DEBUG] ORIGINAL QUESTION EXTRACTED: '{original_question}'")
                            print(f"[HANDLER DEBUG] ✅✅✅ FOUND ORIGINAL QUESTION (most recent): '{original_question}'")
                            break
                        else:
                            print(f"[HANDLER DEBUG]   ⏭️  Skipped (is_conf={is_conf}, len={len(msg_text)})")
                    else:
                        logger.info(f"[DEBUG]   Skipping non-user message (role={role})")
                        print(f"[HANDLER DEBUG]   ⏭️  Skipped (role={role})")
                
                if original_question:
                    # Prepend context to the confirmation message
                    processed_message = f"User confirmed ticket creation. Original question was: '{original_question}'. Create ticket with this issue description: {original_question}"
                    logger.info(f"📝 Enhanced message with context: {processed_message[:150]}...")
                    logger.info(f"[DEBUG] PROCESSED MESSAGE (FULL): '{processed_message}'")
                    print(f"\n[HANDLER DEBUG] ✅✅✅ SUCCESS! Extracted original question")
                    print(f"[HANDLER DEBUG] Original question: '{original_question}'")
                    print(f"[HANDLER DEBUG] Enhanced message: '{processed_message[:150]}...'\n")
                else:
                    logger.warning(f"[DEBUG] No original question found in message history!")
                    print(f"\n[HANDLER DEBUG] ❌ ERROR: No original question found in {len(messages_history)} messages!\n")
            except Exception as e:
                logger.warning(f"⚠️  Could not extract original question: {e}")
                logger.exception(f"[DEBUG] Full exception details:")
                logger.info("Proceeding with original message")
                print(f"\n[HANDLER DEBUG] ❌ EXCEPTION: {e}\n")
        else:
            logger.info(f"[DEBUG] Not a confirmation or agent not cached - using original message")
        
        # Store processed message for tool access
        self._processed_message = processed_message
        logger.info(f"[DEBUG] Final processed_message stored: '{processed_message[:100]}...'")
        
        # # Process message with streaming support
        # logger.info(f"[DEBUG] About to call agent with message: '{processed_message[:100]}...'")
        # logger.info(f"[DEBUG] Stream mode: {stream}")
        # if stream:
        #     # Use run_stream for streaming responses
        #     logger.info(f"[DEBUG] Starting agent.run_stream()...")
        #     async for chunk in agent.run_stream(processed_message):
        #         if hasattr(chunk, 'text') and chunk.text:
        #             logger.info(f"[DEBUG] Stream chunk received: {chunk.text[:50]}...")
        #             yield chunk.text
        #     logger.info(f"[DEBUG] Streaming complete")
        # else:
        #     # Use run for non-streaming (returns AgentRunResponse)
        #     logger.info(f"[DEBUG] Starting agent.run()...")
        #     result = await agent.run(processed_message)
        #     logger.info(f"[DEBUG] Agent run complete, result: {result.text[:100]}...")
        #     yield result.text


        # Track response metrics
        import time
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "common"))
        from a2a_banking_telemetry import get_a2a_telemetry
        telemetry = get_a2a_telemetry("ProdInfoFAQAgent")
        start_time = time.time()
        full_response = ""
        
        try:
            # Process message with streaming support
            logger.info(f"[DEBUG] About to call agent with message: '{processed_message[:100]}...'")
            logger.info(f"[DEBUG] Stream mode: {stream}")
            if stream:
                # Use run_stream for streaming responses
                logger.info(f"[DEBUG] Starting agent.run_stream()...")
                async for chunk in agent.run_stream(processed_message):
                    if hasattr(chunk, 'text') and chunk.text:
                        full_response += chunk.text
                        logger.info(f"[DEBUG] Stream chunk received: {chunk.text[:50]}...")
                        yield chunk.text
                logger.info(f"[DEBUG] Streaming complete")
            else:
                # Use run for non-streaming (returns AgentRunResponse)
                logger.info(f"[DEBUG] Starting agent.run()...")
                result = await agent.run(processed_message)
                full_response = result.text
                logger.info(f"[DEBUG] Agent run complete, result: {result.text[:100]}...")
                yield result.text
            
            # Log successful execution
            duration = time.time() - start_time
            telemetry.log_agent_decision(
                thread_id=thread_id,
                user_query=message,
                triage_rule="UC5_PRODINFO_FAQ_AGENT",
                reasoning="Product info/FAQ query routed to ProdInfoFAQAgent via A2A",
                tools_considered=["searchProductFAQs", "createTicket"],
                tools_invoked=[{"tool": "prodinfo_mcp", "status": "success"}],
                result_status="success",
                result_summary=f"Response generated ({len(full_response)} chars)",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a", "is_confirmation": is_confirmation}
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
                triage_rule="UC5_PRODINFO_FAQ_AGENT",
                reasoning="Product info/FAQ query routed to ProdInfoFAQAgent via A2A",
                tools_considered=["searchProductFAQs", "createTicket"],
                tools_invoked=[],
                result_status="error",
                result_summary=f"Error: {str(e)}",
                duration_seconds=duration,
                context={"customer_id": customer_id, "mode": "a2a", "error": str(e)}
            )
            raise


    async def clear_cache(self, thread_id: str | None = None):
        """Clear agent cache for a specific thread or all threads"""
        if thread_id:
            if thread_id in self._cached_agents:
                del self._cached_agents[thread_id]
                logger.info(f"🗑️  Cleared cache for thread={thread_id}")
        else:
            self._cached_agents.clear()
            logger.info("🗑️  Cleared all cached agents")
