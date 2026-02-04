"""
Refactored Supervisor Agent with A2A Communication.

This version uses the A2A SDK to communicate with domain agent microservices
instead of direct Python method calls.
"""
from typing import Any, AsyncGenerator
from agent_framework import ChatAgent
from agent_framework.exceptions import AgentThreadException
from agent_framework.azure import AzureOpenAIChatClient
from uuid import uuid4
import logging
import sys
import os

# Add paths for A2A SDK
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from a2a_sdk.client.a2a_client import A2AClient
from a2a_sdk.client.registry_client import RegistryClient
from a2a_sdk.models.message import A2AMessage
from common.observability import get_logger, create_span, add_span_attributes

logger = get_logger(__name__)


class SupervisorAgentA2A:
    """
    Supervisor Agent with A2A communication to domain agent microservices.
    
    This refactored version:
    - Uses A2A SDK to discover and call domain agents
    - Maintains the same external API as original Supervisor
    - Adds distributed tracing and observability
    - Supports circuit breaking and retry logic
    """

    instructions = """
      You are a Supervisor Agent for BankX, routing customer requests to specialized domain agents.

      ## Your Responsibilities
      1. Classify user intent
      2. Route to appropriate agent (Account, Transaction, Payment, ProdInfoFAQ, AIMoneyCoach)
      3. Return agent's response to customer
      4. Log routing decisions for governance

      ## Context-Aware Routing
      **Requester Role**: Customer or Teller
      - SAME agents serve both roles
      - Agents adjust behavior based on requester_role context
      - Customer: Self-service operations
      - Teller: Audit dashboard, customer profile views

      ## Triage Rules

      ### Route to AccountAgent (Balance, Limits, Account Info)
      - "What's my balance?"
      - "Show my transfer limits"
      - "What are my account details?"
      - "Check my daily limit usage"

      ### Route to TransactionAgent (Transaction History, Aggregations, Insights)
      - "Show transactions for last week"
      - "How many transactions did I have?"
      - "What's my total spending in October?"
      - "Show details for transaction TXN-064"

      ### Route to PaymentAgent (Transfers, Money Movement)
      - "Transfer 1000 THB to Nattaporn"
      - "Send money to account 123-456-002"
      - "Pay 500 to Somchai"
      - "Make a transfer"

      ### Route to ProdInfoFAQAgent (Product Information, FAQs, Banking Terms)
      - "What is a Current Account?"
      - "Tell me about savings account features"
      - "What are the interest rates for time deposits?"
      - "Compare fixed account vs savings account"

      ### Route to AIMoneyCoachAgent (Personal Finance Coaching, Debt Management)
      - "How can I manage my debt?"
      - "What is good debt vs bad debt?"
      - "How to become debt-free?"
      - "I'm drowning in debt, help!"
      - "Should I consolidate my loans?"

      ## Important Notes
      1. **Single routing per request** - Route to ONE agent only
      2. **Pass complete context** - Include full user message
      3. **Return agent response as-is** - Don't modify structured outputs
      4. **Log routing decisions** - For governance and analytics
      5. **Context preservation** - Maintain conversation thread
    """
    
    name = "SupervisorAgent"
    description = "Routes customer requests to specialized domain agents via A2A communication"

    thread_store: dict[str, dict[str, Any]] = {}
    supervisor_thread_store: dict[str, dict[str, Any]] = {}

    def __init__(
        self,
        azure_chat_client: AzureOpenAIChatClient,
        agent_registry_url: str = None,
        customer_id: str = None,
        requester_role: str = "customer",
    ):
        """
        Initialize Supervisor Agent with A2A client.

        Args:
            azure_chat_client: Azure OpenAI chat client for LLM routing decisions
            agent_registry_url: URL of the agent registry service
            customer_id: Customer ID for context
            requester_role: Role of the requester (customer or teller)
        """
        self.azure_chat_client = azure_chat_client
        self.customer_id = customer_id
        self.requester_role = requester_role

        # Initialize A2A client
        registry_url = agent_registry_url or os.getenv(
            "AGENT_REGISTRY_URL", "http://localhost:9000"
        )
        self.registry_client = RegistryClient(registry_url)
        self.a2a_client = A2AClient(
            agent_id="supervisor-001",
            agent_name="SupervisorAgent",
            registry_client=self.registry_client,
        )

        logger.info(
            f"Supervisor Agent initialized with A2A client (registry: {registry_url})"
        )

    async def _build_af_agent(self) -> ChatAgent:
        """Build the Agent Framework agent with routing tools."""
        tools = [
            self.route_to_account_agent,
            self.route_to_transaction_agent,
            self.route_to_payment_agent,
            self.route_to_prodinfo_faq_agent,
            self.route_to_ai_money_coach_agent,
        ]

        return ChatAgent(
            chat_client=self.azure_chat_client,
            instructions=SupervisorAgentA2A.instructions,
            name=SupervisorAgentA2A.name,
            tools=tools,
        )

    async def route_to_account_agent(self, user_message: str) -> str:
        """Route the conversation to Account Agent via A2A."""
        with create_span(
            "supervisor_route",
            {"target_agent": "AccountAgent", "intent": "account.balance"},
        ):
            try:
                # Create A2A message
                a2a_message = A2AMessage(
                    intent="account.balance",
                    payload={
                        "customer_id": self.customer_id,
                        "user_message": self.user_message,
                        "requester_role": self.requester_role,
                    },
                )

                # Send via A2A
                response = await self.a2a_client.send_message(
                    target_capability="account.balance",
                    intent="account.balance",
                    payload=a2a_message.payload,
                )

                # Extract response
                if response.status == "success":
                    return self._format_agent_response(response.response)
                else:
                    return f"Error from Account Agent: {response.response.get('error', 'Unknown error')}"

            except Exception as e:
                logger.error(f"Failed to route to Account Agent: {e}", exc_info=True)
                return f"I apologize, but I'm having trouble connecting to the account service. Please try again."

    async def route_to_transaction_agent(self, user_message: str) -> str:
        """Route the conversation to Transaction Agent via A2A."""
        with create_span(
            "supervisor_route",
            {"target_agent": "TransactionAgent", "intent": "transaction.history"},
        ):
            try:
                a2a_message = A2AMessage(
                    intent="transaction.history",
                    payload={
                        "customer_id": self.customer_id,
                        "user_message": self.user_message,
                        "requester_role": self.requester_role,
                    },
                )

                response = await self.a2a_client.send_message(
                    target_capability="transaction.history",
                    intent="transaction.history",
                    payload=a2a_message.payload,
                )

                if response.status == "success":
                    return self._format_agent_response(response.response)
                else:
                    return f"Error from Transaction Agent: {response.response.get('error', 'Unknown error')}"

            except Exception as e:
                logger.error(f"Failed to route to Transaction Agent: {e}", exc_info=True)
                return f"I apologize, but I'm having trouble connecting to the transaction service. Please try again."

    async def route_to_payment_agent(self, user_message: str) -> str:
        """Route the conversation to Payment Agent via A2A."""
        with create_span(
            "supervisor_route",
            {"target_agent": "PaymentAgent", "intent": "payment.transfer"},
        ):
            try:
                a2a_message = A2AMessage(
                    intent="payment.transfer",
                    payload={
                        "customer_id": self.customer_id,
                        "user_message": self.user_message,
                        "requester_role": self.requester_role,
                    },
                )

                response = await self.a2a_client.send_message(
                    target_capability="payment.transfer",
                    intent="payment.transfer",
                    payload=a2a_message.payload,
                )

                if response.status == "success":
                    return self._format_agent_response(response.response)
                else:
                    return f"Error from Payment Agent: {response.response.get('error', 'Unknown error')}"

            except Exception as e:
                logger.error(f"Failed to route to Payment Agent: {e}", exc_info=True)
                return f"I apologize, but I'm having trouble connecting to the payment service. Please try again."

    async def route_to_prodinfo_faq_agent(self, user_message: str) -> str:
        """Route the conversation to ProdInfoFAQ Agent via A2A."""
        with create_span(
            "supervisor_route",
            {"target_agent": "ProdInfoFAQAgent", "intent": "product.info"},
        ):
            try:
                a2a_message = A2AMessage(
                    intent="product.info",
                    payload={
                        "customer_id": self.customer_id,
                        "query": self.user_message,
                    },
                )

                response = await self.a2a_client.send_message(
                    target_capability="product.info",
                    intent="product.info",
                    payload=a2a_message.payload,
                )

                if response.status == "success":
                    return self._format_agent_response(response.response)
                else:
                    return f"Error from ProdInfoFAQ Agent: {response.response.get('error', 'Unknown error')}"

            except Exception as e:
                logger.error(f"Failed to route to ProdInfoFAQ Agent: {e}", exc_info=True)
                return f"I apologize, but I'm having trouble connecting to the product information service. Please try again."

    async def route_to_ai_money_coach_agent(self, user_message: str) -> str:
        """Route the conversation to AIMoneyCoach Agent via A2A."""
        with create_span(
            "supervisor_route",
            {"target_agent": "AIMoneyCoachAgent", "intent": "coaching.debt_management"},
        ):
            try:
                a2a_message = A2AMessage(
                    intent="coaching.debt_management",
                    payload={
                        "customer_id": self.customer_id,
                        "context": {"user_message": self.user_message},
                    },
                )

                response = await self.a2a_client.send_message(
                    target_capability="coaching.debt_management",
                    intent="coaching.debt_management",
                    payload=a2a_message.payload,
                )

                if response.status == "success":
                    return self._format_agent_response(response.response)
                else:
                    return f"Error from AIMoneyCoach Agent: {response.response.get('error', 'Unknown error')}"

            except Exception as e:
                logger.error(f"Failed to route to AIMoneyCoach Agent: {e}", exc_info=True)
                return f"I apologize, but I'm having trouble connecting to the AI Money Coach service. Please try again."

    def _format_agent_response(self, response_payload: dict) -> str:
        """
        Format agent response payload into text.

        Args:
            response_payload: Response payload from agent

        Returns:
            Formatted text response
        """
        # For now, return JSON string representation
        # In production, format based on response type (BALANCE_CARD, TXN_TABLE, etc.)
        import json
        return json.dumps(response_payload, indent=2)

    async def processMessageStream(
        self, user_message: str, thread_id: str | None
    ) -> AsyncGenerator[tuple[str, bool, str | None], None]:
        """Process a chat message and stream the response."""
        try:
            agent = await self._build_af_agent()

            processed_thread_id = thread_id
            supervisor_resumed_thread = agent.get_new_thread()

            if processed_thread_id is None:
                self.current_thread = agent.get_new_thread()
                processed_thread_id = str(uuid4())
                SupervisorAgentA2A.thread_store[processed_thread_id] = (
                    await self.current_thread.serialize()
                )
                SupervisorAgentA2A.supervisor_thread_store[processed_thread_id] = (
                    await supervisor_resumed_thread.serialize()
                )
            else:
                serialized_thread = SupervisorAgentA2A.thread_store.get(
                    processed_thread_id, None
                )
                supervisor_serialized_thread = (
                    SupervisorAgentA2A.supervisor_thread_store.get(
                        processed_thread_id, None
                    )
                )

                if serialized_thread is None or supervisor_serialized_thread is None:
                    raise AgentThreadException(
                        f"Thread id {processed_thread_id} not found in thread stores"
                    )

                resumed_thread = agent.get_new_thread()
                await resumed_thread.update_from_thread_state(serialized_thread)
                self.current_thread = resumed_thread
                await supervisor_resumed_thread.update_from_thread_state(
                    supervisor_serialized_thread
                )

            # Save the original user message
            self.user_message = user_message

            # Stream the response
            full_response = ""

            try:
                async for chunk in agent.run_stream(
                    user_message, thread=supervisor_resumed_thread
                ):
                    if hasattr(chunk, "text") and chunk.text:
                        content = chunk.text
                        full_response += content
                        yield (content, False, None)
            except Exception as stream_error:
                logger.error(f"Error during streaming: {str(stream_error)}", exc_info=True)
                error_message = f"Streaming failed: {str(stream_error)}. Please try again."
                yield (error_message, True, processed_thread_id)
                return

            # Update thread stores
            SupervisorAgentA2A.thread_store[processed_thread_id] = (
                await self.current_thread.serialize()
            )
            SupervisorAgentA2A.supervisor_thread_store[processed_thread_id] = (
                await supervisor_resumed_thread.serialize()
            )

            yield ("", True, processed_thread_id)

        except Exception as e:
            logger.error(f"Error in processMessageStream: {str(e)}", exc_info=True)
            error_message = f"I apologize, but I encountered an error: {str(e)}"
            yield (error_message, True, thread_id)

    async def processMessage(
        self, user_message: str, thread_id: str | None
    ) -> tuple[str, str | None]:
        """Process a chat message and return response and thread id."""
        agent = await self._build_af_agent()

        processed_thread_id = thread_id
        supervisor_resumed_thread = agent.get_new_thread()

        if processed_thread_id is None:
            self.current_thread = agent.get_new_thread()
            processed_thread_id = str(uuid4())
            SupervisorAgentA2A.thread_store[processed_thread_id] = (
                await self.current_thread.serialize()
            )
            SupervisorAgentA2A.supervisor_thread_store[processed_thread_id] = (
                await supervisor_resumed_thread.serialize()
            )

        else:
            serialized_thread = SupervisorAgentA2A.thread_store.get(
                processed_thread_id, None
            )
            supervisor_serialized_thread = SupervisorAgentA2A.supervisor_thread_store.get(
                processed_thread_id, None
            )

            if serialized_thread is None or supervisor_serialized_thread is None:
                raise AgentThreadException(
                    f"Thread id {processed_thread_id} not found in thread stores"
                )

            resumed_thread = agent.get_new_thread()
            await resumed_thread.update_from_thread_state(serialized_thread)
            self.current_thread = resumed_thread

            await supervisor_resumed_thread.update_from_thread_state(
                supervisor_serialized_thread
            )

        # Save the original user message
        self.user_message = user_message

        response = await agent.run(user_message, thread=supervisor_resumed_thread)

        # Update thread stores
        SupervisorAgentA2A.thread_store[processed_thread_id] = (
            await self.current_thread.serialize()
        )
        SupervisorAgentA2A.supervisor_thread_store[processed_thread_id] = (
            await supervisor_resumed_thread.serialize()
        )

        return response.text, processed_thread_id
