"""
Supervisor Agent with A2A Integration (Phase 1)

NEW implementation that routes to specialist agents via A2A protocol
Phase 1: AccountAgent via A2A, others via old in-process (for safe migration)

HYBRID ROUTING:
- Primary: Fast keyword-based classification (~instant)
- Fallback: LLM-based classification for uncertain queries (~1-2s)
"""

import logging
import httpx
import json
from typing import AsyncGenerator
from openai import AsyncAzureOpenAI
from app.config.settings import settings

logger = logging.getLogger(__name__)


class SupervisorAgentA2A:
    """
    Supervisor Agent with A2A Integration
    
    Phase 1 Migration:
    - AccountAgent: Routes via A2A protocol (NEW)
    - TransactionAgent, PaymentAgent, etc.: In-process (OLD) - to be migrated later
    
    This allows safe, incremental migration:
    1. Deploy AccountAgent A2A microservice
    2. Enable USE_A2A_FOR_ACCOUNT_AGENT feature flag
    3. Supervisor routes account queries to A2A endpoint
    4. Compare performance and correctness
    5. Once proven, migrate other agents
    """
    
    # Class-level attributes for compatibility with container
    name = "BankX Supervisor"
    description = "Multi-agent orchestrator for banking operations with A2A support"
    
    def __init__(
        self,
        # A2A endpoints for UC1 agents
        account_agent_a2a_url: str | None = None,
        transaction_agent_a2a_url: str | None = None,
        payment_agent_a2a_url: str | None = None,
        
        # A2A endpoints for UC2/UC3 agents
        prodinfo_faq_agent_a2a_url: str | None = None,
        ai_money_coach_agent_a2a_url: str | None = None,
        escalation_comms_agent_a2a_url: str | None = None,
        
        # Feature flags
        enable_a2a_account: bool = False,
        enable_a2a_transaction: bool = False,
        enable_a2a_payment: bool = False,
        enable_a2a_prodinfo: bool = False,
        enable_a2a_ai_coach: bool = False,
        enable_a2a_escalation: bool = False,
        
        # OLD agents (fallback for non-A2A routing)
        account_agent_old=None,
        transaction_agent_old=None,
        payment_agent_old=None,
        prodinfo_agent_old=None,
        ai_coach_agent_old=None,
        escalation_comms_agent_old=None,
        
        # Services (from old supervisor)
        cache_manager=None,
        conversation_manager=None,
        **kwargs
    ):
        """
        Initialize Supervisor with A2A and OLD agent support
        
        Args:
            *_agent_a2a_url: A2A endpoints for specialist agents
            enable_a2a_*: Feature flags to enable A2A routing
            *_agent_old: Fallback OLD in-process agents
        """
        # A2A URLs - UC1
        self.account_agent_a2a_url = account_agent_a2a_url
        self.transaction_agent_a2a_url = transaction_agent_a2a_url
        self.payment_agent_a2a_url = payment_agent_a2a_url
        
        # A2A URLs - UC2/UC3
        self.prodinfo_faq_agent_a2a_url = prodinfo_faq_agent_a2a_url
        self.ai_money_coach_agent_a2a_url = ai_money_coach_agent_a2a_url
        self.escalation_comms_agent_a2a_url = escalation_comms_agent_a2a_url
        
        # Feature flags
        self.enable_a2a_account = enable_a2a_account
        self.enable_a2a_transaction = enable_a2a_transaction
        self.enable_a2a_payment = enable_a2a_payment
        self.enable_a2a_prodinfo = enable_a2a_prodinfo
        self.enable_a2a_ai_coach = enable_a2a_ai_coach
        self.enable_a2a_escalation = enable_a2a_escalation
        
        # OLD agent references (for non-A2A routing)
        self.account_agent_old = account_agent_old
        self.transaction_agent_old = transaction_agent_old
        self.payment_agent_old = payment_agent_old
        self.prodinfo_agent_old = prodinfo_agent_old
        self.ai_coach_agent_old = ai_coach_agent_old
        self.escalation_comms_agent_old = escalation_comms_agent_old
        
        # Services (from old supervisor - needed for full feature parity)
        self.cache_manager = cache_manager
        self.conversation_manager = conversation_manager
        
        # HTTP client for A2A calls
        self.http_client = httpx.AsyncClient(timeout=300.0)
        
        # Azure OpenAI client for LLM-based classification fallback
        self.openai_client = None
        if settings.AZURE_OPENAI_ENDPOINT:
            try:
                from app.config.azure_credential import get_azure_credential
                credential = get_azure_credential()
                token = credential.get_token("https://cognitiveservices.azure.com/.default")
                self.openai_client = AsyncAzureOpenAI(
                    azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                    api_version="2024-10-21",
                    azure_ad_token=token.token
                )
                logger.info("✅ Azure OpenAI client initialized for LLM classification fallback")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Azure OpenAI client: {e}")
                logger.warning("   LLM classification fallback will be disabled")
        
        # Track routed agent name for observability
        self.routed_agent_name: str | None = None
        self.pending_routing_events: list = []
        
        # Conversation state
        self.current_session_id: str | None = None
        self.last_active_thread: str | None = None
        
        # Track conversation history for context passing
        self.last_routed_agent: str | None = None
        self.last_user_message: str | None = None
        self.last_agent_response: str | None = None
        
        # Inherit other supervisor state from kwargs
        self.current_thread = kwargs.get('current_thread')
        self.user_context = kwargs.get('user_context')
        
        logger.info(f"SupervisorAgentA2A initialized (Phase 1)")
        logger.info(f"  A2A Account Agent: {'ENABLED' if enable_a2a_account else 'DISABLED'}")
        logger.info(f"  A2A Transaction Agent: {'ENABLED' if enable_a2a_transaction else 'DISABLED'}")
        logger.info(f"  A2A Payment Agent: {'ENABLED' if enable_a2a_payment else 'DISABLED'}")
        if enable_a2a_account:
            logger.info(f"  Account A2A URL: {account_agent_a2a_url}")
        if enable_a2a_transaction:
            logger.info(f"  Transaction A2A URL: {transaction_agent_a2a_url}")
        if enable_a2a_payment:
            logger.info(f"  Payment A2A URL: {payment_agent_a2a_url}")
        
        if not any([self.enable_a2a_account, self.enable_a2a_transaction, self.enable_a2a_payment]):
            logger.info("⏭️  All A2A agents DISABLED - using old in-process agents")

    async def route_to_account_agent(self, user_message: str, thread_id: str | None = None) -> str:
        """
        Route to AccountAgent - A2A or OLD based on feature flag
        
        Phase 1: Supports both A2A (NEW) and in-process (OLD) for safe migration
        """
        from app.observability.banking_telemetry import get_banking_telemetry
        
        self.routed_agent_name = "AccountAgent"
        print(f"🎯 [DEBUG] Routing to AccountAgent: A2A={'YES' if self.enable_a2a_account else 'NO'}")
        
        # Store routing events for observability
        import time
        self.pending_routing_events = [
            {
                "type": "thinking",
                "step": "routing",
                "message": "Specialist agent determined",
                "status": "completed",
                "timestamp": time.time()
            },
            {
                "type": "thinking",
                "step": "agent_selected",
                "message": f"🎯 {self.routed_agent_name} selected ({'A2A' if self.enable_a2a_account else 'In-Process'})",
                "status": "completed",
                "timestamp": time.time()
            }
        ]
        
        telemetry = get_banking_telemetry()
        # Use passed thread_id or get from current_thread
        initial_thread_id = thread_id or (self.current_thread.service_thread_id if self.current_thread else None)
        
        logger.info(f"🔥 SupervisorAgent routing to AccountAgent: {user_message}")
        logger.info(f"🧵 Thread ID: {initial_thread_id}")
        
        # Track triage rule match
        triage_rule = self._determine_triage_rule(user_message, "AccountAgent")
        telemetry.track_triage_rule_match(triage_rule, "AccountAgent", user_message)
        
        # # Route via A2A or OLD based on feature flag
        # if self.enable_a2a_account and self.account_agent_a2a_url:
        #     # NEW: Route via A2A protocol
        #     print(f"✅ [A2A CHECK] A2A enabled: {self.enable_a2a_account}, URL: {self.account_agent_a2a_url}")
        #     logger.info(f"✅ [A2A] Routing to A2A AccountAgent at {self.account_agent_a2a_url}")
        #     return await self._route_via_a2a_account_agent(user_message, initial_thread_id)
        # else:
        #     # OLD: Route via in-process agent (fallback)
        #     print(f"⚠️ [A2A CHECK] A2A disabled or no URL. enabled={self.enable_a2a_account}, url={self.account_agent_a2a_url}")
        #     logger.info(f"⚠️ [OLD] Routing to in-process AccountAgent (A2A disabled or no URL)")
        #     return await self._route_via_old_account_agent(user_message, initial_thread_id)

        # Track agent decision with telemetry
        start_time = time.time()
        result = None
        
        try:
            # Route via A2A or OLD based on feature flag
            if self.enable_a2a_account and self.account_agent_a2a_url:
                # NEW: Route via A2A protocol
                print(f"✅ [A2A CHECK] A2A enabled: {self.enable_a2a_account}, URL: {self.account_agent_a2a_url}")
                logger.info(f"✅ [A2A] Routing to A2A AccountAgent at {self.account_agent_a2a_url}")
                result = await self._route_via_a2a_account_agent(user_message, initial_thread_id)
            else:
                # OLD: Route via in-process agent (fallback)
                print(f"⚠️ [A2A CHECK] A2A disabled or no URL. enabled={self.enable_a2a_account}, url={self.account_agent_a2a_url}")
                logger.info(f"⚠️ [OLD] Routing to in-process AccountAgent (A2A disabled or no URL)")
                result = await self._route_via_old_account_agent(user_message, initial_thread_id)
            
            # Log successful decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("AccountAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule(triage_rule)
                decision.set_reasoning("Account query classified for AccountAgent")
                decision.add_tool_considered("getAccountsByUserName")
                decision.add_tool_considered("getAccountDetails")
                decision.add_tool_invoked("account_mcp", {"mode": "a2a" if self.enable_a2a_account else "in-process"})
                decision.set_result("success", f"Response from AccountAgent ({len(result)} chars)")
                decision.context = {"mode": "a2a" if self.enable_a2a_account else "in-process"}
            
            return result
            
        except Exception as e:
            # Log failed decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("AccountAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule(triage_rule)
                decision.set_reasoning("Account query classified for AccountAgent")
                decision.add_tool_considered("getAccountsByUserName")
                decision.add_tool_considered("getAccountDetails")
                decision.set_result("error", f"Error: {str(e)}")
                decision.context = {"mode": "a2a" if self.enable_a2a_account else "in-process", "error": str(e)}
            raise
    async def _route_via_a2a_account_agent(self, user_message: str, thread_id: str | None) -> str:
        """
        Route to AccountAgent via A2A protocol (NEW)
        """
        logger.info("📡 [A2A] Routing to AccountAgent via A2A protocol...")
        
        try:
            # Extract customer_id from user context
            customer_id = self.user_context.customer_id if self.user_context else "Somchai"
            
            # Prepare A2A request
            a2a_request = {
                "messages": [
                    {"role": "user", "content": user_message}
                ],
                "thread_id": thread_id or f"thread_{customer_id}",
                "customer_id": customer_id,
                "stream": False,  # Non-streaming for simplicity in Phase 1
            }
            
            logger.info(f"📡 [A2A] Sending request to {self.account_agent_a2a_url}/a2a/invoke")
            logger.info(f"📡 [A2A] Request: {json.dumps(a2a_request, indent=2)}")
            
            # Call AccountAgent A2A endpoint
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.account_agent_a2a_url}/a2a/invoke",
                    json=a2a_request,
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code == 200:
                    result = response.json()
                    agent_response = result.get("content", "")
                    
                    logger.info(f"✅ [A2A] Received response from AccountAgent A2A")
                    logger.info(f"📝 [A2A] Response length: {len(agent_response)} chars")
                    
                    return agent_response
                else:
                    error_msg = f"A2A request failed with status {response.status_code}: {response.text}"
                    logger.error(f"❌ [A2A] {error_msg}")
                    return f"I couldn't connect to the account service. Please try again later. (Error: {response.status_code})"
        
        except httpx.TimeoutException:
            logger.error("❌ [A2A] Request timeout")
            return "The account service is taking too long to respond. Please try again."
        
        except Exception as e:
            logger.error(f"❌ [A2A] Unexpected error: {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}"

    async def _route_via_old_account_agent(self, user_message: str, thread_id: str | None) -> str:
        """
        Route to AccountAgent via OLD in-process method (fallback)
        """
        logger.info("🔄 [OLD] Routing to AccountAgent via in-process method...")
        
        if not self.account_agent_old:
            logger.error("❌ [OLD] No OLD AccountAgent available for fallback")
            return "Account agent is not available. Please try again later."
        
        try:
            # Extract customer_id
            customer_id = self.user_context.customer_id if self.user_context else "Somchai"
            
            # Build OLD agent
            af_account_agent = await self.account_agent_old.build_af_agent(thread_id, customer_id=customer_id)
            
            # Set thread context on MCP tools
            if hasattr(af_account_agent, '_mcp_tools'):
                for tool in af_account_agent._mcp_tools:
                    if hasattr(tool, 'set_thread_context'):
                        tool.set_thread_context(self.current_thread)
            
            # Execute OLD agent
            response = await af_account_agent.run(user_message, thread=self.current_thread)
            
            logger.info(f"✅ [OLD] Received response from AccountAgent (in-process)")
            return response.text
        
        except Exception as e:
            logger.error(f"❌ [OLD] Error in old AccountAgent: {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}"

    def _determine_triage_rule(self, user_message: str, agent_name: str) -> str:
        """
        Determine which triage rule matched for this routing decision
        (Simplified for Phase 1 - copy from old supervisor)
        """
        # TODO: Implement full triage logic or inherit from old supervisor
        return f"Routed to {agent_name} based on query classification"

    # OLD routing methods (unchanged for now - to be migrated in later phases)
    async def route_to_transaction_agent(self, user_message: str, thread_id: str | None = None) -> str:
        """Route to TransactionAgent - A2A or OLD based on feature flag"""
        from app.observability.banking_telemetry import get_banking_telemetry
        import time
        
        self.routed_agent_name = "TransactionAgent"
        print(f"🎯 [DEBUG] Routing to TransactionAgent: A2A={'YES' if self.enable_a2a_transaction else 'NO'}")
        
        telemetry = get_banking_telemetry()
        # Use provided thread_id or fallback to current_thread
        initial_thread_id = thread_id or (self.current_thread.service_thread_id if self.current_thread else None)
        
        logger.info(f"🔥 SupervisorAgent routing to TransactionAgent: {user_message} (thread={initial_thread_id})")
        
        # # Route via A2A or OLD based on feature flag
        # if self.enable_a2a_transaction and self.transaction_agent_a2a_url:
        #     # NEW: Route via A2A protocol
        #     return await self._route_via_a2a_generic(
        #         agent_name="TransactionAgent",
        #         a2a_url=self.transaction_agent_a2a_url,
        #         user_message=user_message,
        #         thread_id=initial_thread_id
        #     )
        # else:
        #     # OLD: Route via in-process agent (fallback)
        #     logger.info("🔄 [OLD] Routing to TransactionAgent (in-process)")
        #     if self.transaction_agent_old:
        #         customer_id = self.user_context.customer_id if self.user_context else "Somchai"
        #         af_transaction_agent = await self.transaction_agent_old.build_af_agent(initial_thread_id, customer_id=customer_id)
        #         response = await af_transaction_agent.run(user_message, thread=self.current_thread)
        #         return response.text
        #     return "Transaction agent not available"

        # Track agent decision with telemetry
        start_time = time.time()
        result = None
        
        try:
            # Route via A2A or OLD based on feature flag
            if self.enable_a2a_transaction and self.transaction_agent_a2a_url:
                # NEW: Route via A2A protocol
                result = await self._route_via_a2a_generic(
                    agent_name="TransactionAgent",
                    a2a_url=self.transaction_agent_a2a_url,
                    user_message=user_message,
                    thread_id=initial_thread_id
                )
            else:
                # OLD: Route via in-process agent (fallback)
                logger.info("🔄 [OLD] Routing to TransactionAgent (in-process)")
                if self.transaction_agent_old:
                    customer_id = self.user_context.customer_id if self.user_context else "Somchai"
                    af_transaction_agent = await self.transaction_agent_old.build_af_agent(initial_thread_id, customer_id=customer_id)
                    response = await af_transaction_agent.run(user_message, thread=self.current_thread)
                    result = response.text
                else:
                    result = "Transaction agent not available"
            
            # Log successful decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("TransactionAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC2_TRANSACTION_AGENT")
                decision.set_reasoning("Transaction query classified for TransactionAgent")
                decision.add_tool_considered("getTransactionsByAccountId")
                decision.add_tool_considered("getTransactionDetails")
                decision.add_tool_invoked("transaction_mcp", {"mode": "a2a" if self.enable_a2a_transaction else "in-process"})
                decision.set_result("success", f"Response from TransactionAgent ({len(result)} chars)")
                decision.context = {"mode": "a2a" if self.enable_a2a_transaction else "in-process"}
            
            return result
            
        except Exception as e:
            # Log failed decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("TransactionAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC2_TRANSACTION_AGENT")
                decision.set_reasoning("Transaction query classified for TransactionAgent")
                decision.add_tool_considered("getTransactionsByAccountId")
                decision.add_tool_considered("getTransactionDetails")
                decision.set_result("error", f"Error: {str(e)}")
                decision.context = {"mode": "a2a" if self.enable_a2a_transaction else "in-process", "error": str(e)}
            raise        

    async def route_to_payment_agent(self, user_message: str, thread_id: str | None = None) -> str:
        """Route to PaymentAgent - A2A or OLD based on feature flag"""
        from app.observability.banking_telemetry import get_banking_telemetry
        import time
        self.routed_agent_name = "PaymentAgent"
        print(f"🎯 [DEBUG] Routing to PaymentAgent: A2A={'YES' if self.enable_a2a_payment else 'NO'}")
        
        telemetry = get_banking_telemetry()
        # Use provided thread_id or fallback to current_thread
        initial_thread_id = thread_id or (self.current_thread.service_thread_id if self.current_thread else None)
        
        logger.info(f"🔥 SupervisorAgent routing to PaymentAgent: {user_message} (thread={initial_thread_id})")
        
        # Route via A2A or OLD based on feature flag
        # if self.enable_a2a_payment and self.payment_agent_a2a_url:
        #     # NEW: Route via A2A protocol
        #     return await self._route_via_a2a_generic(
        #         agent_name="PaymentAgent",
        #         a2a_url=self.payment_agent_a2a_url,
        #         user_message=user_message,
        #         thread_id=initial_thread_id
        #     )
        # else:
        #     # OLD: Route via in-process agent (fallback)
        #     logger.info("🔄 [OLD] Routing to PaymentAgent (in-process)")
        #     if self.payment_agent_old:
        #         customer_id = self.user_context.customer_id if self.user_context else "Somchai"
        #         af_payment_agent = await self.payment_agent_old.build_af_agent(initial_thread_id, customer_id=customer_id)
        #         response = await af_payment_agent.run(user_message, thread=self.current_thread)
        #         return response.text
        #     return "Payment agent not available"
    

        # Track agent decision with telemetry
        start_time = time.time()
        result = None
        
        try:
            # Route via A2A or OLD based on feature flag
            if self.enable_a2a_payment and self.payment_agent_a2a_url:
                # NEW: Route via A2A protocol
                result = await self._route_via_a2a_generic(
                    agent_name="PaymentAgent",
                    a2a_url=self.payment_agent_a2a_url,
                    user_message=user_message,
                    thread_id=initial_thread_id
                )
            else:
                # OLD: Route via in-process agent (fallback)
                logger.info("🔄 [OLD] Routing to PaymentAgent (in-process)")
                if self.payment_agent_old:
                    customer_id = self.user_context.customer_id if self.user_context else "Somchai"
                    af_payment_agent = await self.payment_agent_old.build_af_agent(initial_thread_id, customer_id=customer_id)
                    response = await af_payment_agent.run(user_message, thread=self.current_thread)
                    result = response.text
                else:
                    result = "Payment agent not available"
            
            # Log successful decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("PaymentAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC4_PAYMENT_AGENT")
                decision.set_reasoning("Payment query classified for PaymentAgent")
                decision.add_tool_considered("createPayment")
                decision.add_tool_considered("getBeneficiaryByName")
                decision.add_tool_invoked("payment_mcp", {"mode": "a2a" if self.enable_a2a_payment else "in-process"})
                decision.set_result("success", f"Response from PaymentAgent ({len(result)} chars)")
                decision.context = {"mode": "a2a" if self.enable_a2a_payment else "in-process"}
            
            return result
            
        except Exception as e:
            # Log failed decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("PaymentAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC4_PAYMENT_AGENT")
                decision.set_reasoning("Payment query classified for PaymentAgent")
                decision.add_tool_considered("createPayment")
                decision.add_tool_considered("getBeneficiaryByName")
                decision.set_result("error", f"Error: {str(e)}")
                decision.context = {"mode": "a2a" if self.enable_a2a_payment else "in-process", "error": str(e)}
            raise


    async def route_to_escalation_agent(self, user_message: str, thread_id: str | None = None) -> str:
        """Route to EscalationAgent - A2A or OLD based on feature flag"""
        from app.observability.banking_telemetry import get_banking_telemetry
        import time
        self.routed_agent_name = "EscalationAgent"
        print(f"🎯 [DEBUG] Routing to EscalationAgent: A2A={'YES' if self.enable_a2a_escalation else 'NO'}")
        
        telemetry = get_banking_telemetry()
        # Use provided thread_id or fallback to current_thread
        initial_thread_id = thread_id or (self.current_thread.service_thread_id if self.current_thread else None)
        
        logger.info(f"🔥 SupervisorAgent routing to EscalationAgent: {user_message} (thread={initial_thread_id})")
        
        # Check if this is a ticket confirmation from Product Info or AI Coach
        message_lower = user_message.lower().strip()
        is_confirmation = any(keyword in message_lower for keyword in ["yes", "yeah", "yep", "ok", "confirm", "create", "proceed"])
        is_ticket_request = "ticket" in message_lower or "escalate" in message_lower
        
        # If user is confirming AND last agent was Product Info or AI Coach, route back to them
        if is_confirmation and self.last_routed_agent in ["Product Info Agent", "AI Money Coach"]:
            logger.info(f"🔄 [CONTINUATION] User confirming ticket creation from {self.last_routed_agent}")
            logger.info(f"🔄 [CONTINUATION] Routing BACK to {self.last_routed_agent} (not Escalation directly)")
            
            # Route back to the agent that offered the ticket
            if self.last_routed_agent == "Product Info Agent":
                return await self.route_to_prodinfo_agent(user_message, thread_id)
            elif self.last_routed_agent == "AI Money Coach":
                return await self.route_to_ai_money_coach(user_message, thread_id)
        
        # # Route via A2A or OLD based on feature flag
        # if self.enable_a2a_escalation and self.escalation_comms_agent_a2a_url:
        #     # NEW: Route via A2A protocol
        #     # If we have conversation history, pass it along
        #     conversation_history = None
        #     if self.last_user_message and self.last_agent_response:
        #         conversation_history = [
        #             {"role": "user", "content": self.last_user_message},
        #             {"role": "assistant", "content": self.last_agent_response}
        #         ]
            
        #     return await self._route_via_a2a_generic(
        #         agent_name="EscalationAgent",
        #         a2a_url=self.escalation_comms_agent_a2a_url,
        #         user_message=user_message,
        #         thread_id=initial_thread_id,
        #         conversation_history=conversation_history
        #     )
        # else:
        #     # OLD: Route via in-process agent (fallback)
        #     logger.info("🔄 [OLD] Routing to EscalationAgent (in-process)")
        #     if self.escalation_comms_agent_old:
        #         af_escalation_agent = await self.escalation_comms_agent_old.build_af_agent(thread_id=None)
        #         response = await af_escalation_agent.run(user_message, thread=self.current_thread)
        #         return response.text
        #     return "Escalation agent not available"
    
        # Track agent decision with telemetry
        start_time = time.time()
        result = None
        
        try:
            # Route via A2A or OLD based on feature flag
            if self.enable_a2a_escalation and self.escalation_comms_agent_a2a_url:
                # NEW: Route via A2A protocol
                # If we have conversation history, pass it along
                conversation_history = None
                if self.last_user_message and self.last_agent_response:
                    conversation_history = [
                        {"role": "user", "content": self.last_user_message},
                        {"role": "assistant", "content": self.last_agent_response}
                    ]
                
                result = await self._route_via_a2a_generic(
                    agent_name="EscalationAgent",
                    a2a_url=self.escalation_comms_agent_a2a_url,
                    user_message=user_message,
                    thread_id=initial_thread_id,
                    conversation_history=conversation_history
                )
            else:
                # OLD: Route via in-process agent (fallback)
                logger.info("🔄 [OLD] Routing to EscalationAgent (in-process)")
                if self.escalation_comms_agent_old:
                    af_escalation_agent = await self.escalation_comms_agent_old.build_af_agent(thread_id=None)
                    response = await af_escalation_agent.run(user_message, thread=self.current_thread)
                    result = response.text
                else:
                    result = "Escalation agent not available"
            
            # Log successful decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("EscalationAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC6_ESCALATION_AGENT")
                decision.set_reasoning("Escalation query classified for EscalationAgent")
                decision.add_tool_considered("createTicket")
                decision.add_tool_considered("notifyHumanAgent")
                decision.add_tool_invoked("escalation_mcp", {"mode": "a2a" if self.enable_a2a_escalation else "in-process"})
                decision.set_result("success", f"Response from EscalationAgent ({len(result)} chars)")
                decision.context = {"mode": "a2a" if self.enable_a2a_escalation else "in-process"}
            
            return result
            
        except Exception as e:
            # Log failed decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("EscalationAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC6_ESCALATION_AGENT")
                decision.set_reasoning("Escalation query classified for EscalationAgent")
                decision.add_tool_considered("createTicket")
                decision.add_tool_considered("notifyHumanAgent")
                decision.set_result("error", f"Error: {str(e)}")
                decision.context = {"mode": "a2a" if self.enable_a2a_escalation else "in-process", "error": str(e)}
            raise

    async def route_to_ai_money_coach(self, user_message: str, thread_id: str | None = None) -> str:
        """Route to AI Money Coach Agent - A2A or OLD based on feature flag"""
        from app.observability.banking_telemetry import get_banking_telemetry
        import time
        self.routed_agent_name = "AIMoneyCoachAgent"
        print(f"🎯 [DEBUG] Routing to AI Money Coach: A2A={'YES' if self.enable_a2a_ai_coach else 'NO'}")
        
        telemetry = get_banking_telemetry()
        # Use provided thread_id or fallback to current_thread
        initial_thread_id = thread_id or (self.current_thread.service_thread_id if self.current_thread else None)
        
        logger.info(f"🔥 SupervisorAgent routing to AI Money Coach: {user_message} (thread={initial_thread_id})")
        
        # # Route via A2A or OLD based on feature flag
        # if self.enable_a2a_ai_coach and self.ai_money_coach_agent_a2a_url:
        #     # NEW: Route via A2A protocol
        #     return await self._route_via_a2a_generic(
        #         agent_name="AI Money Coach",
        #         a2a_url=self.ai_money_coach_agent_a2a_url,
        #         user_message=user_message,
        #         thread_id=initial_thread_id
        #     )
        # else:
        #     # OLD: Route via in-process agent (fallback)
        #     logger.info("🔄 [OLD] Routing to AI Money Coach (in-process)")
        #     if self.ai_coach_agent_old:
        #         af_agent = await self.ai_coach_agent_old.build_af_agent(thread_id=None)
        #         response = await af_agent.run(user_message, thread=self.current_thread)
        #         return response.text
        #     return "AI Money Coach is not available"


        # Track agent decision with telemetry
        start_time = time.time()
        result = None
        
        try:
            # Route via A2A or OLD based on feature flag
            if self.enable_a2a_ai_coach and self.ai_money_coach_agent_a2a_url:
                # NEW: Route via A2A protocol
                result = await self._route_via_a2a_generic(
                    agent_name="AI Money Coach",
                    a2a_url=self.ai_money_coach_agent_a2a_url,
                    user_message=user_message,
                    thread_id=initial_thread_id
                )
            else:
                # OLD: Route via in-process agent (fallback)
                logger.info("🔄 [OLD] Routing to AI Money Coach (in-process)")
                if self.ai_coach_agent_old:
                    af_agent = await self.ai_coach_agent_old.build_af_agent(thread_id=None)
                    response = await af_agent.run(user_message, thread=self.current_thread)
                    result = response.text
                else:
                    result = "AI Money Coach is not available"
            
            # Log successful decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("AIMoneyCoachAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC3_AI_MONEY_COACH")
                decision.set_reasoning("Financial advice query classified for AIMoneyCoachAgent")
                decision.add_tool_considered("searchMoneyCoachKnowledge")
                decision.add_tool_considered("createTicket")
                decision.add_tool_invoked("ai_money_coach_mcp", {"mode": "a2a" if self.enable_a2a_ai_coach else "in-process"})
                decision.set_result("success", f"Response from AIMoneyCoachAgent ({len(result)} chars)")
                decision.context = {"mode": "a2a" if self.enable_a2a_ai_coach else "in-process"}
            
            return result
            
        except Exception as e:
            # Log failed decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("AIMoneyCoachAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC3_AI_MONEY_COACH")
                decision.set_reasoning("Financial advice query classified for AIMoneyCoachAgent")
                decision.add_tool_considered("searchMoneyCoachKnowledge")
                decision.add_tool_considered("createTicket")
                decision.set_result("error", f"Error: {str(e)}")
                decision.context = {"mode": "a2a" if self.enable_a2a_ai_coach else "in-process", "error": str(e)}
            raise        
    
    def _get_a2a_url_for_agent(self, agent_name: str) -> str | None:
        """Helper to get A2A URL for an agent by name"""
        url_map = {
            "Account Agent": self.account_agent_a2a_url if self.enable_a2a_account else None,
            "Transaction Agent": self.transaction_agent_a2a_url if self.enable_a2a_transaction else None,
            "Payment Agent": self.payment_agent_a2a_url if self.enable_a2a_payment else None,
            "Product Info Agent": self.prodinfo_faq_agent_a2a_url if self.enable_a2a_prodinfo else None,
            "AI Money Coach": self.ai_money_coach_agent_a2a_url if self.enable_a2a_ai_coach else None,
            "Escalation Agent": self.escalation_comms_agent_a2a_url if self.enable_a2a_escalation else None,
        }
        return url_map.get(agent_name)
    
    async def route_to_prodinfo_agent(self, user_message: str, thread_id: str | None = None) -> str:
        """Route to Product Info Agent - A2A or OLD based on feature flag"""
        from app.observability.banking_telemetry import get_banking_telemetry
        import time
        self.routed_agent_name = "ProdInfoFAQAgent"
        print(f"🎯 [DEBUG] Routing to Product Info: A2A={'YES' if self.enable_a2a_prodinfo else 'NO'}")
        
        telemetry = get_banking_telemetry()
        # Use provided thread_id or fallback to current_thread
        initial_thread_id = thread_id or (self.current_thread.service_thread_id if self.current_thread else None)
        
        logger.info(f"🔥 SupervisorAgent routing to Product Info: {user_message} (thread={initial_thread_id})")
        
        # # Route via A2A or OLD based on feature flag
        # if self.enable_a2a_prodinfo and self.prodinfo_faq_agent_a2a_url:
        #     # NEW: Route via A2A protocol
        #     return await self._route_via_a2a_generic(
        #         agent_name="Product Info",
        #         a2a_url=self.prodinfo_faq_agent_a2a_url,
        #         user_message=user_message,
        #         thread_id=initial_thread_id
        #     )
        # else:
        #     # OLD: Route via in-process agent (fallback)
        #     logger.info("🔄 [OLD] Routing to Product Info (in-process)")
        #     if self.prodinfo_agent_old:
        #         af_agent = await self.prodinfo_agent_old.build_af_agent(thread_id=None)
        #         response = await af_agent.run(user_message, thread=self.current_thread)
        #         return response.text
        #     return "Product information is not available"

        # Track agent decision with telemetry
        start_time = time.time()
        result = None
        
        try:
            # Route via A2A or OLD based on feature flag
            if self.enable_a2a_prodinfo and self.prodinfo_faq_agent_a2a_url:
                # NEW: Route via A2A protocol
                result = await self._route_via_a2a_generic(
                    agent_name="Product Info",
                    a2a_url=self.prodinfo_faq_agent_a2a_url,
                    user_message=user_message,
                    thread_id=initial_thread_id
                )
            else:
                # OLD: Route via in-process agent (fallback)
                logger.info("🔄 [OLD] Routing to Product Info (in-process)")
                if self.prodinfo_agent_old:
                    af_agent = await self.prodinfo_agent_old.build_af_agent(thread_id=None)
                    response = await af_agent.run(user_message, thread=self.current_thread)
                    result = response.text
                else:
                    result = "Product information is not available"
            
            # Log successful decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("ProdInfoFAQAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC5_PRODINFO_FAQ_AGENT")
                decision.set_reasoning("Product info/FAQ query classified for ProdInfoFAQAgent")
                decision.add_tool_considered("searchProductFAQs")
                decision.add_tool_considered("createTicket")
                decision.add_tool_invoked("prodinfo_mcp", {"mode": "a2a" if self.enable_a2a_prodinfo else "in-process"})
                decision.set_result("success", f"Response from ProdInfoFAQAgent ({len(result)} chars)")
                decision.context = {"mode": "a2a" if self.enable_a2a_prodinfo else "in-process"}
            
            return result
            
        except Exception as e:
            # Log failed decision
            duration = time.time() - start_time
            with telemetry.track_agent_decision("ProdInfoFAQAgent", user_message, initial_thread_id) as decision:
                decision.set_triage_rule("UC5_PRODINFO_FAQ_AGENT")
                decision.set_reasoning("Product info/FAQ query classified for ProdInfoFAQAgent")
                decision.add_tool_considered("searchProductFAQs")
                decision.add_tool_considered("createTicket")
                decision.set_result("error", f"Error: {str(e)}")
                decision.context = {"mode": "a2a" if self.enable_a2a_prodinfo else "in-process", "error": str(e)}
            raise        
    
    async def _route_via_a2a_generic(self, agent_name: str, a2a_url: str, user_message: str, thread_id: str | None, conversation_history: list | None = None) -> str:
        """Generic A2A routing method (reusable for all agents)"""
        logger.info(f"📡 [A2A] Routing to {agent_name} via A2A protocol...")
        
        try:
            customer_id = self.user_context.customer_id if self.user_context else "Somchai"
            user_email = self.user_context.entra_user_email if self.user_context else "user@bankx.com"
            
            # For PaymentAgent: Prepend username to ALL user messages (so agent sees it in conversation, not just context)
            # This matches the pattern that works in Azure AI Foundry playground
            if agent_name == "PaymentAgent" or agent_name == "Payment Agent":
                user_message = f"my username is {user_email}, {user_message}"
                logger.info(f"💳 [PAYMENT FIX] Prepended username to current message: {user_message[:100]}...")
                
                # ALSO prepend username to all user messages in conversation history
                if conversation_history:
                    fixed_history = []
                    for msg in conversation_history:
                        if msg.get("role") == "user":
                            # Only prepend if not already prepended
                            content = msg.get("content", "")
                            if not content.startswith(f"my username is {user_email}"):
                                content = f"my username is {user_email}, {content}"
                            fixed_history.append({"role": "user", "content": content})
                        else:
                            # Keep assistant messages as-is
                            fixed_history.append(msg)
                    conversation_history = fixed_history
                    logger.info(f"💳 [PAYMENT FIX] Fixed {len([m for m in conversation_history if m.get('role') == 'user'])} user messages in history")
            
            # Build messages array - use conversation_history if provided, otherwise just current message
            if conversation_history:
                messages = conversation_history + [{"role": "user", "content": user_message}]
                logger.info(f"📡 [A2A] Passing {len(conversation_history)} history messages + current message")
            else:
                messages = [{"role": "user", "content": user_message}]
            
            a2a_request = {
                "messages": messages,
                "thread_id": thread_id or f"thread_{customer_id}",
                "customer_id": customer_id,
                "user_email": user_email,
                "stream": False,
            }
            
            logger.info(f"📡 [A2A] Sending request to {a2a_url}/a2a/invoke")
            
            # Use 60s timeout: First request needs time for MCP init, subsequent requests are instant
            async with httpx.AsyncClient(timeout=90.0) as client:
                response = await client.post(
                    f"{a2a_url}/a2a/invoke",
                    json=a2a_request,
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Extract response content from A2A response format
                    # A2A agents return: {"messages": [{"role": "user", ...}, {"role": "assistant", "content": "..."}]}
                    if "messages" in result and len(result["messages"]) >= 2:
                        # Get assistant message (last message in array)
                        assistant_message = result["messages"][-1]
                        agent_response = assistant_message.get("content", "")
                    else:
                        # Fallback: try direct content field (for compatibility)
                        agent_response = result.get("content", "")
                    
                    if not agent_response:
                        logger.warning(f"⚠️ [A2A] Empty response from {agent_name}, raw result: {result}")
                        agent_response = "I received an empty response. Please try again."
                    
                    logger.info(f"✅ [A2A] Received response from {agent_name} A2A ({len(agent_response)} chars)")
                    return agent_response
                else:
                    error_msg = f"A2A request failed with status {response.status_code}"
                    logger.error(f"❌ [A2A] {error_msg}")
                    return f"I couldn't connect to the {agent_name.lower()} service. Please try again later."
        
        except httpx.TimeoutException:
            logger.error(f"❌ [A2A] Request timeout for {agent_name}")
            return f"The {agent_name.lower()} service is taking too long to respond. Please try again."
        
        except Exception as e:
            logger.error(f"❌ [A2A] Unexpected error: {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}"

    async def processMessage(self, user_message: str, thread_id: str | None, user_context) -> tuple[str, str | None]:
        """
        Main entry point for non-streaming message processing (A2A mode)
        
        This is the interface called by the FastAPI chat endpoint.
        Handles cache-first logic and routing to A2A agents.
        """
        import time
        start_time = time.time()
        
        # Store user context for use in routing methods
        self.user_context = user_context
        
        # Create thread_id if not provided, using conversation_manager
        if not thread_id and self.conversation_manager:
            thread_id = self.conversation_manager.create_session()
            logger.info(f"✅ [CONVERSATION] Created new session: {thread_id}")
        elif not thread_id:
            # Fallback if conversation_manager not available
            import uuid
            thread_id = f"session_{uuid.uuid4().hex[:8]}"
            logger.warning(f"⚠️ [CONVERSATION] No conversation_manager, using fallback thread_id: {thread_id}")
        


        logger.info(f"[SUPERVISOR A2A] Processing message from {user_context.entra_user_email}: {user_message[:100]}")
        print(f"\n{'='*80}")
        print(f"🎯 [SUPERVISOR A2A] NEW MESSAGE RECEIVED")
        print(f"{'='*80}")
        print(f"💬 User Message: {user_message}")
        print(f"🧵 Thread ID: {thread_id}")
        print(f"👤 User: {user_context.entra_user_email} (Customer: {user_context.customer_id})")
        print(f"{'='*80}\n")
        
        # TODO: Add cache-first logic here
        # For now, route directly to account agent (simplified for Phase 1)
        logger.info("🚀 [A2A] Routing to AccountAgent via A2A...")
        
        response_text = await self.route_to_account_agent(user_message, thread_id)
        
        duration = time.time() - start_time
        logger.info(f"[SUPERVISOR A2A] Response sent | Duration: {duration:.2f}s")
        
        return response_text, thread_id
    
    async def _classify_with_llm(self, user_message: str) -> str:
        """
        Use LLM to classify query when keyword matching has low confidence
        
        Args:
            user_message: The user's query to classify
            
        Returns:
            Agent name: One of [Payment Agent, Transaction Agent, Account Agent, 
                               Product Info Agent, AI Money Coach]
        """
        if not self.openai_client:
            logger.warning("⚠️ [LLM] OpenAI client not available, defaulting to Account Agent")
            return "Account Agent"
        
        classification_prompt = f"""You are a banking query classifier. Analyze the user's query and determine which specialist agent should handle it.

AGENTS:
1. **Payment Agent** - Handles money transfers, payments, sending money to beneficiaries
2. **Transaction Agent** - Handles transaction history, spending analysis, past payments
3. **Account Agent** - Handles account balance, account details, cards, limits
4. **Product Info Agent** - Handles bank product information (interest rates, fees, account types, loans, credit cards)
5. **AI Money Coach** - Handles personal finance advice, budgeting, debt management, savings strategies
6. **Escalation Agent** - Handles support tickets, complaints, issues requiring human assistance

USER QUERY: "{user_message}"

INSTRUCTIONS:
- Respond with ONLY the agent name (e.g., "Payment Agent")
- Consider typos and variations (e.g., "trnasfer" means "transfer")
- If query mentions amounts and recipients (e.g., "50 THB to Somchai"), it's a payment
- If user explicitly asks to create ticket, file complaint, or escalate, choose "Escalation Agent"
- If uncertain, default to "Account Agent"

RESPONSE (agent name only):"""

        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.AZURE_OPENAI_MINI_DEPLOYMENT_NAME,  # Use mini for fast classification
                messages=[
                    {"role": "system", "content": "You are a precise banking query classifier. Respond with only the agent name."},
                    {"role": "user", "content": classification_prompt}
                ],
                temperature=0.0,  # Deterministic classification
                max_tokens=20,  # Just need agent name
                timeout=5.0  # Fast timeout - fallback if slow
            )
            
            classification = response.choices[0].message.content.strip()
            
            # Validate classification result
            valid_agents = ["Payment Agent", "Transaction Agent", "Account Agent", "Product Info Agent", "AI Money Coach", "Escalation Agent"]
            if classification in valid_agents:
                return classification
            else:
                logger.warning(f"⚠️ [LLM] Invalid classification '{classification}', defaulting to Account Agent")
                return "Account Agent"
                
        except Exception as e:
            logger.error(f"❌ [LLM] Classification failed: {e}")
            return "Account Agent"  # Safe fallback
    
    async def processMessageStream(self, user_message: str, thread_id: str | None, user_context) -> AsyncGenerator[tuple[str, bool, str | None, dict | None], None]:
        """
        Main entry point for streaming message processing (A2A mode)
        
        Yields:
            tuple[str, bool, str | None, dict | None]: (content_chunk, is_final, thread_id, thinking_event)
        """
        import time
        start_time = time.time()
        
        # Store user context for use in routing methods
        self.user_context = user_context
        
        logger.info(f"[SUPERVISOR A2A STREAM] Processing streaming message from {user_context.entra_user_email}: {user_message[:100]}")
        print(f"\n{'='*80}")
        print(f"🎯 [SUPERVISOR A2A STREAM] NEW STREAMING REQUEST")
        print(f"{'='*80}")
        print(f"💬 User Message: {user_message}")
        print(f"🧵 Thread ID: {thread_id}")
        print(f"👤 User: {user_context.entra_user_email} (Customer: {user_context.customer_id})")
        print(f"{'='*80}\n")
        
        # Check for escalation keywords first (skip analyzing step for escalation)
        message_lower = user_message.lower()
        is_escalation = any(phrase in message_lower for phrase in [
            "speak to someone", "talk to human", "human agent", "support ticket",
            "escalate", "file complaint", "complaint", "i want to speak"
        ])
        
        if is_escalation:
            # Emit analyzing step for escalation
            yield ("", False, None, {
                "type": "thinking",
                "step": "analyzing",
                "message": "Analyzing your request",
                "status": "in_progress",
                "timestamp": time.time()
            })
            # Route to escalation agent
            logger.info("🎯 [ESCALATION] User requested escalation")
            
            yield ("", False, None, {
                "type": "thinking",
                "step": "routing",
                "message": "Routing to Support Escalation",
                "agent_name": "EscalationCommsAgent",
                "status": "in_progress",
                "timestamp": time.time()
            })
            
            if self.escalation_comms_agent_old:
                # Create ticket
                import datetime
                ticket_id = f"TKT-{datetime.datetime.now().strftime('%Y-%H%M%S')}"
                customer_email = user_context.entra_user_email
                
                response_text = await self.route_to_escalation_comms_agent(
                    ticket_id=ticket_id,
                    subject="Customer Support Request",
                    description=user_message,
                    priority="medium",
                    customer_email=customer_email
                )
            else:
                response_text = "I understand you'd like to speak with someone. Unfortunately, our support system is temporarily unavailable. Please try again later or contact us at support@bankx.com"
            
            # Stream response
            words = response_text.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield (chunk, False, None, None)
            
            yield ("", False, None, {
                "type": "thinking",
                "step": "generating",
                "message": "Response generated",
                "status": "completed",
                "timestamp": time.time(),
                "duration": time.time() - start_time
            })
            
            yield ("", True, thread_id, None)
            
            # Track conversation
            if self.conversation_manager and thread_id:
                self.conversation_manager.add_message(thread_id, "user", user_message, azure_thread_id=thread_id)
                self.conversation_manager.add_message(thread_id, "assistant", response_text, azure_thread_id=thread_id)

            # Log Q&A pair in question-answer/ folder
            try:
                from app.utils.conversation_logger import get_conversation_logger
                conv_logger = get_conversation_logger()
                conv_logger.log_qa_pair(
                    session_id=thread_id or "no-thread",
                    question=user_message,
                    answer=response_text,
                    agent_used=routed_agent,
                    duration_seconds=time.time() - start_time,
                    customer_id=user_context.customer_id if user_context else None,
                    user_email=user_context.entra_user_email if user_context else None
                )
            except Exception as e:
                logger.error(f"❌ Error logging Q&A pair: {e}", exc_info=True)
            

            return
        
        # Try cache-first for read queries (skip for write operations and knowledge queries)
        skip_cache = any([
            # UC3 - Financial advice keywords
            any(word in message_lower for word in ["financial", "financially", "budget", "debt", "invest"]),
            # UC2 - Product info keywords (but NOT personal account queries like "what is my balance/limit")
            (any(phrase in message_lower for phrase in ["interest rate", "loan", "credit card", "product"]) or 
             ("what is" in message_lower and "my" not in message_lower)),
            # Write operations
            any(word in message_lower for word in ["pay", "transfer", "send money", "create", "add"])
        ])
        
        cached_response = None
        cache_agent = None
        cache_check_start = time.time()
        
        if not skip_cache and self.cache_manager:
            # Emit checking_cache step
            yield ("", False, None, {
                "type": "thinking",
                "step": "checking_cache",
                "message": "Checking cache for instant response",
                "status": "in_progress",
                "timestamp": time.time()
            })
            
            cached_response = await self._try_cache_response(user_message, user_context.customer_id)
            
            if cached_response:
                # Cache HIT - return instantly (skip analyzing step completely)
                logger.info(f"⚡ [CACHE HIT] Query answered from cache")
                cache_agent = self._determine_cache_agent(message_lower)
                
                yield ("", False, None, {
                    "type": "thinking",
                    "step": "checking_cache",
                    "message": "Cache hit - instant response",
                    "status": "completed",
                    "timestamp": time.time(),
                    "duration": time.time() - cache_check_start
                })
                
                # Emit routing event to highlight agent on map (even though cached)
                yield ("", False, None, {
                    "type": "thinking",
                    "step": "routing",
                    "message": f"Using cached result from {cache_agent}",
                    "agent_name": cache_agent,
                    "agent": cache_agent,  # Add for Agent System Map compatibility
                    "status": "completed",
                    "timestamp": time.time(),
                    "duration": 0
                })
                
                # Stream cached response word by word
                words = cached_response.split()
                for i, word in enumerate(words):
                    chunk = word + (" " if i < len(words) - 1 else "")
                    yield (chunk, False, None, None)
                
                yield ("", False, None, {
                    "type": "thinking",
                    "step": "generating",
                    "message": "Response generated from cache",
                    "status": "completed",
                    "timestamp": time.time(),
                    "duration": time.time() - start_time
                })
                
                yield ("", True, thread_id, None)
                
                # Track conversation
                if self.conversation_manager and thread_id:
                    self.conversation_manager.add_message(thread_id, "user", user_message, azure_thread_id=thread_id)
                    self.conversation_manager.add_message(thread_id, "assistant", cached_response, azure_thread_id=thread_id)
                
                # Log Q&A pair in question-answer/ folder
                try:
                    from app.utils.conversation_logger import get_conversation_logger
                    conv_logger = get_conversation_logger()
                    conv_logger.log_qa_pair(
                        session_id=thread_id or "cache-response",
                        question=user_message,
                        answer=cached_response,
                        agent_used=cache_agent or "Cache",
                        duration_seconds=time.time() - start_time,
                        customer_id=user_context.customer_id if user_context else None,
                        user_email=user_context.entra_user_email if user_context else None
                    )
                except Exception as e:
                    logger.error(f"❌ Error logging cached Q&A pair: {e}", exc_info=True)
                


                # Track telemetry
                from app.observability.banking_telemetry import get_banking_telemetry
                telemetry = get_banking_telemetry()
                telemetry.track_user_message(
                    user_query=user_message,
                    thread_id=thread_id or "cache-response",
                    response_text=cached_response,
                    duration_seconds=time.time() - start_time
                )
                
                return
        
        # Cache MISS or skipped - continue with agent routing
        if not skip_cache:
            yield ("", False, None, {
                "type": "thinking",
                "step": "checking_cache",
                "message": "Cache miss, querying live data",
                "status": "completed",
                "timestamp": time.time(),
                "duration": time.time() - cache_check_start
            })
        
        # NOW emit analyzing step for non-cached queries
        yield ("", False, None, {
            "type": "thinking",
            "step": "analyzing",
            "message": "Analyzing your request",
            "status": "in_progress",
            "timestamp": time.time()
        })
        
        # Mark analyzing as complete
        yield ("", False, None, {
            "type": "thinking",
            "step": "analyzing",
            "message": "Request analyzed",
            "status": "completed",
            "timestamp": time.time(),
            "duration": time.time() - start_time
        })
        
        # HYBRID ROUTING: Keyword matching (fast) → LLM classification (smart fallback)
        message_lower = user_message.lower()
        
        # Phase 1: Keyword-based classification with confidence scoring
        confidence_scores = {}
        
        # UC3 - Financial advice keywords
        financial_keywords = [
            "financial", "financially", "budget", "save money", "debt", "avalanche", "snowball", 
            "invest", "investment", "retirement", "financial security", "financial advice",
            "money management", "spending habits", "financial goal", "how to be"
        ]
        confidence_scores["AI Money Coach"] = sum(1 for word in financial_keywords if word in message_lower)
        
        # UC2 - Product info keywords
        product_keywords = [
            "interest rate", "savings account", "loan", "credit card", "fixed deposit",
            "td bonus", "account type", "eligibility", "fees", "charges", "product",
            "what is", "what are", "explain", "tell me about"
        ]
        confidence_scores["Product Info Agent"] = sum(1 for phrase in product_keywords if phrase in message_lower)
        
        # UC1 - Transaction keywords
        transaction_keywords = ["transaction", "history", "spent", "spending", "purchase", "payment history"]
        confidence_scores["Transaction Agent"] = sum(1 for word in transaction_keywords if word in message_lower)
        
        # UC1 - Payment keywords (with typo-tolerant matching)
        payment_score = 0
        payment_keywords = ["pay", "send money", "beneficiary", "recipient", "payment", "remit"]
        payment_score += sum(1 for word in payment_keywords if word in message_lower)
        
        # Fuzzy match for "transfer" (handle common typos)
        transfer_patterns = ["transfer", "trnasfer", "trasfer", "tranfer", "transfe", "transfr"]
        if any(pattern in message_lower for pattern in transfer_patterns):
            payment_score += 2  # High confidence for transfer variants
        
        # Currency + "to" pattern (e.g., "50 THB to Apichat")
        import re
        currency_to_pattern = r'\d+\s*(thb|baht|฿|\$|usd)\s+to\s+\w+'
        if re.search(currency_to_pattern, message_lower):
            payment_score += 3  # Very high confidence for payment pattern
        
        confidence_scores["Payment Agent"] = payment_score
        
        # Account Agent - default with balance/account keywords
        account_keywords = ["balance", "account", "detail", "information"]
        confidence_scores["Account Agent"] = sum(1 for word in account_keywords if word in message_lower)
        
        # Escalation Agent - ticket management keywords
        escalation_keywords = ["ticket", "escalate", "complaint", "issue", "problem", "help", "support"]
        escalation_score = sum(1 for word in escalation_keywords if word in message_lower)
        
        # Boost score if explicit ticket creation phrases
        if any(phrase in message_lower for phrase in ["create ticket", "open ticket", "need help", "file complaint"]):
            escalation_score += 3
        
        confidence_scores["Escalation Agent"] = escalation_score
        
        # Determine best match and confidence level
        max_score = max(confidence_scores.values())
        best_agents = [agent for agent, score in confidence_scores.items() if score == max_score]
        
        # High confidence threshold: 2+ keyword matches
        # Low confidence: 0-1 matches OR multiple agents tied
        is_high_confidence = max_score >= 2 and len(best_agents) == 1
        
        if is_high_confidence:
            # FAST PATH: High confidence keyword match
            agent_name = best_agents[0]
            logger.info(f"🎯 [KEYWORD] High confidence match (score={max_score}): {agent_name}")
        
        else:
            # LOW CONFIDENCE: Fall back to LLM classification
            logger.info(f"⚠️ [KEYWORD] Low confidence (score={max_score}, candidates={best_agents})")
            logger.info("🧠 [LLM] Falling back to LLM classification...")
            
            agent_name = await self._classify_with_llm(user_message)
            logger.info(f"✅ [LLM] Classification result: {agent_name}")
        
        # Emit routing step with correct agent (include both agent_name and agent for compatibility)
        agent_mode = "A2A" if (
            (agent_name == "Payment Agent" and self.enable_a2a_payment) or
            (agent_name == "Account Agent" and self.enable_a2a_account) or
            (agent_name == "Transaction Agent" and self.enable_a2a_transaction) or
            (agent_name == "AI Money Coach" and self.enable_a2a_ai_coach) or
            (agent_name == "Product Info Agent" and self.enable_a2a_prodinfo) or
            (agent_name == "Escalation Agent" and self.enable_a2a_escalation)
        ) else "In-Process"
        
        yield ("", False, None, {
            "type": "thinking",
            "step": "routing",
            "message": f"{agent_name} selected ({agent_mode} Mode)",
            "agent_name": agent_name,
            "agent": agent_name,  # Add for Agent System Map compatibility
            "status": "in_progress",
            "timestamp": time.time()
        })
        
        # Route to the appropriate agent (PASS thread_id for continuity!)
        if agent_name == "AI Money Coach":
            # Route to AI Money Coach (A2A if enabled) - WITH THREAD ID
            response_text = await self.route_to_ai_money_coach(user_message, thread_id)
        
        elif agent_name == "Product Info Agent":
            # Route to Product Info (A2A if enabled) - WITH THREAD ID
            response_text = await self.route_to_prodinfo_agent(user_message, thread_id)
        
        elif agent_name == "Transaction Agent":
            # Route to Transaction Agent (A2A if enabled) - WITH THREAD ID
            response_text = await self.route_to_transaction_agent(user_message, thread_id)
        
        elif agent_name == "Payment Agent":
            # Route to Payment Agent (A2A if enabled) - WITH THREAD ID
            response_text = await self.route_to_payment_agent(user_message, thread_id)
        
        elif agent_name == "Escalation Agent":
            # Route to Escalation Agent (A2A if enabled) - WITH THREAD ID
            response_text = await self.route_to_escalation_agent(user_message, thread_id)
        
        else:
            # Route to Account Agent (A2A if enabled) - WITH THREAD ID
            response_text = await self.route_to_account_agent(user_message, thread_id)
        
        # Store conversation history for next turn
        self.last_routed_agent = agent_name
        self.last_user_message = user_message
        self.last_agent_response = response_text
        
        # Store agent in conversation state for continuation support
        from app.conversation_state_manager import get_conversation_state_manager
        if user_context and user_context.customer_id:
            state_manager = get_conversation_state_manager()
            # Create a proxy object that represents the A2A agent
            class A2AAgentProxy:
                def __init__(self, agent_name, a2a_url):
                    self.agent_name = agent_name
                    self.a2a_url = a2a_url
            
            proxy = A2AAgentProxy(agent_name, self._get_a2a_url_for_agent(agent_name))
            state_manager.set_active_agent(
                thread_id=thread_id or f"thread_{user_context.customer_id}",
                agent_name=agent_name,
                agent_instance=proxy,
                customer_id=user_context.customer_id
            )
            logger.info(f"✅ [STATE] Stored {agent_name} in conversation state for customer {user_context.customer_id}")
        
        # Mark routing as completed
        yield ("", False, None, {
            "type": "thinking",
            "step": "routing",
            "message": f"{agent_name} selected ({agent_mode} Mode)",
            "agent_name": agent_name,
            "agent": agent_name,  # Add for Agent System Map compatibility
            "status": "completed",
            "timestamp": time.time(),
            "duration": time.time() - start_time
        })
        
        # Emit MCP tools invoked step
        yield ("", False, None, {
            "type": "thinking",
            "step": "mcp_tools_invoked",
            "message": "MCP tools invoked",
            "agent_name": agent_name,
            "agent": agent_name,
            "status": "completed",
            "timestamp": time.time()
        })
        
        # Stream the response back FIRST (chunked for better UX)
        words = response_text.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            is_final = False  # Not final yet - completion event comes after
            yield (chunk, is_final, None, None)
        
        # Emit completion event to close thinking panel AFTER response is fully streamed
        yield ("", False, None, {
            "type": "thinking",
            "step": "generating",
            "message": "Response generated",
            "status": "completed",
            "timestamp": time.time(),
            "duration": time.time() - start_time
        })
        
        # Final yield with thread_id to signal end of stream
        yield ("", True, thread_id, None)

        # Track conversation in conversations/ folder
        if self.conversation_manager and thread_id:
            try:
                self.conversation_manager.add_message(thread_id, "user", user_message, azure_thread_id=thread_id)
                self.conversation_manager.add_message(thread_id, "assistant", response_text, azure_thread_id=thread_id)
                logger.info(f"✅ [CONVERSATION] Messages added to session {thread_id}")
            except Exception as e:
                logger.error(f"❌ Error adding messages to conversation: {e}", exc_info=True)
        
        # Log Q&A pair in question-answer/ folder
        try:
            from app.utils.conversation_logger import get_conversation_logger
            conv_logger = get_conversation_logger()
            conv_logger.log_qa_pair(
                session_id=thread_id or "no-thread",
                question=user_message,
                answer=response_text,
                agent_used=agent_name,
                duration_seconds=time.time() - start_time,
                customer_id=user_context.customer_id if user_context else None,
                user_email=user_context.entra_user_email if user_context else None
            )
        except Exception as e:
            logger.error(f"❌ Error logging Q&A pair: {e}", exc_info=True)
        



        duration = time.time() - start_time
        logger.info(f"[SUPERVISOR A2A STREAM] Stream completed | Duration: {duration:.2f}s")

    async def _try_cache_response(self, user_message: str, customer_id: str) -> str | None:
        """
        Try to answer query from cache (balance, transactions, account details, etc.)
        Returns cached response if available, otherwise None
        """
        if not self.cache_manager:
            logger.info("⚠️ [CACHE] No cache_manager available")
            return None
        
        message_lower = user_message.lower()
        logger.info(f"🔍 [CACHE] Checking cache for: {user_message}")
        
        # Balance queries
        if any(word in message_lower for word in ["balance", "how much money", "how much do i have"]):
            balance = await self.cache_manager.get_cached_data(customer_id, "balance")
            logger.info(f"🔍 [CACHE] Balance query - got balance: {balance}")
            if balance is not None and balance > 0:
                logger.info(f"✅ [CACHE HIT] Balance: {balance} THB")
                return f"Your current account balance is **{balance:,.2f} THB**."
            else:
                logger.info(f"❌ [CACHE MISS] Balance is {balance} (None or 0)")
        
        # Transaction queries
        elif any(word in message_lower for word in ["transaction", "history", "recent", "last"]):
            transactions = await self.cache_manager.get_cached_data(customer_id, "last_5_transactions")
            if transactions and len(transactions) > 0:
                # Parse how many transactions user wants
                import re
                count_match = re.search(r'last\s+(\d+)', message_lower)
                requested_count = int(count_match.group(1)) if count_match else 5
                requested_count = min(requested_count, len(transactions))  # Don't exceed available
                
                logger.info(f"✅ [CACHE HIT] Transactions: showing {requested_count} of {len(transactions)}")
                
                # Format as HTML table for frontend rendering
                response = "Here are your recent transactions:\n\n<table>\n<thead>\n"
                response += "<tr><th>Date</th><th>Description</th><th>Type</th><th>Amount</th><th>Recipient</th></tr>\n"
                response += "</thead>\n<tbody>\n"
                
                for txn in transactions[:requested_count]:
                    desc = txn.get("description", "N/A")
                    amount = txn.get("amount", 0)
                    timestamp = txn.get("timestamp", "N/A")
                    txn_type_raw = txn.get("type", "").lower()
                    
                    # Format date
                    date_str = timestamp.split('T')[0] if 'T' in timestamp else timestamp
                    
                    # Extract recipient name from description (e.g., "Transfer to Somchai Rattanakorn")
                    recipient_match = re.search(r'(?:to|from)\s+(.+?)(?:\s*$)', desc)
                    recipient = recipient_match.group(1) if recipient_match else "N/A"
                    
                    # Determine transaction type/emoji based on type field
                    if txn_type_raw == "outcome":
                        txn_type = "📤 Transfer"
                    else:  # income
                        txn_type = "📥 Income"
                    
                    response += f"<tr><td>{date_str}</td><td>{desc}</td><td>{txn_type}</td>"
                    response += f"<td>THB {abs(amount):,.2f}</td><td>{recipient}</td></tr>\n"
                
                response += "</tbody>\n</table>"
                return response.strip()
        
        # Account details
        elif any(word in message_lower for word in ["account number", "account details", "account info"]):
            account_details = await self.cache_manager.get_cached_data(customer_id, "account_details")
            if account_details:
                logger.info(f"✅ [CACHE HIT] Account details")
                response = f"**Account ID:** {account_details.get('id', 'N/A')}\n"
                response += f"**Account Holder:** {account_details.get('accountHolderFullName', 'N/A')}\n"
                response += f"**Balance:** {float(account_details.get('balance', 0)):,.2f} THB"
                return response
        
        # Limit queries (daily limit, transaction limit, etc.)
        elif any(word in message_lower for word in ["limit", "daily limit", "transaction limit", "transfer limit"]):
            limits = await self.cache_manager.get_cached_data(customer_id, "limits")
            if limits:
                logger.info(f"✅ [CACHE HIT] Limits")
                response = "Your account limits:\n\n"
                response += f"**Daily Transaction Limit:** {limits.get('daily_limit', 'N/A'):,.2f} THB\n"
                response += f"**Per Transaction Limit:** {limits.get('per_transaction_limit', 'N/A'):,.2f} THB"
                return response
        
        return None

    def _determine_cache_agent(self, message_lower: str) -> str:
        """Determine which agent would have been called (for cache hit logging)"""
        if any(word in message_lower for word in ["transaction", "history"]):
            return "TransactionAgent"
        elif any(word in message_lower for word in ["limit"]):
            return "AccountAgent"  # Limits are handled by Account Agent
        return "AccountAgent"

    async def route_to_escalation_comms_agent(
        self, 
        ticket_id: str, 
        subject: str, 
        description: str, 
        priority: str = "medium", 
        customer_email: str = None
    ) -> str:
        """Route ticket creation to EscalationComms Agent"""
        from app.observability.banking_telemetry import get_banking_telemetry
        
        self.routed_agent_name = "EscalationCommsAgent"
        logger.info(f"🔥 SupervisorAgent routing to EscalationComms: {subject}")
        
        try:
            telemetry = get_banking_telemetry()
            
            if self.escalation_comms_agent_old:
                # Build agent
                af_escalation_agent = await self.escalation_comms_agent_old.build_af_agent(thread_id=None)
                
                # Create ticket message
                ticket_message = f"Create support ticket: ID={ticket_id}, Subject='{subject}', Description='{description}', Priority={priority}, CustomerEmail={customer_email}"
                
                # Run agent
                response = await af_escalation_agent.run(ticket_message)
                
                # Track decision
                with telemetry.track_agent_decision("EscalationCommsAgent", ticket_message, None) as decision:
                    decision.set_result("success", "Support ticket created")
                
                return response.text
            else:
                return f"I've created support ticket **{ticket_id}** for your request. Our team will contact you at {customer_email} shortly."
        
        except Exception as e:
            logger.error(f"❌ Error in route_to_escalation_comms_agent: {e}", exc_info=True)
            return f"I encountered an error while creating your support ticket: {str(e)}"


# Helper function to create supervisor with A2A support
def create_supervisor_with_a2a(
    # A2A URLs - UC1
    account_agent_a2a_url: str | None = None,
    transaction_agent_a2a_url: str | None = None,
    payment_agent_a2a_url: str | None = None,
    # A2A URLs - UC2/UC3
    prodinfo_faq_agent_a2a_url: str | None = None,
    ai_money_coach_agent_a2a_url: str | None = None,
    escalation_comms_agent_a2a_url: str | None = None,
    # Feature flags
    enable_a2a_account: bool = False,
    enable_a2a_transaction: bool = False,
    enable_a2a_payment: bool = False,
    enable_a2a_prodinfo: bool = False,
    enable_a2a_ai_coach: bool = False,
    enable_a2a_escalation: bool = False,
    **kwargs
) -> SupervisorAgentA2A:
    """
    Factory function to create SupervisorAgentA2A with feature flag support
    
    Args:
        *_a2a_url: A2A endpoint URLs for specialist agents
        enable_a2a_*: Feature flags to enable A2A for each agent
        **kwargs: OLD agent instances and other supervisor dependencies
    
    Returns:
        SupervisorAgentA2A instance
    """
    supervisor = SupervisorAgentA2A(
        # A2A URLs - UC1
        account_agent_a2a_url=account_agent_a2a_url,
        transaction_agent_a2a_url=transaction_agent_a2a_url,
        payment_agent_a2a_url=payment_agent_a2a_url,
        # A2A URLs - UC2/UC3
        prodinfo_faq_agent_a2a_url=prodinfo_faq_agent_a2a_url,
        ai_money_coach_agent_a2a_url=ai_money_coach_agent_a2a_url,
        escalation_comms_agent_a2a_url=escalation_comms_agent_a2a_url,
        # Feature flags
        enable_a2a_account=enable_a2a_account,
        enable_a2a_transaction=enable_a2a_transaction,
        enable_a2a_payment=enable_a2a_payment,
        enable_a2a_prodinfo=enable_a2a_prodinfo,
        enable_a2a_ai_coach=enable_a2a_ai_coach,
        enable_a2a_escalation=enable_a2a_escalation,
        **kwargs
    )
    
    return supervisor
