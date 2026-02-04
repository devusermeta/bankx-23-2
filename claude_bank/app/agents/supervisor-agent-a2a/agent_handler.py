"""
Supervisor Agent Handler

Routes customer queries to specialized agents via A2A protocol.
Main entry point for all BankX customer interactions.

CACHE-FIRST STRATEGY:
- For READ queries (balance, transactions, limits) → Check cache first
- For WRITE queries (transfers, payments) → Always route to live agents
- Uses gpt-4.1-mini for query classification and response formatting
"""

import asyncio
import httpx
import logging
import json
import sys
from datetime import datetime
from typing import AsyncIterator
from pathlib import Path
from azure.identity import AzureCliCredential
from openai import AsyncAzureOpenAI

from agent_framework import ChatAgent
from agent_framework.azure import AzureAIClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

from config import (
    AZURE_AI_PROJECT_ENDPOINT,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_MINI_DEPLOYMENT_NAME,
    SUPERVISOR_AGENT_NAME,
    SUPERVISOR_AGENT_VERSION,
    SUPERVISOR_AGENT_MODEL_DEPLOYMENT,
    ACCOUNT_AGENT_A2A_URL,
    TRANSACTION_AGENT_A2A_URL,
    PAYMENT_AGENT_A2A_URL,
    PRODINFO_FAQ_AGENT_A2A_URL,
    AI_MONEY_COACH_AGENT_A2A_URL,
    ESCALATION_AGENT_A2A_URL,
)

# Add path to copilot cache module
copilot_path = Path(__file__).parent.parent.parent.parent / "copilot" / "app"
sys.path.insert(0, str(copilot_path))

try:
    from cache.user_cache import get_cache_manager
    CACHE_AVAILABLE = True
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("✅ Cache manager imported successfully")
except ImportError as e:
    CACHE_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"⚠️ Cache manager not available: {e}")

logger = logging.getLogger(__name__)


class SupervisorAgentHandler:
    """
    Handler for Supervisor Agent - Routes queries to specialist agents
    
    Architecture:
    - Uses Azure AI Foundry ChatAgent for routing decisions
    - Routes to 6 specialist agents via A2A HTTP calls:
      1. AccountAgent (port 9001)
      2. TransactionAgent (port 9002)
      3. PaymentAgent (port 9003)
      4. ProdInfoFAQAgent (port 9004)
      5. AIMoneyCoachAgent (port 9005)
      6. EscalationAgent (port 9006)
    """

    def __init__(self):
        """Initialize handler with cache-first strategy"""
        self.credential = AzureCliCredential()
        self.project_client = None
        self.instructions = self._load_instructions()
        self._cached_agents: dict[str, ChatAgent] = {}
        self._mini_client: AsyncAzureOpenAI | None = None
        
        # Initialize cache manager (shared with copilot backend)
        if CACHE_AVAILABLE:
            try:
                self.cache_manager = get_cache_manager()
                logger.info("✅ Cache manager initialized - cache-first strategy enabled")
            except Exception as e:
                logger.warning(f"⚠️ Cache manager init failed: {e} - will route all queries to agents")
                self.cache_manager = None
        else:
            self.cache_manager = None
            logger.warning("⚠️ Cache not available - will route all queries to agents")
        
        # A2A endpoint mapping
        self.agent_urls = {
            "account": ACCOUNT_AGENT_A2A_URL,
            "transaction": TRANSACTION_AGENT_A2A_URL,
            "payment": PAYMENT_AGENT_A2A_URL,
            "prodinfo": PRODINFO_FAQ_AGENT_A2A_URL,
            "aicoach": AI_MONEY_COACH_AGENT_A2A_URL,
            "escalation": ESCALATION_AGENT_A2A_URL,
        }
        
        logger.info("SupervisorAgentHandler initialized")
        logger.info(f"Specialist agent endpoints configured: {len(self.agent_urls)}")

    def _load_instructions(self) -> str:
        """Load routing instructions from markdown file"""
        try:
            with open("prompts/supervisor_agent.md", "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load instructions: {e}")
            return "You are a Supervisor Agent. Route queries to appropriate specialist agents."

    async def _route_to_specialist(
        self,
        agent_name: str,
        agent_url: str,
        user_message: str,
        customer_id: str,
        thread_id: str,
        user_mail: str | None = None,
        stream: bool = False,
    ) -> str:
        """
        Route query to specialist agent via A2A protocol
        
        Args:
            agent_name: Name of specialist agent
            agent_url: A2A endpoint URL
            user_message: User's query
            customer_id: Customer identifier
            thread_id: Thread identifier
            user_mail: Customer email (optional)
            stream: Whether to stream response
        
        Returns:
            Agent's response
        """
        logger.info(f"🎯 Routing to {agent_name} at {agent_url}")
        
        try:
            # Build A2A request
            a2a_request = {
                "messages": [
                    {"role": "user", "content": user_message}
                ],
                "customer_id": customer_id,
                "thread_id": thread_id,
                "stream": stream,
            }
            
            # Add optional parameters
            if user_mail:
                a2a_request["user_mail"] = user_mail
            
            # Call specialist agent
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{agent_url}/a2a/invoke",
                    json=a2a_request,
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code == 200:
                    result = response.json()
                    agent_response = result.get("content", "")
                    logger.info(f"✅ Received response from {agent_name} ({len(agent_response)} chars)")
                    return agent_response
                else:
                    error_msg = f"A2A request failed with status {response.status_code}"
                    logger.error(f"❌ {error_msg}: {response.text}")
                    return f"I couldn't connect to our {agent_name.lower()} service. Please try again later."
        
        except httpx.TimeoutException:
            logger.error(f"❌ Request timeout for {agent_name}")
            return f"The request is taking too long. Please try again."
        
        except Exception as e:
            logger.error(f"❌ Error routing to {agent_name}: {e}", exc_info=True)
            return f"I encountered an error processing your request. Please try again."

    async def _determine_routing(
        self,
        user_message: str,
        customer_id: str,
        thread_id: str,
    ) -> str:
        """
        Use Azure AI Foundry persistent agent to determine which specialist agent to route to
        
        Args:
            user_message: User's query
            customer_id: Customer identifier
            thread_id: Thread identifier
        
        Returns:
            Agent name to route to (account, transaction, payment, prodinfo, aicoach, escalation)
        """
        try:
            # Get or create persistent agent in Azure AI Foundry (cached per thread)
            if thread_id in self._cached_agents:
                agent = self._cached_agents[thread_id]
                logger.debug(f"Using cached Supervisor Agent for thread {thread_id}")
            else:
                # Initialize project client if not already done
                if not self.project_client:
                    self.project_client = AIProjectClient(
                        endpoint=AZURE_AI_PROJECT_ENDPOINT,
                        credential=self.credential
                    )
                
                # Create Azure AI Client that references the EXISTING Foundry agent
                azure_client = AzureAIClient(
                    project_client=self.project_client,
                    agent_name=SUPERVISOR_AGENT_NAME,
                    agent_version=SUPERVISOR_AGENT_VERSION,
                )
                
                # Create routing instructions
                routing_instructions = f"""
{self.instructions}

## ROUTING TASK

Analyze this query and respond with ONLY the agent name to route to.
Valid agent names: account, transaction, payment, prodinfo, aicoach, escalation

Customer ID: {customer_id}
Query: "{{user_message}}"

Respond with ONE WORD ONLY - the agent name (lowercase).
"""
                
                # Create persistent ChatAgent with MCP tools added dynamically
                agent = azure_client.create_agent(
                    name=SUPERVISOR_AGENT_NAME,
                    tools=[],  # No tools needed for routing
                    instructions=routing_instructions,
                )
                
                # Cache agent per thread for thread tracking in Azure
                self._cached_agents[thread_id] = agent
                logger.info(f"Created persistent Supervisor Agent in Azure AI Foundry for thread {thread_id}")
            
            # Get routing decision
            result = await agent.run(user_message)
            agent_name = result.text.strip().lower()
            
            # Validate agent name
            valid_agents = list(self.agent_urls.keys())
            if agent_name not in valid_agents:
                logger.warning(f"Invalid agent name '{agent_name}', defaulting to prodinfo")
                agent_name = "prodinfo"
            
            logger.info(f"🤖 Routing decision: {agent_name}")
            return agent_name
        
        except Exception as e:
            logger.error(f"Error determining routing: {e}", exc_info=True)
            # Default to prodinfo agent (safest fallback)
            return "prodinfo"

    async def _get_mini_llm_client(self) -> AsyncAzureOpenAI | None:
        """Get or create Azure OpenAI client for gpt-4.1-mini (used for cache classification)"""
        if self._mini_client:
            return self._mini_client
        
        if not AZURE_OPENAI_ENDPOINT:
            logger.warning("⚠️ AZURE_OPENAI_ENDPOINT not configured - cache formatting disabled")
            return None
        
        try:
            token = self.credential.get_token("https://cognitiveservices.azure.com/.default")
            self._mini_client = AsyncAzureOpenAI(
                azure_endpoint=AZURE_OPENAI_ENDPOINT,
                api_version=AZURE_OPENAI_API_VERSION,
                api_key=token.token
            )
            return self._mini_client
        except Exception as e:
            logger.error(f"❌ Failed to create Azure OpenAI client: {e}")
            return None

    async def _classify_query_with_llm(self, user_query: str) -> dict:
        """
        Use gpt-4.1-mini to dynamically classify if query can be answered from cache.
        
        Args:
            user_query: User's question
        
        Returns:
            dict with keys: can_use_cache (bool), data_type (str|None), reasoning (str)
        """
        try:
            client = await self._get_mini_llm_client()
            if not client:
                return {"can_use_cache": False, "data_type": None, "reasoning": "LLM client unavailable"}
            
            system_prompt = """You are a query classifier for a banking system. Determine if the user's query can be answered using cached data.

CRITICAL RULE: Cache is ONLY for READ operations. NEVER use cache for:
❌ Transfers, payments, or money movements (e.g., "transfer money", "send payment", "pay someone")
❌ Any action that modifies account data
❌ Creating, updating, or deleting anything
These MUST go to live agents for real-time processing.

✅ Cache CAN be used ONLY for READ queries:
1. balance - current account balance, available funds
2. account_details - account info, holder name, account number, currency, activation date, status
3. transactions - last 5 transactions (recent payments, spending, transaction history)
4. beneficiaries - saved recipients/contacts for payments (up to 10)
5. limits - transaction limits (per-transaction, daily, monthly) with remaining amounts

Respond ONLY with valid JSON in this exact format:
{
  "can_use_cache": true,
  "data_type": "transactions",
  "reasoning": "Query asks about recent transaction history"
}

If query is a WRITE operation (transfer, payment, action), respond:
{
  "can_use_cache": false,
  "data_type": null,
  "reasoning": "Write operation - must use live agent"
}"""
            
            user_prompt = f"""Current user query: "{user_query}"

Can this query be answered using cached data? Which type?"""
            
            response = await client.chat.completions.create(
                model=AZURE_OPENAI_MINI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"🤖 [LLM CLASSIFY] '{user_query[:50]}...' → Cache: {result.get('can_use_cache')}, Type: {result.get('data_type')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ [LLM CLASSIFY] Failed to classify query: {e}")
            return {"can_use_cache": False, "data_type": None, "reasoning": f"Classification error: {e}"}

    async def _format_with_llm(self, user_query: str, cached_data: dict, data_type: str) -> str | None:
        """
        Use gpt-4.1-mini to format cached data based on user query.
        
        Args:
            user_query: Original user question
            cached_data: Relevant cached data (dict)
            data_type: Type of data (balance, transactions, account_details, beneficiaries, limits)
        
        Returns:
            Formatted response or None if LLM fails
        """
        try:
            client = await self._get_mini_llm_client()
            if not client:
                return None
            
            # Build context-aware system prompt based on data_type
            if data_type == "balance":
                system_prompt = """You are a banking assistant. Answer the user's balance question using ONLY the provided data.
Be concise and accurate. Format currency as THB with commas (e.g., THB 89,850.00).

IMPORTANT:
- User asked ONLY for balance information
- Do NOT mention transactions unless user specifically asked for them
- Simply provide the balance in a clear, professional format
- Do NOT add polite closings like "Happy to help!", "Feel free to ask", or "Is there anything else?"
- Answer ONLY what was asked - be direct and to-the-point"""
                
                user_prompt = f"""User question: {user_query}

Available data:
{json.dumps(cached_data, indent=2)}

Provide the account balance clearly."""

            elif data_type == "transactions":
                system_prompt = """You are a banking assistant. Answer the user's transaction question using ONLY the provided data.
Be concise and accurate. Format currency as THB with commas. Format dates as YYYY-MM-DD HH:MM.

🚨 MANDATORY: When showing 2 or more transactions, you MUST generate an HTML table (NOT markdown).

Use this EXACT format for multiple transactions:

Here are your transactions:

<table>
<thead>
<tr><th>Date</th><th>Description</th><th>Type</th><th>Amount</th><th>Recipient</th></tr>
</thead>
<tbody>
<tr><td>2025-11-18 21:03</td><td>Transfer to Apichat</td><td>📤 Transfer</td><td>THB 1,000.00</td><td>Apichat</td></tr>
<tr><td>2025-11-18 00:16</td><td>Transfer to Somchai</td><td>📤 Transfer</td><td>THB 1,000.00</td><td>Somchai</td></tr>
</tbody>
</table>

CRITICAL RULES:
- Use simple HTML <table> tags with NO inline styles - frontend CSS will handle styling
- Use 📥 emoji for income, 📤 emoji for transfers
- NEVER use numbered lists (1. 2. 3.) for multiple transactions
- Each transaction must be in its own <tr> row with <td> cells
- Format amounts as "THB X,XXX.XX" with commas
- Keep HTML minimal for fast generation

🚨 CRITICAL: RESPECT THE EXACT NUMBER REQUESTED BY USER 🚨
- If user asks "last 2 transactions" → Show ONLY 2 rows
- If user asks "last 3 transactions" → Show ONLY 3 rows
- If user asks "last transactions" (no number) → Show up to 5 rows
- NEVER show more transactions than specifically requested
- Count carefully and stop when you reach the requested number"""
                
                user_prompt = f"""User question: {user_query}

Available data:
{json.dumps(cached_data, indent=2)}

IMPORTANT: 
1. Look at the user's question carefully to see how many transactions they want
2. Show EXACTLY that number of transactions (e.g., "last 2" = show only 2 rows, not 5)
3. Every row MUST have data in ALL columns (Date, Description, Type, Amount, Recipient)
4. Do not leave any cells empty"""

            else:  # account_details, beneficiaries, limits, etc.
                system_prompt = """You are a banking assistant. Answer the user's question using ONLY the provided data.
Be concise and accurate. Format currency as THB with commas. Format dates as YYYY-MM-DD HH:MM.
If the data doesn't contain enough information to answer, say so clearly."""
                
                user_prompt = f"""User question: {user_query}

Available data:
{json.dumps(cached_data, indent=2)}"""
            
            response = await client.chat.completions.create(
                model=AZURE_OPENAI_MINI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,  # Deterministic for data formatting
                max_tokens=1500  # Allow full HTML tables
            )
            
            answer = response.choices[0].message.content
            logger.info(f"✅ [LLM FORMAT] Formatted {data_type} with gpt-4.1-mini")
            return answer
            
        except Exception as e:
            logger.error(f"❌ [LLM FORMAT] Failed to format with LLM: {e}")
            return None

    async def _try_cache_response(self, user_message: str, customer_id: str) -> str | None:
        """
        Use LLM to dynamically classify query and try to answer from cache.
        
        Returns cached response if available and fresh, otherwise None.
        """
        if not self.cache_manager:
            return None
        
        # Use LLM to classify the query
        classification = await self._classify_query_with_llm(user_message)
        
        if not classification.get("can_use_cache"):
            logger.info(f"🔍 [CACHE] Query not cacheable: {classification.get('reasoning')}")
            return None
        
        data_type = classification.get("data_type")
        if not data_type:
            return None
        
        logger.info(f"✅ [CACHE] Query classified as '{data_type}' - checking cache...")
        
        try:
            # Try to get cached data based on classification
            if data_type == "balance":
                balance = await self.cache_manager.get_cached_data(customer_id, "balance")
                if balance is not None and balance > 0:
                    logger.info(f"✅ [CACHE HIT] Balance query answered from cache: {balance} THB")
                    
                    llm_response = await self._format_with_llm(
                        user_query=user_message,
                        cached_data={"balance": balance, "currency": "THB"},
                        data_type="balance"
                    )
                    
                    if llm_response:
                        return llm_response
                    
                    # Fallback format
                    return f"Your current account balance is **{balance:,.2f} THB**."
                else:
                    logger.info(f"⚠️ [CACHE MISS] Balance is {balance}, forcing agent call")
                    return None
            
            elif data_type == "account_details":
                account_details = await self.cache_manager.get_cached_data(customer_id, "account_details")
                if account_details:
                    logger.info(f"✅ [CACHE HIT] Account details from cache")
                    
                    llm_response = await self._format_with_llm(
                        user_query=user_message,
                        cached_data={"account": account_details},
                        data_type="account_details"
                    )
                    
                    if llm_response:
                        return llm_response
            
            elif data_type == "transactions":
                transactions = await self.cache_manager.get_cached_data(customer_id, "last_5_transactions")
                if transactions:
                    logger.info(f"✅ [CACHE HIT] Transaction query from cache: {len(transactions)} transactions")
                    
                    llm_response = await self._format_with_llm(
                        user_query=user_message,
                        cached_data={"transactions": transactions},
                        data_type="transactions"
                    )
                    
                    if llm_response:
                        return llm_response
            
            elif data_type == "beneficiaries":
                beneficiaries = await self.cache_manager.get_cached_data(customer_id, "contacts")
                if beneficiaries:
                    logger.info(f"✅ [CACHE HIT] Beneficiaries from cache: {len(beneficiaries)} contacts")
                    
                    llm_response = await self._format_with_llm(
                        user_query=user_message,
                        cached_data={"beneficiaries": beneficiaries},
                        data_type="beneficiaries"
                    )
                    
                    if llm_response:
                        return llm_response
            
            elif data_type == "limits":
                limits = await self.cache_manager.get_cached_data(customer_id, "limits")
                if limits:
                    logger.info(f"✅ [CACHE HIT] Limits from cache")
                    
                    llm_response = await self._format_with_llm(
                        user_query=user_message,
                        cached_data={"limits": limits},
                        data_type="limits"
                    )
                    
                    if llm_response:
                        return llm_response
        
        except Exception as e:
            logger.error(f"❌ [CACHE] Error accessing cache: {e}")
        
        logger.info(f"⚠️ [CACHE MISS] No cached data for {data_type}")
        return None

    async def process_message(
        self,
        messages: list,
        thread_id: str,
        customer_id: str,
        user_mail: str | None = None,
        stream: bool = False,
    ) -> AsyncIterator[str]:
        """
        Process user message and route to appropriate specialist agent
        
        Args:
            messages: Conversation messages
            thread_id: Thread identifier
            customer_id: Customer identifier
            user_mail: Customer email (optional)
            stream: Whether to stream response
        
        Returns:
            AsyncIterator[str]: Response from specialist agent
        """
        try:
            # Extract user message
            if not messages:
                async def error_gen():
                    yield "No message provided."
                return error_gen()
            
            # Get last user message
            user_message = messages[-1].get("content", "") if isinstance(messages[-1], dict) else messages[-1].content
            
            logger.info(f"📥 Supervisor received message: {user_message[:100]}...")
            
            # CACHE-FIRST STRATEGY: Try cache before routing to agents
            if self.cache_manager:
                logger.info("🔍 [CACHE-FIRST] Checking if query can be answered from cache...")
                cached_response = await self._try_cache_response(user_message, customer_id)
                
                if cached_response:
                    logger.info("✅ [CACHE HIT] Returning cached response - NO agent call needed!")
                    
                    async def cache_response_generator():
                        yield cached_response
                    
                    return cache_response_generator()
                else:
                    logger.info("⚠️ [CACHE MISS] Routing to specialist agent...")
            else:
                logger.info("⚠️ [NO CACHE] Routing to specialist agent...")
            
            # Determine routing
            agent_name = await self._determine_routing(user_message, customer_id, thread_id)
            agent_url = self.agent_urls.get(agent_name)
            
            if not agent_url:
                logger.error(f"No URL configured for agent: {agent_name}")
                async def error_gen():
                    yield "Service configuration error. Please contact support."
                return error_gen()
            
            # Route to specialist agent
            response = await self._route_to_specialist(
                agent_name=agent_name,
                agent_url=agent_url,
                user_message=user_message,
                customer_id=customer_id,
                thread_id=thread_id,
                user_mail=user_mail,
                stream=stream,
            )
            
            # Return response
            async def response_generator():
                yield response
            
            return response_generator()
        
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            async def error_generator():
                yield f"I encountered an error: {str(e)}"
            
            return error_generator()
