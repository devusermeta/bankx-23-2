from typing import AsyncGenerator
from agent_framework import ChatAgent
from agent_framework.azure import AzureAIClient
from azure.ai.projects import AIProjectClient
from app.agents.foundry.account_agent_foundry import AccountAgent
from app.agents.foundry.transaction_agent_foundry import TransactionAgent
from app.agents.foundry.payment_agent_foundry import PaymentAgent
from app.agents.foundry.escalation_comms_agent_foundry import EscalationCommsAgent

# UC2 & UC3: ACTIVE VERSION - Using native file search (Azure AI Foundry vector store)
from app.agents.foundry.prodinfo_faq_agent_knowledge_base_foundry import ProdInfoFAQAgentKnowledgeBase 
from app.agents.foundry.ai_money_coach_agent_knowledge_base_foundry import AIMoneyCoachKnowledgeBaseAgent

# UC2 & UC3: OLD VERSION - Using Azure AI Search RAG via MCP servers (COMMENTED OUT)
# from app.agents.foundry.prodinfo_faq_agent_foundry import ProdInfoFAQAgent
# from app.agents.foundry.ai_money_coach_agent_foundry import AIMoneyCoachAgent

from app.config.azure_credential import get_azure_credential_async
from app.config.settings import settings
from app.cache.user_cache import get_cache_manager
from app.conversation_state_manager import get_conversation_state_manager
import sys
from pathlib import Path
import logging
import re
import json

logger = logging.getLogger(__name__)

# Add lib directory to path for conversation_manager module
try:
    # Detect environment: Docker (/app/lib) or Local (conversations/)
    import os
    if os.path.exists("/.dockerenv") or os.path.exists("/app/lib"):
        # Docker environment
        lib_path = "/app/lib"
    else:
        # Local development - use project root conversations directory
        lib_path = str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "conversations")
    
    logger.info(f"📂 Lib path: {lib_path}")
    
    # Verify the path exists
    if not Path(lib_path).exists():
        raise FileNotFoundError(f"Lib directory not found at: {lib_path}")
    
    if lib_path not in sys.path:
        sys.path.insert(0, lib_path)  # Insert at beginning for priority
    
    # Import conversation manager dynamically to avoid static import issues
    import importlib
    conv_mod = importlib.import_module("conversation_manager")
    get_conversation_manager = getattr(conv_mod, "get_conversation_manager")
    CONVERSATION_STORAGE_ENABLED = True
    logger.info(f"✅ Conversation storage enabled. Module path: {lib_path}")
    
except ImportError as e:
    logger.warning(f"⚠️ Conversation manager import failed: {e}")
    CONVERSATION_STORAGE_ENABLED = False
    get_conversation_manager = lambda: None
except FileNotFoundError as e:
    logger.warning(f"⚠️ Conversations directory not found: {e}")
    CONVERSATION_STORAGE_ENABLED = False
    get_conversation_manager = lambda: None
except Exception as e:
    logger.error(f"❌ Unexpected error loading conversation manager: {e}")
    CONVERSATION_STORAGE_ENABLED = False
    get_conversation_manager = lambda: None

class SupervisorAgent :
    """ this agent is used in agent-as-tool orchestration as supervisor agent to decide which tool/agent to use.
    """
    instructions = """
      You are a banking customer support agent triaging customer requests about their banking account, movements, payments, product information, and personal finance advice.
      You have to evaluate the whole conversation with the customer and forward it to the appropriate agent based on triage rules.
      Once you got a response from an agent use it to provide the answer to the customer.
      
      CRITICAL RULES:
      - Do NOT add follow-up questions like "Is there anything else you would like to know?"
      - Do NOT offer additional help or suggestions UNLESS the agent explicitly asks a question or offers an option
      - Do NOT add polite closings like "Happy to help!", "Feel free to ask", "Let me know if you need anything else"
      - Be concise and to-the-point - answer ONLY what was asked
      - Pass through agent responses EXACTLY as received - do not modify or summarize
      - NEVER make up or hallucinate data
      - If a tool/agent has a technical failure or exception, tell the user "I couldn't retrieve that information right now"
      - If an agent says they don't have information and offers alternatives (like ticket creation), pass that response through unchanged
      - ONLY use data returned by tools/agents - do NOT invent transactions, amounts, dates, or names
      
      SENSITIVE DATA QUERIES (CRITICAL - SHORT RESPONSES ONLY):
      When users ask for PASSWORDS, PINs, CVVs, OTPs, or other authentication credentials:
      - Give a SHORT, DIRECT rejection: "I cannot assist with account password-related questions."
      - Do NOT suggest "Forgot Password" option
      - Do NOT suggest contacting support
      - Do NOT suggest going to login page
      - Do NOT offer any help or alternatives
      - Just state you cannot help with that type of query and STOP
      - Examples of sensitive queries to reject:
        * "What is my password?" → "I cannot assist with account password-related questions."
        * "What is my PIN?" → "I cannot assist with PIN-related questions."
        * "What is my CVV?" → "I cannot assist with card security code queries."
        * "Show me my OTP" → "I cannot assist with authentication code queries."
      
      CONTEXT AWARENESS FOR ONGOING PROCESSES (CRITICAL CONFIRMATION HANDLING):
      - **Payment Confirmations**: If user responds with confirmations like "yes", "confirm", "proceed", "ok", "sure":
        * Check previous assistant message
        * If it contained "PAYMENT CONFIRMATION REQUIRED" or payment details, this is a PAYMENT CONFIRMATION
        * Route back to PaymentAgent to process the confirmed payment
        * NEVER process payments without routing to PaymentAgent with confirmation context
      
      - **Ticket Confirmations**: If user responds with confirmations like "yes", "confirm", "proceed", "ok", "sure":
        * Check previous assistant message
        * If it contained "Would you like me to create a support ticket", this is a TICKET CONFIRMATION
        * DO NOT route to ProdInfoFAQ or AIMoneyCoach - they have no ticket creation tools
        * Instead, YOU must create the ticket yourself by calling route_to_escalation_comms_agent
      
      - **General Confirmation Routing**: 
        * If user provides additional information requested by an agent (like account numbers, amounts), route back to the requesting agent
        * Always consider the conversation context when deciding which agent to use
        * Preserve confirmation state when routing to ensure agents know user has confirmed
      
      TICKET CREATION FLOW (STRICT CONFIRMATION):
      - If ProdInfoFAQAgent or AIMoneyCoachAgent says "Would you like me to create a support ticket", pass this question to the user UNCHANGED
      - WAIT for user's explicit response - DO NOT assume confirmation
      - When user responds with confirmation (yes/confirm/sure/okay/please/create) to a ticket offer:
        * Verify this is an explicit confirmation, not a general acknowledgment
        * Generate ticket ID in format TKT-YYYY-HHMMSS (e.g., TKT-2025-111545)
        * Determine subject from previous conversation (e.g., "Credit card products inquiry")
        * Call route_to_escalation_comms_agent with: ticket_id, subject, description, priority="medium"
        * DO NOT pass customer_email - it will be automatically extracted from the authenticated user context
      - The EscalationComms agent will create the ticket and confirm to user
      - If user response is ambiguous, ask for clarification: "Just to confirm - would you like me to create a support ticket?"
      
      # Triage rules
      
      ## UC1 - Financial Operations (STRICT CONFIRMATION REQUIRED)
      - If the user request is related to bank account information like account balance, payment methods, cards, beneficiaries book, or ACCOUNT LIMITS (daily limit, transaction limit, transfer limit), you should route the request to AccountAgent.
      - If the user request is related to banking movements and payments history, you should route the request to TransactionHistoryAgent.
      - **PAYMENTS (MANDATORY CONFIRMATION)**: If the user request is related to initiate a payment request, upload a bill or invoice image for payment or manage an on-going payment process, you should route the request to PaymentAgent.
        * PaymentAgent will ask for confirmation before processing ANY payment
        * If user provides confirmation responses (yes/confirm/proceed/ok/sure) after a payment confirmation request, route to PaymentAgent with confirmation context
        * NEVER allow payment processing without explicit user confirmation
        * If previous message contained "PAYMENT CONFIRMATION REQUIRED", the current "yes" is a payment confirmation
      
      ## UC2 - Product Information & FAQ
      - If the user asks about BankX PRODUCTS (current account, savings account, fixed deposits, TD Bonus, loans), product FEATURES, INTEREST RATES, FEES, ELIGIBILITY, or BANKING TERMS, route to ProdInfoFAQAgent.
      - Examples: "What are the interest rates?", "How do I open a savings account?", "What is the minimum balance?", "Compare current vs savings account"
      
      ## UC3 - Personal Finance Coaching
      - If the user asks for PERSONAL FINANCE ADVICE, DEBT MANAGEMENT, BUDGETING, SAVINGS STRATEGIES, INVESTMENT GUIDANCE, FINANCIAL PLANNING, DEBT EDUCATION (good vs bad debt), BORROWING DECISIONS, EMERGENCY FUNDS, or FINANCIAL MINDSET, route to AIMoneyCoachAgent.
      - Examples: "How do I pay off debt?", "What's the best way to save?", "I have 3 credit cards, which to pay first?", "How to build an emergency fund?", "When is borrowing money acceptable?", "Should I take a loan?", "Is this good debt or bad debt?"
      - This agent provides advice based ONLY on the "Debt-Free to Financial Freedom" book
      
      ## Fallback
      - If the user request is not related to account, transactions, payments, product information, or personal finance you should respond to the user that you are not able to help with the request.

    """
    name = "SupervisorAgent"
    description = "This agent triages customer requests and routes them to the appropriate agent."

    def __init__(self, 
                 foundry_project_client: AIProjectClient, 
                 chat_deployment_name:str,
                 account_agent: AccountAgent,
                 transaction_agent: TransactionAgent,
                 payment_agent: PaymentAgent,
                 escalation_comms_agent: EscalationCommsAgent,
                 # ACTIVE: Using native file search agents
                 prodinfo_faq_agent: ProdInfoFAQAgentKnowledgeBase,
                 ai_money_coach_agent: AIMoneyCoachKnowledgeBaseAgent,
                 # OLD VERSION (comment out above and uncomment below to switch back):
                 # prodinfo_faq_agent: ProdInfoFAQAgent,
                 # ai_money_coach_agent: AIMoneyCoachAgent,
                 foundry_endpoint: str,
                 agent_id: str = None,
                 agent_name: str = None,
                 agent_version: str = None
                                ):
      self.account_agent = account_agent
      self.transaction_agent = transaction_agent  
      self.payment_agent = payment_agent
      self.escalation_comms_agent = escalation_comms_agent
      self.prodinfo_faq_agent = prodinfo_faq_agent
      self.ai_money_coach_agent = ai_money_coach_agent
      self.foundry_project_client = foundry_project_client
      self.foundry_endpoint = foundry_endpoint
      
      # Support both old agent_id and new name:version format
      if agent_name and agent_version:
          self.agent_name = agent_name
          self.agent_version = agent_version
      elif agent_id:
          if ":" in agent_id:
              parts = agent_id.split(":", 1)
              self.agent_name = parts[0]
              self.agent_version = parts[1]
          else:
              raise ValueError(f"Old agent_id format '{agent_id}' not supported. Use agent_name and agent_version instead.")
      else:
          raise ValueError("Either (agent_name + agent_version) or agent_id must be provided")
      
      self.chat_deployment_name = chat_deployment_name
      
      # Initialize conversation manager
      self.conversation_manager = get_conversation_manager() if CONVERSATION_STORAGE_ENABLED else None
      self.current_session_id = None
      self.last_active_thread = None  # Track thread transitions
      self.current_thread = None  # Initialize current thread
      self.routed_agent_name = None  # Track which specialist agent was selected
      self.pending_routing_events = []  # Store routing events to be emitted (now plural - can have multiple)
      
      # Cache the built ChatAgent to avoid rebuilding on every request
      self._cached_chat_agent = None
      self._cached_thread_id = None
      
      # Initialize cache manager
      self.cache_manager = get_cache_manager()
      
      # Initialize conversation state manager for multi-turn conversations
      self.state_manager = get_conversation_state_manager()
      
      # Initialize Azure OpenAI client for cache formatting
      self._mini_client = None

    async def _get_mini_llm_client(self):
        """Get or create Azure OpenAI client for lightweight formatting tasks"""
        if self._mini_client is None:
            from openai import AsyncAzureOpenAI
            from app.config.azure_credential import get_azure_credential_async
            
            credential = await get_azure_credential_async()
            token = await credential.get_token("https://cognitiveservices.azure.com/.default")
            
            self._mini_client = AsyncAzureOpenAI(
                api_version="2024-08-01-preview",
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=token.token
            )
        
        return self._mini_client

    async def _classify_query_with_llm(self, user_query: str, conversation_history: str = "") -> dict:
        """
        Use gpt-4.1-mini to dynamically classify if query can be answered from cache.
        
        Args:
            user_query: User's question
            conversation_history: Optional context from previous messages
        
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
            
            context = f"Previous context: {conversation_history}\n\n" if conversation_history else ""
            user_prompt = f"""{context}Current user query: "{user_query}"

Can this query be answered using cached data? Which type?"""
            
            response = await client.chat.completions.create(
                model=settings.AZURE_OPENAI_MINI_DEPLOYMENT_NAME,
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
                model=settings.AZURE_OPENAI_MINI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,  # Deterministic for data formatting
                max_tokens=1500  # Increased to allow full HTML tables with inline styles
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
        # Use LLM to classify the query
        classification = await self._classify_query_with_llm(user_message)
        
        if not classification.get("can_use_cache"):
            logger.info(f"🔍 [CACHE] Query not cacheable: {classification.get('reasoning')}")
            return None
        
        data_type = classification.get("data_type")
        if not data_type:
            return None
        
        logger.info(f"✅ [CACHE] Query classified as '{data_type}' - checking cache...")
        
        # Try to get cached data based on classification
        if data_type == "balance":
            balance = await self.cache_manager.get_cached_data(customer_id, "balance")
            # Validate balance - if 0 or None, treat as cache miss and call MCP
            if balance is not None and balance > 0:
                logger.info(f"✅ [CACHE HIT] Balance query answered from cache: {balance} THB")
                
                # Try LLM formatting first
                llm_response = await self._format_with_llm(
                    user_query=user_message,
                    cached_data={"balance": balance, "currency": "THB"},
                    data_type="balance"
                )
                
                if llm_response:
                    return llm_response
                
                # Fallback to hardcoded format
                return f"Your current account balance is **{balance:,.2f} THB**."
            else:
                # Balance is 0 or None - don't trust cache, force MCP call
                logger.info(f"⚠️ [CACHE MISS] Balance is {balance}, forcing MCP call to get real data")
                return None
        
        elif data_type == "account_details":
            account_details = await self.cache_manager.get_cached_data(customer_id, "account_details")
            if account_details:
                logger.info(f"✅ [CACHE HIT] Account details query answered from cache")
                
                # Try LLM formatting first
                llm_response = await self._format_with_llm(
                    user_query=user_message,
                    cached_data={"account": account_details},
                    data_type="account_details"
                )
                
                if llm_response:
                    return llm_response
                
                # Fallback to hardcoded format
                response = "Here are your account details:\n\n"
                response += f"**Account ID:** {account_details.get('id', 'N/A')}\n"
                response += f"**Account Holder:** {account_details.get('accountHolderFullName', 'N/A')}\n"
                response += f"**Currency:** {account_details.get('currency', 'N/A')}\n"
                response += f"**Balance:** {float(account_details.get('balance', 0)):,.2f} THB\n"
                response += f"**Activation Date:** {account_details.get('activationDate', 'N/A')}\n"
                
                # Add payment methods if available
                payment_methods = account_details.get('paymentMethods')
                if payment_methods:
                    response += f"\n**Payment Methods:**\n"
                    for pm in payment_methods:
                        response += f"- {pm.get('type', 'N/A')} (ID: {pm.get('id', 'N/A')})\n"
                
                return response.strip()
        
        elif data_type == "transactions":
            transactions = await self.cache_manager.get_cached_data(customer_id, "last_5_transactions")
            if transactions:
                logger.info(f"✅ [CACHE HIT] Transaction query answered from cache: {len(transactions)} transactions")
                
                # Try LLM formatting first - let LLM interpret the query
                llm_response = await self._format_with_llm(
                    user_query=user_message,
                    cached_data={"transactions": transactions},
                    data_type="transactions"
                )
                
                if llm_response:
                    return llm_response
                
                # Fallback to hardcoded format (show all 5)
                response = "Here are your recent transactions:\n\n"
                for i, txn in enumerate(transactions[:5], 1):
                    txn_id = txn.get("id", "N/A")
                    desc = txn.get("description", "N/A")
                    amount = txn.get("amount", 0)
                    timestamp = txn.get("timestamp", "N/A")
                    # Format timestamp to readable date if available
                    if timestamp != "N/A":
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(timestamp.replace('+07:00', ''))
                            date_str = dt.strftime("%Y-%m-%d %H:%M")
                        except:
                            date_str = timestamp.split('T')[0] if 'T' in timestamp else timestamp
                    else:
                        date_str = "N/A"
                    
                    response += f"{i}. **{desc}** - {amount:,.2f} THB (ID: {txn_id}, Date: {date_str})\n"
                return response.strip()
        
        elif data_type == "beneficiaries":
            beneficiaries = await self.cache_manager.get_cached_data(customer_id, "beneficiaries")
            if beneficiaries:
                logger.info(f"✅ [CACHE HIT] Beneficiary query answered from cache: {len(beneficiaries)} beneficiaries")
                
                # Try LLM formatting first
                llm_response = await self._format_with_llm(
                    user_query=user_message,
                    cached_data={"beneficiaries": beneficiaries, "total_count": len(beneficiaries)},
                    data_type="beneficiaries"
                )
                
                if llm_response:
                    return llm_response
                
                # Fallback to hardcoded format
                response = f"You have **{len(beneficiaries)}** registered beneficiaries:\n\n"
                for i, ben in enumerate(beneficiaries[:10], 1):  # Show up to 10
                    name = ben.get("name", "N/A")
                    account_num = ben.get("account_number", "N/A")
                    alias = ben.get("alias", "")
                    if alias:
                        response += f"{i}. **{name}** ({alias}) - Account: {account_num}\n"
                    else:
                        response += f"{i}. **{name}** - Account: {account_num}\n"
                
                if len(beneficiaries) > 10:
                    response += f"\n... and {len(beneficiaries) - 10} more."
                
                return response.strip()
        
        elif data_type == "limits":
            limits = await self.cache_manager.get_cached_data(customer_id, "limits")
            if limits:
                logger.info(f"✅ [CACHE HIT] Limits query answered from cache")
                
                # Try LLM formatting first
                llm_response = await self._format_with_llm(
                    user_query=user_message,
                    cached_data={"limits": limits},
                    data_type="limits"
                )
                
                if llm_response:
                    return llm_response
                
                # Fallback to hardcoded format
                response = "Your transaction limits:\n\n"
                
                # Per-transaction limit
                per_txn = limits.get("perTransactionLimit", {})
                if per_txn:
                    response += f"**Per Transaction:** {per_txn.get('amount', 0):,.2f} {per_txn.get('currency', 'THB')}\n"
                
                # Daily limit
                daily = limits.get("dailyLimit", {})
                if daily:
                    response += f"**Daily Limit:** {daily.get('amount', 0):,.2f} {daily.get('currency', 'THB')}\n"
                    response += f"**Daily Remaining:** {daily.get('remaining', 0):,.2f} {daily.get('currency', 'THB')}\n"
                
                # Monthly limit
                monthly = limits.get("monthlyLimit", {})
                if monthly:
                    response += f"**Monthly Limit:** {monthly.get('amount', 0):,.2f} {monthly.get('currency', 'THB')}\n"
                    response += f"**Monthly Remaining:** {monthly.get('remaining', 0):,.2f} {monthly.get('currency', 'THB')}\n"
                
                return response.strip()
        
        return None

    async def _build_af_agent(self, thread_id: str | None, user_context=None) -> ChatAgent:
      """
      Build Azure AI Foundry agent with user context.
      
      Uses cached ChatAgent if available (unless thread_id changes).
      
      Args:
          thread_id: Optional thread ID for conversation continuity
          user_context: UserContext object containing authenticated user information
      """
      # Check if we can reuse cached agent (only if thread_id matches or both are None)
      if self._cached_chat_agent is not None and self._cached_thread_id == thread_id:
          logger.info(f"⚡ [CACHE HIT] Reusing cached Supervisor agent (avoids 10s rebuild)")
          print(f"⚡ [CACHE HIT] Reusing cached Supervisor agent (avoids 10s rebuild)")
          # Still need to update user_context for routing functions
          self.user_context = user_context
          return self._cached_chat_agent
      
      # Store user_context for use in routing functions
      self.user_context = user_context
      
      credential = await get_azure_credential_async()  
      chat_agent = None
      if thread_id is None:
          logger.info("🆕 Creating NEW Azure AI Foundry thread (no thread_id provided)")
          chat_client = AzureAIClient(
              project_client=self.foundry_project_client,
              agent_name=self.agent_name,
              agent_version=self.agent_version
          )
          
          # Debug: Check if Application Insights connection string is available
          app_insights_conn = settings.APPLICATIONINSIGHTS_CONNECTION_STRING
          if app_insights_conn:
              logger.info(f"✅ Application Insights connection string found: {app_insights_conn[:50]}...")
          else:
              logger.warning("⚠️ APPLICATIONINSIGHTS_CONNECTION_STRING not found in settings")
          
          try:
              await chat_client.setup_azure_ai_observability()
          except AttributeError:
              logger.warning("⚠️ setup_azure_ai_observability not available in current SDK version")
          
          chat_agent = chat_client.create_agent(
            name=SupervisorAgent.name,
            instructions=SupervisorAgent.instructions,
            tools=[self.route_to_account_agent,self.route_to_transaction_agent,self.route_to_payment_agent,self.route_to_prodinfo_faq_agent,self.route_to_ai_money_coach_agent,self.route_to_escalation_comms_agent]
          ) 
          
          self.current_thread = chat_agent.get_new_thread()
          logger.info(f"✅ NEW thread created: {self.current_thread.service_thread_id}")
      else:
         logger.info(f"🔄 ATTEMPTING to reuse existing Azure AI Foundry thread: {thread_id}")
         
         # Check if we already have this thread in our current session
         if hasattr(self, 'current_thread') and self.current_thread and self.current_thread.service_thread_id == thread_id:
             logger.info(f"♻️ Thread already exists in session, reusing: {thread_id}")
             return self.chat_agent if hasattr(self, 'chat_agent') else await self._create_chat_agent_for_thread(thread_id)
         
         try:
             chat_client = AzureAIClient(
                 project_client=self.foundry_project_client,
                 agent_name=self.agent_name,
                 agent_version=self.agent_version,
                 thread_id=thread_id
             )
             try:
                 await chat_client.setup_azure_ai_observability()
             except AttributeError:
                 logger.warning("⚠️ setup_azure_ai_observability not available in current SDK version")
             chat_agent = chat_client.create_agent(
                name=SupervisorAgent.name,
                instructions=SupervisorAgent.instructions,
                tools=[self.route_to_account_agent,self.route_to_transaction_agent,self.route_to_payment_agent,self.route_to_prodinfo_faq_agent,self.route_to_ai_money_coach_agent,self.route_to_escalation_comms_agent]
             ) 
             self.current_thread = chat_agent.get_new_thread(service_thread_id=thread_id)
             
             # Validate that we got the expected thread ID
             if self.current_thread.service_thread_id == thread_id:
                 logger.info(f"✅ Successfully REUSED thread: {self.current_thread.service_thread_id}")
             else:
                 logger.warning(f"⚠️ Thread ID mismatch! Expected: {thread_id}, Got: {self.current_thread.service_thread_id}")
                 # Force correct thread ID to maintain consistency
                 logger.info(f"🔧 Forcing thread ID consistency: {thread_id}")
         except Exception as e:
             logger.error(f"❌ Failed to reuse thread {thread_id}: {e}")
             # Fallback to creating new thread
             logger.info("🔄 Falling back to creating NEW thread")
             chat_client = AzureAIClient(
                 project_client=self.foundry_project_client,
                 agent_name=self.agent_name,
                 agent_version=self.agent_version
             )
             try:
                 await chat_client.setup_azure_ai_observability()
             except AttributeError:
                 logger.warning("⚠️ setup_azure_ai_observability not available in current SDK version")
             chat_agent = chat_client.create_agent(
                name=SupervisorAgent.name,
                instructions=SupervisorAgent.instructions,
                tools=[self.route_to_account_agent,self.route_to_transaction_agent,self.route_to_payment_agent,self.route_to_prodinfo_faq_agent,self.route_to_ai_money_coach_agent,self.route_to_escalation_comms_agent]
             ) 
             self.current_thread = chat_agent.get_new_thread()
             logger.info(f"✅ Fallback NEW thread created: {self.current_thread.service_thread_id}") 
      
      # Cache the built agent for future requests
      self._cached_chat_agent = chat_agent
      self._cached_thread_id = thread_id
      logger.info(f"💾 [CACHE STORED] Supervisor agent cached (thread_id={thread_id})")
      print(f"💾 [CACHE STORED] Supervisor agent cached (thread_id={thread_id})")
      
      # Store chat_agent reference for potential reuse
      self.chat_agent = chat_agent
      return chat_agent

    async def _create_chat_agent_for_thread(self, thread_id: str) -> ChatAgent:
        """Helper method to create a chat agent for an existing thread"""
        credential = await get_azure_credential_async()
        chat_client = AzureAIClient(
            project_client=self.foundry_project_client,
            agent_name=self.agent_name,
            agent_version=self.agent_version,
            thread_id=thread_id
        )
        try:
            await chat_client.setup_azure_ai_observability()
        except AttributeError:
            logger.warning("⚠️ setup_azure_ai_observability not available in current SDK version")
        chat_agent = chat_client.create_agent(
            name=SupervisorAgent.name,
            instructions=SupervisorAgent.instructions,
            tools=[self.route_to_account_agent,self.route_to_transaction_agent,self.route_to_payment_agent,self.route_to_prodinfo_faq_agent,self.route_to_ai_money_coach_agent,self.route_to_escalation_comms_agent]
        ) 
        return chat_agent

    def _get_app_insights_connection_string(self) -> str:
        """Get Application Insights connection string from settings."""
        connection_string = settings.APPLICATIONINSIGHTS_CONNECTION_STRING
        if not connection_string:
            logger.warning("⚠️ APPLICATIONINSIGHTS_CONNECTION_STRING not found in settings")
            return ""
        return connection_string

    async def processMessage(self, user_message: str, thread_id: str | None, user_context) -> tuple[str, str | None]:
      """Process a chat message using the injected Azure Chat Completion service and return response and thread id.
         Foundry based agents have built-in thread store implementation per thread id using cosmosdb.
         
      Args:
          user_message: The user's chat message
          thread_id: Optional thread ID for conversation continuity
          user_context: UserContext object containing authenticated user information
      """
      from app.observability.banking_telemetry import get_banking_telemetry
      import time
      
      telemetry = get_banking_telemetry()
      start_time = time.time()
      
      print(f"\n{'='*80}")
      print(f"🎯 [SUPERVISOR] NEW MESSAGE RECEIVED")
      print(f"{'='*80}")
      print(f"💬 User Message: {user_message}")
      print(f"🧵 Thread ID: {thread_id}")
      print(f"👤 User: {user_context.entra_user_email} (Customer: {user_context.customer_id})")
      print(f"{'='*80}\n")
      
      logger.info(f"[SUPERVISOR] Processing message from {user_context.entra_user_email}: {user_message[:100]}")
      
      # Try to answer from cache first (for balance/transaction queries)
      cached_response = await self._try_cache_response(user_message, user_context.customer_id)
      if cached_response:
          print(f"⚡ [CACHE] Query answered from cache (instant response)")
          duration = time.time() - start_time
          
          # Track cache hit
          telemetry.track_user_message(
              user_query=user_message,
              thread_id=thread_id or "cache-response",
              response_text=cached_response,
              duration_seconds=duration
          )
          
          logger.info(f"[SUPERVISOR] Cache hit | Duration: {duration:.2f}s")
          return cached_response, thread_id
      
      print(f"🔧 [SUPERVISOR] Cache miss - building supervisor agent...")
      agent = await self._build_af_agent(thread_id, user_context)
      print(f"✅ [SUPERVISOR] Supervisor agent ready, analyzing message for routing...\n")
      
      response = await agent.run(user_message, thread=self.current_thread)
      
      duration = time.time() - start_time
      actual_thread_id = self.current_thread.service_thread_id if self.current_thread else thread_id
      
      # Track EVERY user message (including follow-ups)
      telemetry.track_user_message(
          user_query=user_message,
          thread_id=actual_thread_id,
          response_text=response.text,
          duration_seconds=duration
      )
      
      print(f"\n{'='*80}")
      print(f"✅ [SUPERVISOR] REQUEST COMPLETED")
      print(f"{'='*80}")
      print(f"⏱️  Duration: {duration:.2f}s")
      print(f"🧵 Final Thread ID: {actual_thread_id}")
      print(f"{'='*80}\n")
      
      logger.info(f"[SUPERVISOR] Response sent | Duration: {duration:.2f}s | Thread: {actual_thread_id}")
      
      return response.text, self.current_thread.service_thread_id

    async def processMessageStream(self, user_message: str, thread_id: str | None, user_context) -> AsyncGenerator[tuple[str, bool, str | None, dict | None], None]:
      """Process a chat message and stream the response using Azure AI Foundry agent.
         Foundry based agents have built-in thread store implementation per thread id using cosmosdb.

      Args:
          user_message: The user's chat message
          thread_id: Optional thread ID for conversation continuity
          user_context: UserContext object containing authenticated user information

      Yields:
          tuple[str, bool, str | None, dict | None]: (content_chunk, is_final, thread_id, thinking_event)
              - content_chunk: The text chunk to send
              - is_final: Whether this is the final chunk
              - thread_id: The thread ID (only set on final chunk)
              - thinking_event: Optional thinking event data (type, step, message, status, timestamp, duration)
      """
      import time
      start_time = time.time()
      
      print(f"\n{'='*80}")
      print(f"🎯 [SUPERVISOR STREAM] NEW STREAMING REQUEST")
      print(f"{'='*80}")
      print(f"💬 User Message: {user_message}")
      print(f"🧵 Thread ID: {thread_id}")
      print(f"👤 User: {user_context.entra_user_email} (Customer: {user_context.customer_id})")
      print(f"{'='*80}\n")
      
      logger.info(f"[SUPERVISOR STREAM] Processing streaming message from {user_context.entra_user_email}: {user_message[:100]}")
      
      # Emit analyzing step
      print(f"\n🧠 [THINKING] Emitting 'analyzing' step (in_progress)")
      yield ("", False, None, {
          "type": "thinking",
          "step": "analyzing",
          "message": "Analyzing your request",
          "status": "in_progress",
          "timestamp": time.time()
      })
      
      # Smart cache checking: Skip for knowledge-only queries (UC2/UC3)
      # These don't need account data and can route immediately
      message_lower = user_message.lower()
      skip_cache = any([
          # UC3 - Financial advice keywords
          any(word in message_lower for word in ["avalanche", "snowball", "debt payoff", "financial advice", "budgeting tip"]),
          # UC2 - Product info keywords (when not asking about MY specific account)
          (any(phrase in message_lower for phrase in ["what is", "what are", "explain", "tell me about", "how does", "how do"]) and
           any(word in message_lower for word in ["interest rate", "savings account", "loan", "credit card", "product", "fee"])),
          # UC2 - Direct product questions  
          any(phrase in message_lower for phrase in ["your interest rate", "your credit card", "your loan", "your product", "bankx offer"])
      ])
      
      if skip_cache:
          print(f"⚡ [CACHE] Skipping cache check - knowledge-only query detected")
          yield ("", False, None, {
              "type": "thinking",
              "step": "checking_cache",
              "message": "Knowledge query - routing directly",
              "status": "completed",
              "timestamp": time.time(),
              "duration": 0.1
          })
      else:
          # Try to answer from cache first (for balance/transaction queries)
          cache_check_start = time.time()
          print(f"🧠 [THINKING] Emitting 'checking_cache' step (in_progress)")
          yield ("", False, None, {
              "type": "thinking",
              "step": "checking_cache",
              "message": "Checking cached data",
              "status": "in_progress",
              "timestamp": time.time()
          })
          
          cached_response = await self._try_cache_response(user_message, user_context.customer_id)
          if cached_response:
              print(f"⚡ [CACHE] Query answered from cache (instant response)")
              
              # Determine which agent would have been used (for visualization)
              cache_agent = "SupervisorAgent"  # Default
              if any(word in user_message.lower() for word in ['balance', 'account', 'detail']):
                  cache_agent = "AccountAgent"
              elif any(word in user_message.lower() for word in ['transfer', 'payment', 'pay', 'send']):
                  cache_agent = "PaymentAgent"
              elif any(word in user_message.lower() for word in ['transaction', 'history', 'last']):
                  cache_agent = "TransactionAgent"
              elif any(word in user_message.lower() for word in ['product', 'service', 'loan', 'card']):
                  cache_agent = "ProdInfoFAQAgent"
              elif any(word in user_message.lower() for word in ['debt', 'saving', 'financial', 'budget']):
                  cache_agent = "AIMoneyCoachAgent"
              
              # Mark analyzing step as complete FIRST
              print(f"🧠 [THINKING] Cache HIT - Emitting 'analyzing' step (completed) - Duration: {time.time() - start_time:.2f}s")
              yield ("", False, None, {
                  "type": "thinking",
                  "step": "analyzing",
                  "message": "Request analyzed",
                  "status": "completed",
                  "timestamp": time.time(),
                  "duration": time.time() - start_time
              })
              
              # Mark cache check as complete
              print(f"🧠 [THINKING] Cache HIT - Emitting 'checking_cache' step (completed) - Duration: {time.time() - cache_check_start:.2f}s")
              yield ("", False, None, {
                  "type": "thinking",
                  "step": "checking_cache",
                  "message": "Found in cache",
                  "status": "completed",
                  "timestamp": time.time(),
                  "duration": time.time() - cache_check_start
              })
              
              # Emit routing event (simulated for visualization)
              print(f"🧠 [THINKING] Cache HIT - Emitting routing events for {cache_agent}")
              yield ("", False, None, {
                  "type": "thinking",
                  "step": "routing",
                  "message": "Using cached result",
                  "status": "completed",
                  "timestamp": time.time()
              })
              
              # Emit agent selected event
              yield ("", False, None, {
                  "type": "thinking",
                  "step": "agent_selected",
                  "message": f"🎯 {cache_agent} (cached)",
                  "status": "completed",
                  "timestamp": time.time()
              })
              
              # Mark response as generated
              yield ("", False, None, {
                  "type": "thinking",
                  "step": "generating",
                  "message": "Preparing response",
                  "status": "completed",
                  "timestamp": time.time(),
                  "duration": 0.1
              })
              
              # Yield the complete cached response as a single chunk
              yield (cached_response, False, None, None)
              yield ("", True, thread_id, None)
              
              # Track cache hit
              from app.observability.banking_telemetry import get_banking_telemetry
              telemetry = get_banking_telemetry()
              telemetry.track_user_message(
                  user_query=user_message,
                  thread_id=thread_id or "cache-response",
                  response_text=cached_response,
                  duration_seconds=0
              )
              
              # Log to conversation manager if enabled
              if self.conversation_manager and thread_id:
                  self.conversation_manager.add_message(
                      thread_id, "user", user_message, azure_thread_id=thread_id
                  )
                  self.conversation_manager.add_message(
                      thread_id, "assistant", cached_response, azure_thread_id=thread_id
                  )
              
              logger.info(f"[SUPERVISOR STREAM] Cache hit - instant response")
              return
          
          # Cache miss - continue with agent routing
          print(f"🧠 [THINKING] Cache MISS - Emitting 'checking_cache' step (completed) - Duration: {time.time() - cache_check_start:.2f}s")
          yield ("", False, None, {
              "type": "thinking",
              "step": "checking_cache",
              "message": "Cache miss, querying live data",
              "status": "completed",
          "timestamp": time.time(),
          "duration": time.time() - cache_check_start
      })
      
      # Mark analyzing as complete
      print(f"🧠 [THINKING] Emitting 'analyzing' step (completed) - Duration: {time.time() - start_time:.2f}s")
      yield ("", False, None, {
          "type": "thinking",
          "step": "analyzing",
          "message": "Request analyzed",
          "status": "completed",
          "timestamp": time.time(),
          "duration": time.time() - start_time
      })
      
      print(f"🔧 [SUPERVISOR STREAM] Cache miss - building supervisor agent...")
      
      # Emit routing step
      routing_start = time.time()
      print(f"🧠 [THINKING] Emitting 'routing' step (in_progress)")
      yield ("", False, None, {
          "type": "thinking",
          "step": "routing",
          "message": "Determining specialist agent",
          "status": "in_progress",
          "timestamp": time.time()
      })
      
      # Check for thread transitions and mark previous thread complete
      if self.conversation_manager and thread_id and self.last_active_thread and thread_id != self.last_active_thread:
          logger.info(f"🔄 Thread transition detected: {self.last_active_thread} → {thread_id}")
          self.conversation_manager.mark_thread_complete(self.last_active_thread)
      
      # Initialize session based on thread_id to avoid duplicate sessions
      if self.conversation_manager:
          if thread_id:
              # Use thread_id directly as session_id (Azure already provides proper thread ID format)
              self.current_session_id = thread_id
              
              if not self.conversation_manager.get_conversation(self.current_session_id):
                  self.current_session_id = self.conversation_manager.create_session(self.current_session_id)
                  logger.info(f"✅ Created new conversation session: {self.current_session_id}")
              else:
                  logger.info(f"✅ Reusing existing conversation session: {self.current_session_id}")
          elif not self.current_session_id:
              self.current_session_id = self.conversation_manager.create_session()
              logger.info(f"✅ Created new conversation session (no thread_id): {self.current_session_id}")
      
      # Update last active thread
      self.last_active_thread = thread_id
      
      # Enhanced validation to prevent thread duplication
      logger.info(f"🔍 Session validation - Input thread_id: {thread_id}, Session ID: {self.current_session_id}")
      
      # Log user message
      if self.conversation_manager and self.current_session_id:
          self.conversation_manager.add_message(
              self.current_session_id, "user", user_message, 
              azure_thread_id=thread_id
          )
      
      try:
          agent = await self._build_af_agent(thread_id, user_context)
          
          full_response = ""
          routing_events_emitted = False
          gathering_emitted = False
          gathering_start = time.time()  # Initialize here
          first_content_received = False

          try:
              # Use streaming with the foundry agent
              async for chunk in agent.run_stream(user_message, thread=self.current_thread):
                  # FIRST: Check if routing tool was called and emit routing events
                  if not routing_events_emitted and hasattr(self, 'pending_routing_events') and self.pending_routing_events:
                      print(f"🎯 [DEBUG] Emitting {len(self.pending_routing_events)} pending routing events", flush=True)
                      for event in self.pending_routing_events:
                          print(f"🎯 [DEBUG] Emitting event: {event}", flush=True)
                          yield ("", False, None, event)
                      self.pending_routing_events = []  # Clear after emitting
                      routing_events_emitted = True
                  
                  # SECOND: After routing events, emit gathering_data step (only once)
                  if routing_events_emitted and not gathering_emitted:
                      gathering_start = time.time()  # Reset timer when actually emitting
                      print(f"🧠 [THINKING] Emitting 'gathering_data' step (in_progress)")
                      yield ("", False, None, {
                          "type": "thinking",
                          "step": "gathering_data",
                          "message": "Fetching required information",
                          "status": "in_progress",
                          "timestamp": time.time()
                      })
                      gathering_emitted = True
                  
                  if hasattr(chunk, 'text') and chunk.text:
                      content = chunk.text
                      full_response += content
                      
                      # On first content chunk, mark routing as completed (if not already done by routing tool)
                      if not first_content_received:
                          first_content_received = True
                          if not routing_events_emitted:
                              print(f"🧠 [THINKING] First content received - Marking 'routing' step as completed")
                              yield ("", False, None, {
                                  "type": "thinking",
                                  "step": "routing",
                              "message": "Specialist agent determined",
                              "status": "completed",
                              "timestamp": time.time(),
                              "duration": time.time() - routing_start
                          })
                      
                      # Yield intermediate chunk
                      yield (content, False, None, None)
          except Exception as stream_error:
              logger.error(f"Error during streaming: {str(stream_error)}", exc_info=True)
              
              # Check if it's a thread cancellation error - create new thread if needed
              if "Cannot cancel run with status" in str(stream_error):
                  logger.info("Thread cancellation error detected, creating new thread")
                  try:
                      # Force create a new thread to bypass the stuck thread
                      agent = await self._build_af_agent(None)  # Force new thread
                      response = await agent.run(user_message, thread=None)
                      content = response.text if hasattr(response, 'text') else str(response)
                      yield (content, True, None, None)
                      return
                  except Exception as new_thread_error:
                      logger.error(f"New thread creation failed: {str(new_thread_error)}", exc_info=True)
              
              # Fallback to non-streaming if streaming fails
              try:
                  logger.info("Streaming failed, falling back to non-streaming response")
                  response = await agent.run(user_message, thread=self.current_thread)
                  content = response.text if hasattr(response, 'text') else str(response)
                  yield (content, True, self.current_thread.service_thread_id, None)
                  return
              except Exception as fallback_error:
                  logger.error(f"Fallback also failed: {str(fallback_error)}", exc_info=True)
                  error_message = f"Both streaming and regular response failed. Please try again later."
                  yield (error_message, True, self.current_thread.service_thread_id, None)
                  return

          # Mark gathering data as complete (only if it was emitted)
          if gathering_emitted:
              print(f"🧠 [THINKING] Emitting 'gathering_data' step (completed) - Duration: {time.time() - gathering_start:.2f}s")
              yield ("", False, None, {
                  "type": "thinking",
                  "step": "gathering_data",
                  "message": "Information retrieved",
                  "status": "completed",
                  "timestamp": time.time(),
                  "duration": time.time() - gathering_start
              })
          
          # Mark generating as complete
          print(f"🧠 [THINKING] Emitting 'generating' step (completed)")
          yield ("", False, None, {
              "type": "thinking",
              "step": "generating",
              "message": "Response generated",
              "status": "completed",
              "timestamp": time.time(),
              "duration": 0.5
          })
          
          # Yield final chunk with consistent thread_id
          final_thread_id = self.current_thread.service_thread_id if self.current_thread else thread_id
          yield ("", True, final_thread_id, None)
          
          # Track EVERY user message (streaming version)
          from app.observability.banking_telemetry import get_banking_telemetry
          telemetry = get_banking_telemetry()
          telemetry.track_user_message(
              user_query=user_message,
              thread_id=final_thread_id,
              response_text=full_response,
              duration_seconds=0  # We don't track duration in streaming mode
          )
          
          # Log conversation Q&A pair
          try:
              from app.utils.conversation_logger import get_conversation_logger
              conv_logger = get_conversation_logger()
              conv_logger.log_qa_pair(
                  session_id=final_thread_id,
                  question=user_message,
                  answer=full_response,
                  agent_used=self.routed_agent_name,
                  thinking_steps=None,  # Can add if needed
                  duration_seconds=time.time() - start_time,
                  customer_id=user_context.customer_id if user_context else None,
                  user_email=user_context.entra_user_email if user_context else None
              )
          except Exception as e:
              logger.error(f"❌ Error logging conversation: {e}", exc_info=True)
          
          # Log assistant response with proper thread mapping
          if self.conversation_manager and self.current_session_id and full_response:
              self.conversation_manager.add_message(
                  self.current_session_id, "assistant", full_response,
                  azure_thread_id=final_thread_id
              )
              logger.info(f"🔍 Session tracking - Session: {self.current_session_id}, Azure Thread: {final_thread_id}")
          
      except Exception as e:
          logger.error(f"Error in processMessageStream: {str(e)}", exc_info=True)
          error_message = f"I apologize, but I encountered an error while processing your request: {str(e)}"
          
          # Log error
          if self.conversation_manager and self.current_session_id:
              self.conversation_manager.log_error(
                  self.current_session_id, "supervisor_error", str(e)
              )
          
          # Yield error message with consistent thread ID
          current_thread_id = self.current_thread.service_thread_id if self.current_thread else thread_id
          yield (error_message, True, current_thread_id, None)

    async def route_to_account_agent(self, user_message: str) -> str:
       """ Route the conversation to Account Agent with thread context"""
       from app.observability.banking_telemetry import get_banking_telemetry
       
       self.routed_agent_name = "AccountAgent"
       print(f"🎯 [DEBUG] Just set self.routed_agent_name = '{self.routed_agent_name}'", flush=True)
       
       # Store TWO routing events to be emitted by main stream:
       # 1. Complete the "routing" step
       # 2. Add new "agent_selected" step showing which agent was chosen
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
               "message": f"🎯 {self.routed_agent_name} selected",
               "status": "completed",
               "timestamp": time.time()
           }
       ]
       print(f"🎯 [DEBUG] Created pending_routing_events: {self.pending_routing_events}", flush=True)
       
       telemetry = get_banking_telemetry()
       
       # Get initial thread_id for logging and triage tracking
       initial_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       
       print(f"🔥 [ROUTE] SupervisorAgent routing to AccountAgent")
       print(f"🧵 [ROUTE] Initial thread ID: {initial_thread_id}")
       print(f"🧵 [ROUTE] current_thread exists: {self.current_thread is not None}")
       
       logger.info(f"🔥 SupervisorAgent routing to AccountAgent: {user_message}")
       logger.info(f"🧵 Current thread ID: {initial_thread_id}")
       
       # Track triage rule match
       triage_rule = self._determine_triage_rule(user_message, "AccountAgent")
       telemetry.track_triage_rule_match(triage_rule, "AccountAgent", user_message)
       
       # Build agent and execute (thread_id gets set here if new)
       # Extract customer_id and email from authenticated user context
       customer_id = self.user_context.customer_id if self.user_context else "Somchai"
       user_email = self.user_context.entra_user_email if self.user_context else None
       print(f"👤 [ROUTE] Using customer_id: {customer_id}, email: {user_email}")
       af_account_agent = await self.account_agent.build_af_agent(
           initial_thread_id, 
           customer_id=customer_id,
           user_email=user_email
       )
       
       # Set thread context on MCP tools so they can get actual thread_id
       if hasattr(af_account_agent, '_mcp_tools'):
           for tool in af_account_agent._mcp_tools:
               if hasattr(tool, 'set_thread_context'):
                   tool.set_thread_context(self.current_thread)
       
       response = await af_account_agent.run(user_message, thread=self.current_thread)
       
       # Get ACTUAL thread_id after execution (now it definitely exists)
       actual_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       print(f"🧵 [ROUTE] Actual thread ID after execution: {actual_thread_id}")
       
       # Store active agent for conversation continuity AFTER run() to get correct thread_id
       if actual_thread_id:
           self._store_active_agent("AccountAgent", self.account_agent, actual_thread_id)
       else:
           logger.warning(f"⚠️ No thread_id available to store AccountAgent in conversation state")
        #    decision.set_reasoning(f"User query classified as account-related: {self._classify_account_query(user_message)}")
        #    decision.set_result("success", f"Response length: {len(response.text)} chars")
           
       return response.text
    
    async def route_to_transaction_agent(self, user_message: str) -> str:
       """ Route the conversation to Transaction History Agent with thread context"""
       from app.observability.banking_telemetry import get_banking_telemetry
       
       telemetry = get_banking_telemetry()
       initial_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       
       self.routed_agent_name = "TransactionAgent"
       print(f"🎯 [DEBUG] Just set self.routed_agent_name = '{self.routed_agent_name}'", flush=True)
       
       # Store TWO routing events to be emitted by main stream
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
               "message": f"🎯 {self.routed_agent_name} selected",
               "status": "completed",
               "timestamp": time.time()
           }
       ]
       print(f"🎯 [DEBUG] Created pending_routing_events: {self.pending_routing_events}", flush=True)
       
       print(f"\n{'='*80}")
       print(f"📈 [ROUTING DECISION] SupervisorAgent → TransactionAgent (UC1)")
       print(f"{'='*80}")
       print(f"📝 User Question: {user_message}")
       print(f"🧵 Thread ID: {initial_thread_id}")
       print(f"💡 Reason: Question about transaction history or spending analysis")
       print(f"{'='*80}\n")
       
       logger.info(f"📈 SupervisorAgent routing to TransactionAgent: {user_message}")
       logger.info(f"🧵 Current thread ID: {initial_thread_id}")
       
       # Track triage rule match
       triage_rule = self._determine_triage_rule(user_message, "TransactionAgent")
       telemetry.track_triage_rule_match(triage_rule, "TransactionAgent", user_message)
       print(f"📋 [TRIAGE] Matched rule: {triage_rule}")
       
       # Build agent and execute
       customer_id = self.user_context.customer_id if self.user_context else "Somchai"
       user_email = self.user_context.entra_user_email if self.user_context else None
       print(f"👤 [CONTEXT] Using customer_id: {customer_id}, email: {user_email}")
       print(f"🔧 [BUILD] Building TransactionAgent...")

    #    # Track triage rule match
    #    triage_rule = self._determine_triage_rule(user_message, "AccountAgent")
    #    telemetry.track_triage_rule_match(triage_rule, "AccountAgent", user_message)
    #    print(f"📋 [TRIAGE] Matched rule: {triage_rule}")
       
    #    # Build agent and execute
    #    customer_id = self.user_context.customer_id if self.user_context else "Somchai"
    #    print(f"👤 [CONTEXT] Using customer_id: {customer_id}")
    #    print(f"🔧 [BUILD] Building AccountAgent...")

       af_transaction_agent = await self.transaction_agent.build_af_agent(
           initial_thread_id,
           customer_id=customer_id,
           user_email=user_email
       )
       
       # Set thread context on MCP tools so they can get actual thread_id
       if hasattr(af_transaction_agent, '_mcp_tools'):
           for tool in af_transaction_agent._mcp_tools:
               if hasattr(tool, 'set_thread_context'):
                   tool.set_thread_context(self.current_thread)
       
       print(f"🤖 [EXECUTE] Running TransactionAgent...")
       response = await af_transaction_agent.run(user_message, thread=self.current_thread)
       
       # Get actual thread_id after execution
       actual_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       
       print(f"\n{'='*80}")
       print(f"✅ [RESPONSE] TransactionAgent completed successfully")
       print(f"{'='*80}")
       print(f"📤 Response Preview: {response.text[:150]}...")
       print(f"🧵 Thread ID: {actual_thread_id}")
       print(f"{'='*80}\n")
       
       # Track agent decision with ACTUAL thread_id
       with telemetry.track_agent_decision("TransactionAgent", user_message, actual_thread_id) as decision:
           decision.set_triage_rule(triage_rule)
           decision.set_reasoning(f"User query involves transaction history or spending analysis")
           decision.set_result("success", f"Response length: {len(response.text)} chars")
           
       return response.text
    
    async def route_to_payment_agent(self, user_message: str) -> str:
       """ Route the conversation to Payment Agent with full thread context"""
       from app.observability.banking_telemetry import get_banking_telemetry
       
       telemetry = get_banking_telemetry()
       initial_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       
       self.routed_agent_name = "PaymentAgent"
       print(f"🎯 [DEBUG] Just set self.routed_agent_name = '{self.routed_agent_name}'", flush=True)
       
       # Store TWO routing events to be emitted by main stream
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
               "message": f"🎯 {self.routed_agent_name} selected",
               "status": "completed",
               "timestamp": time.time()
           }
       ]
       print(f"🎯 [DEBUG] Created pending_routing_events: {self.pending_routing_events}", flush=True)
       
       print(f"\n{'='*80}")
       print(f"💸 [ROUTING DECISION] SupervisorAgent → PaymentAgent (UC1)")
       print(f"{'='*80}")
       print(f"📝 User Question: {user_message}")
       print(f"🧵 Thread ID: {initial_thread_id}")
       print(f"💡 Reason: Payment request, bill upload, or payment confirmation")
       print(f"{'='*80}\n")
       
       logger.info(f"💸 SupervisorAgent routing to PaymentAgent: {user_message}")
       logger.info(f"🧵 Current thread ID: {initial_thread_id}")
       
       try:
           # Track triage rule match
           triage_rule = self._determine_triage_rule(user_message, "PaymentAgent")
           telemetry.track_triage_rule_match(triage_rule, "PaymentAgent", user_message)
           print(f"📋 [TRIAGE] Matched rule: {triage_rule}")
           
           # Build PaymentAgent with the SAME thread ID to maintain context
           customer_id = self.user_context.customer_id if self.user_context else "Somchai"
           user_email = self.user_context.entra_user_email if self.user_context else None
           print(f"👤 [CONTEXT] Using customer_id: {customer_id}, user_email: {user_email}")
           print(f"🔧 [BUILD] Building PaymentAgent...")
           af_payment_agent = await self.payment_agent.build_af_agent(initial_thread_id, customer_id=customer_id, user_email=user_email)
           print(f"✅ [BUILD] PaymentAgent built successfully")
           logger.info("✅ PaymentAgent built successfully with thread context")
           
           # Set thread context on MCP tools so they can get actual thread_id
           if hasattr(af_payment_agent, '_mcp_tools'):
               for tool in af_payment_agent._mcp_tools:
                   if hasattr(tool, 'set_thread_context'):
                       tool.set_thread_context(self.current_thread)
           
           # Pass the conversation context including previous messages
           # This ensures the PaymentAgent knows about previous confirmations
           print(f"🤖 [EXECUTE] Running PaymentAgent...")
           response = await af_payment_agent.run(user_message, thread=self.current_thread)
           
           # Get actual thread_id after execution
           actual_thread_id = self.current_thread.service_thread_id if self.current_thread else None
           
           # Store active agent for conversation continuity AFTER run() to get correct thread_id
           if actual_thread_id:
               self._store_active_agent("PaymentAgent", self.payment_agent, actual_thread_id)
           else:
               logger.warning(f"⚠️ No thread_id available to store PaymentAgent in conversation state")
           
           print(f"\n{'='*80}")
           print(f"✅ [RESPONSE] PaymentAgent completed successfully")
           print(f"{'='*80}")
           print(f"📤 Response Preview: {response.text[:150]}...")
           print(f"🧵 Thread ID: {actual_thread_id}")
           print(f"{'='*80}\n")
           
           logger.info(f"✅ PaymentAgent response: {response.text[:100]}...")
           
           # Get actual thread_id after execution (already set above)
           actual_thread_id = self.current_thread.service_thread_id if self.current_thread else None
           
           # Track agent decision with ACTUAL thread_id
           with telemetry.track_agent_decision("PaymentAgent", user_message, actual_thread_id) as decision:
               decision.set_triage_rule(triage_rule)
               decision.set_reasoning(f"User initiated payment or provided confirmation response")
               decision.set_result("success", f"Payment processing completed")
               
               # Log the interaction for debugging
               if self.conversation_manager and self.current_session_id:
                   self.conversation_manager.log_banking_operation(
                       self.current_session_id, "payment_agent_call", 
                       {"input": user_message, "output": response.text[:200]}
                   )
           
        #    # 🔄 CACHE REFRESH: After successful payment, refresh cache to get updated balances
        #    # Check if response indicates successful payment
        #    response_lower = response.text.lower()
        #    if any(keyword in response_lower for keyword in ["payment", "transfer", "successful", "completed", "sent"]):
        #        if customer_id and customer_id != "Somchai":
        #            try:
        #                print(f"\n{'='*80}")
        #                print(f"🔄 [CACHE_REFRESH] Payment completed, refreshing cache for {customer_id}")
        #                print(f"{'='*80}\n")
        #                logger.info(f"🔄 Refreshing cache after payment for customer {customer_id}")
                       
        #                # Get cache manager and refresh cache
        #                cache_manager = get_cache_manager()
                       
        #                # Create MCP client instances for cache refresh
        #                from app.cache.mcp_client import (
        #                    get_account_mcp_client,
        #                    get_transaction_mcp_client,
        #                    get_contacts_mcp_client,
        #                    get_limits_mcp_client
        #                )
                       
        #                mcp_clients = {
        #                    "account_mcp": get_account_mcp_client(),
        #                    "transaction_mcp": get_transaction_mcp_client(),
        #                    "contacts_mcp": get_contacts_mcp_client(),
        #                    "limits_mcp": get_limits_mcp_client()
        #                }
                       
        #                # Refresh cache with updated data from MCP servers
        #                await cache_manager.initialize_user_cache(
        #                    customer_id=customer_id,
        #                    user_email=self.user_context.entra_user_email if self.user_context else f"{customer_id}@example.com",
        #                    mcp_clients=mcp_clients
        #                )
                       
        #                print(f"✅ [CACHE_REFRESH] Cache refreshed successfully with updated balances")
        #                logger.info(f"✅ Cache refreshed successfully after payment")
        #            except Exception as cache_error:
        #                # Don't fail the payment response if cache refresh fails
        #                logger.warning(f"⚠️ Failed to refresh cache after payment: {cache_error}")
        #                print(f"⚠️ [CACHE_REFRESH] Failed to refresh cache: {cache_error}")
               
           return response.text
       except Exception as e:
           logger.error(f"❌ Error in route_to_payment_agent: {e}", exc_info=True)
           return f"I encountered an error while processing your payment request: {str(e)}"

    async def route_to_prodinfo_faq_agent(self, user_message: str) -> str:
       """ Route the conversation to ProdInfoFAQ Agent (UC2) for product information queries"""
       from app.observability.banking_telemetry import get_banking_telemetry
       
       telemetry = get_banking_telemetry()
       initial_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       
       self.routed_agent_name = "ProdInfoFAQAgent"
       print(f"🎯 [DEBUG] Just set self.routed_agent_name = '{self.routed_agent_name}'", flush=True)
       
       # Store TWO routing events to be emitted by main stream
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
               "message": f"🎯 {self.routed_agent_name} selected",
               "status": "completed",
               "timestamp": time.time()
           }
       ]
       print(f"🎯 [DEBUG] Created pending_routing_events: {self.pending_routing_events}", flush=True)
       
       print(f"\n{'='*80}")
       print(f"📚 [ROUTING DECISION] SupervisorAgent → ProdInfoFAQAgent (UC2 - Knowledge Base)")
       print(f"{'='*80}")
       print(f"📝 User Question: {user_message}")
       print(f"🧵 Thread ID: {initial_thread_id}")
       print(f"💡 Reason: Question about BankX products, features, rates, or FAQ")
       print(f"🔍 Agent Type: Native File Search (Azure AI Foundry Vector Store)")
       print(f"{'='*80}\n")
       
       logger.info(f"📚 SupervisorAgent routing to ProdInfoFAQAgent (UC2): {user_message}")
       logger.info(f"🧵 Current thread ID: {initial_thread_id}")
       
       try:
           # Track triage rule match
           triage_rule = self._determine_triage_rule(user_message, "ProdInfoFAQAgent")
           telemetry.track_triage_rule_match(triage_rule, "ProdInfoFAQAgent", user_message)
           print(f"📋 [TRIAGE] Matched rule: {triage_rule}")
           
           # Build ProdInfoFAQAgent with its OWN thread (NOT supervisor's thread to avoid tool inheritance)
           print(f"\n{'─'*80}")
           print(f"🔧 [BUILD PHASE] Building ProdInfoFAQAgentKnowledgeBase")
           print(f"{'─'*80}")
           print(f"🔧 Thread Strategy: Creating NEW isolated thread (thread_id=None)")
           print(f"🔧 Reason: Prevent tool inheritance from SupervisorAgent")
           print(f"⏳ Calling prodinfo_faq_agent.build_af_agent(thread_id=None)...")
           print(f"{'─'*80}\n")
           
           af_prodinfo_agent = await self.prodinfo_faq_agent.build_af_agent(thread_id=None)
           
           print(f"\n{'─'*80}")
           print(f"✅ [BUILD COMPLETE] ProdInfoFAQAgent built successfully")
           print(f"{'─'*80}")
           print(f"✅ Agent Object Type: {type(af_prodinfo_agent).__name__}")
           print(f"✅ Agent has 'run' method: {hasattr(af_prodinfo_agent, 'run')}")
           print(f"✅ Agent has 'chat_client': {hasattr(af_prodinfo_agent, 'chat_client')}")
           if hasattr(af_prodinfo_agent, 'chat_client'):
               print(f"✅ Chat Client Type: {type(af_prodinfo_agent.chat_client).__name__}")
           print(f"{'─'*80}\n")
           logger.info("✅ ProdInfoFAQAgent built successfully with its own thread context")
           
           # Run the agent WITHOUT passing supervisor's thread (use agent's own thread)
           print(f"\n{'='*80}")
           print(f"🤖 [EXECUTE] Running ProdInfoFAQAgent with knowledge base search...")
           print(f"{'='*80}")
           print(f"📤 Input Message: '{user_message}'")
           print(f"🔧 Agent Type: {type(af_prodinfo_agent).__name__}")
           print(f"🔧 Agent Name: {af_prodinfo_agent.name if hasattr(af_prodinfo_agent, 'name') else 'N/A'}")
           print(f"⏳ Waiting for agent response...")
           print(f"{'='*80}\n")
           
           response = await af_prodinfo_agent.run(user_message)
           
           print(f"\n{'='*80}")
           print(f"✅ [RESPONSE RECEIVED] ProdInfoFAQAgent completed")
           print(f"{'='*80}")
           print(f"📋 Response Type: {type(response).__name__}")
           print(f"📋 Response Attributes: {dir(response)}")
           print(f"\n📤 FULL RESPONSE TEXT:")
           print(f"{'─'*80}")
           print(f"{response.text}")
           print(f"{'─'*80}")
           print(f"\n📊 Response Analysis:")
           print(f"   Length: {len(response.text)} characters")
           print(f"   Contains citation marker '【': {('【' in response.text)}")
           print(f"   Contains 'source': {('source' in response.text.lower())}")
           print(f"   Contains '.docx': {('.docx' in response.text)}")
           print(f"   First 100 chars: {response.text[:100]}...")
           
           print(f"\n📋 Response Object Attributes:")
           response_attrs = dir(response)
           key_attrs = ['text', 'citations', 'annotations', 'metadata', 'content']
           for attr in key_attrs:
               has_attr = hasattr(response, attr)
               print(f"   {attr}: {'✅ EXISTS' if has_attr else '❌ MISSING'}")
               if has_attr:
                   try:
                       value = getattr(response, attr)
                       if value:
                           print(f"      Type: {type(value).__name__}, Value: {str(value)[:150]}...")
                       else:
                           print(f"      Value: None or empty")
                   except Exception as e:
                       print(f"      Error: {e}")
           
           print(f"{'='*80}\n")
           logger.info(f"✅ ProdInfoFAQAgent full response: {response.text}")
           if hasattr(response, 'citations'):
               logger.info(f"📎 Citations: {response.citations}")
           
           # Get actual thread_id after execution
           actual_thread_id = self.current_thread.service_thread_id if self.current_thread else None
           
           # Track agent decision with ACTUAL thread_id
           with telemetry.track_agent_decision("ProdInfoFAQAgent", user_message, actual_thread_id) as decision:
               decision.set_triage_rule(triage_rule)
               decision.set_reasoning(f"User asked about BankX products, features, or FAQ")
               decision.add_context("use_case", "UC2")
               decision.set_result("success", f"Product info retrieved")
               
               # Log the interaction
               if self.conversation_manager and self.current_session_id:
                   self.conversation_manager.log_banking_operation(
                       self.current_session_id, "prodinfo_faq_agent_call", 
                       {"input": user_message, "output": response.text[:200]}
                   )
           
           return response.text
       except Exception as e:
           logger.error(f"❌ Error in route_to_prodinfo_faq_agent: {e}", exc_info=True)
           return f"I encountered an error while retrieving product information: {str(e)}"

    async def route_to_ai_money_coach_agent(self, user_message: str) -> str:
       """ Route the conversation to AIMoneyCoach Agent (UC3) for personal finance advice"""
       from app.observability.banking_telemetry import get_banking_telemetry
       
       telemetry = get_banking_telemetry()
       initial_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       
       self.routed_agent_name = "AIMoneyCoachAgent"
       print(f"🎯 [DEBUG] Just set self.routed_agent_name = '{self.routed_agent_name}'", flush=True)
       
       # Store TWO routing events to be emitted by main stream
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
               "message": f"🎯 {self.routed_agent_name} selected",
               "status": "completed",
               "timestamp": time.time()
           }
       ]
       print(f"🎯 [DEBUG] Created pending_routing_events: {self.pending_routing_events}", flush=True)
       
       print(f"\n{'='*80}")
       print(f"💰 [ROUTING DECISION] SupervisorAgent → AIMoneyCoachAgent (UC3 - Knowledge Base)")
       print(f"{'='*80}")
       print(f"📝 User Question: {user_message}")
       print(f"🧵 Thread ID: {initial_thread_id}")
       print(f"💡 Reason: Question about personal finance advice, debt management, or budgeting")
       print(f"🔍 Agent Type: Native File Search (Financial Guidance Materials)")
       print(f"{'='*80}\n")
       
       logger.info(f"💰 SupervisorAgent routing to AIMoneyCoachAgent (UC3): {user_message}")
       logger.info(f"🧵 Current thread ID: {initial_thread_id}")
       
       try:
           # Track triage rule match
           triage_rule = self._determine_triage_rule(user_message, "AIMoneyCoachAgent")
           telemetry.track_triage_rule_match(triage_rule, "AIMoneyCoachAgent", user_message)
           print(f"📋 [TRIAGE] Matched rule: {triage_rule}")
           
           # Build AIMoneyCoachAgent with its OWN thread (NOT supervisor's thread to avoid tool inheritance)
           print(f"🔧 [BUILD] Building AIMoneyCoachKnowledgeBaseAgent with isolated thread...")
           af_money_coach_agent = await self.ai_money_coach_agent.build_af_agent(thread_id=None)
           print(f"✅ [BUILD] AIMoneyCoachAgent built successfully with isolated thread")
           logger.info("✅ AIMoneyCoachAgent built successfully with its own thread context")
           
           # Run the agent WITHOUT passing supervisor's thread (use agent's own thread)
           print(f"🤖 [EXECUTE] Running AIMoneyCoachAgent with knowledge base search...")
           response = await af_money_coach_agent.run(user_message)
           print(f"\n{'='*80}")
           print(f"✅ [RESPONSE] AIMoneyCoachAgent completed successfully")
           print(f"{'='*80}")
           print(f"📤 Response Preview: {response.text[:150]}...")
           print(f"📏 Response Length: {len(response.text)} characters")
           print(f"{'='*80}\n")
           logger.info(f"✅ AIMoneyCoachAgent response: {response.text[:100]}...")
           
           # Get actual thread_id after execution
           actual_thread_id = self.current_thread.service_thread_id if self.current_thread else None
           
           # Track agent decision with ACTUAL thread_id
           with telemetry.track_agent_decision("AIMoneyCoachAgent", user_message, actual_thread_id) as decision:
               decision.set_triage_rule(triage_rule)
               decision.set_reasoning(f"User asked for personal finance advice or debt management guidance")
               decision.add_context("use_case", "UC3")
               decision.add_context("advice_source", "Debt-Free to Financial Freedom book")
               decision.set_result("success", f"Financial advice provided")
               
               # Log the interaction
               if self.conversation_manager and self.current_session_id:
                   self.conversation_manager.log_banking_operation(
                       self.current_session_id, "ai_money_coach_agent_call", 
                       {"input": user_message, "output": response.text[:200]}
                   )
           
           return response.text
       except Exception as e:
           logger.error(f"❌ Error in route_to_ai_money_coach_agent: {e}", exc_info=True)
           return f"I encountered an error while providing financial advice: {str(e)}"

    async def route_to_escalation_comms_agent(self, ticket_id: str, subject: str, description: str, priority: str = "medium", customer_email: str = None) -> str:
       """Route ticket creation to EscalationComms Agent

       Args:
           ticket_id: Ticket identifier (format: TKT-YYYY-HHMMSS)
           subject: Ticket subject
           description: Ticket description
           priority: Ticket priority (default: "medium")
           customer_email: Optional. If not provided, extracted from self.user_context
       """
       from app.observability.banking_telemetry import get_banking_telemetry
       
       # Extract customer_email from user_context if not provided
       if not customer_email:
           if hasattr(self, 'user_context') and self.user_context:
               customer_email = "purohitabhinav2001@gmail.com"  # Temporary for testing
               logger.info(f"✅ Using hardcoded test email: {customer_email}")
           else:
               logger.error("❌ No customer_email provided and no user_context available")
               return "I encountered an error: Unable to identify the customer for ticket creation. Please try again."
       
       telemetry = get_banking_telemetry()
       initial_thread_id = self.current_thread.service_thread_id if self.current_thread else None
       
       self.routed_agent_name = "EscalationCommsAgent"
       print(f"🎯 [DEBUG] Just set self.routed_agent_name = '{self.routed_agent_name}'", flush=True)
       
       # Store routing events
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
               "message": f"🎯 {self.routed_agent_name} selected",
               "status": "completed",
               "timestamp": time.time()
           }
       ]
       print(f"🎯 [DEBUG] Created pending_routing_events: {self.pending_routing_events}", flush=True)
       
       print(f"\n{'='*80}")
       print(f"📧 [ROUTING DECISION] SupervisorAgent → EscalationCommsAgent via MCP")
       print(f"{'='*80}")
       print(f"📋 Ticket ID: {ticket_id}")
       print(f"👤 Customer: {customer_email}")
       print(f"📝 Subject: {subject}")
       print(f"🔧 Priority: {priority}")
       print(f"🧵 Thread ID: {initial_thread_id}")
       print(f"{'='*80}\n")
       
       logger.info(f"📧 SupervisorAgent routing to EscalationCommsAgent (via A2A service)")
       
       try:
           # Route to escalation-comms A2A service (port 8104)
           # The service will create the ticket and send emails
           logger.info(f"🔨 Building EscalationCommsAgent A2A wrapper...")
           af_escalation_agent = await self.escalation_comms_agent.build_af_agent(thread_id=None)
           logger.info(f"✅ EscalationCommsAgent wrapper built successfully")
           
           # Create ticket notification message for the agent
           ticket_message = f"Create support ticket {ticket_id} for customer {customer_email}. Subject: {subject}. Description: {description}. Priority: {priority}"
           logger.info(f"📤 Ticket message: {ticket_message}")
           
           try:
               logger.info(f"⏳ Calling af_escalation_agent.run()...")
               response = await af_escalation_agent.run(ticket_message)
               logger.info(f"✅ af_escalation_agent.run() completed successfully")
           except Exception as e:
               logger.error(f"❌ Error running EscalationCommsAgent: {e}", exc_info=True)
               return f"Error creating ticket: {str(e)}"
           
           # Extract response text with comprehensive error handling
           response_text = None
           try:
               logger.info(f"📋 Response object type: {type(response)}, value: {response}")
               
               if response is None:
                   logger.error("❌ Response is None")
                   response_text = "Ticket creation initiated"
               elif isinstance(response, str):
                   response_text = response
               elif hasattr(response, 'text') and response.text:
                   response_text = response.text
               elif hasattr(response, '__dict__'):
                   logger.info(f"📋 Response attributes: {response.__dict__}")
                   for attr in ['text', 'content', 'message', 'body', 'output']:
                       if hasattr(response, attr):
                           val = getattr(response, attr)
                           if val:
                               response_text = str(val)
                               break
               
               if not response_text:
                   response_text = str(response) if response else "Ticket creation initiated (no response text)"
                   
           except Exception as parse_error:
               logger.error(f"❌ Error parsing response: {parse_error}", exc_info=True)
               response_text = f"Ticket {ticket_id} creation initiated (response parsing issue)"
           
           logger.info(f"✅ EscalationCommsAgent response: {response_text}")
           
           # Track agent decision
           actual_thread_id = self.current_thread.service_thread_id if self.current_thread else None
           with telemetry.track_agent_decision("EscalationCommsAgent", ticket_message, actual_thread_id) as decision:
               decision.set_triage_rule("TICKET_CREATION")
               decision.set_reasoning(f"Creating support ticket via MCP server")
               decision.add_context("ticket_id", ticket_id)
               decision.add_context("customer_email", customer_email)
               decision.set_result("success", f"Ticket {ticket_id} creation initiated")
               
               if self.conversation_manager and self.current_session_id:
                   self.conversation_manager.log_banking_operation(
                       self.current_session_id, "escalation_comms_agent_call", 
                       {"ticket_id": ticket_id, "customer_email": customer_email}
                   )
           
           return response_text
       except Exception as e:
           logger.error(f"❌ Error in route_to_escalation_comms_agent: {e}", exc_info=True)
           return f"I encountered an error while creating the support ticket: {str(e)}"

    def _determine_triage_rule(self, user_message: str, target_agent: str) -> str:
        """
        Determine which triage rule was matched based on the message content.
        Returns a standardized rule name for telemetry tracking.
        """
        message_lower = user_message.lower()
        
        # UC1 - Financial Operations
        if target_agent == "AccountAgent":
            if any(word in message_lower for word in ["balance", "how much"]):
                return "UC1_ACCOUNT_BALANCE"
            elif any(word in message_lower for word in ["limit", "daily limit", "transaction limit"]):
                return "UC1_ACCOUNT_LIMITS"
            elif any(word in message_lower for word in ["card", "credit card", "debit card"]):
                return "UC1_PAYMENT_METHODS"
            elif any(word in message_lower for word in ["beneficiar", "saved", "contact"]):
                return "UC1_BENEFICIARIES"
            else:
                return "UC1_ACCOUNT_GENERAL"
        
        elif target_agent == "TransactionAgent":
            if any(word in message_lower for word in ["transaction", "history", "statement"]):
                return "UC1_TRANSACTION_HISTORY"
            elif any(word in message_lower for word in ["spent", "spending", "expense"]):
                return "UC1_TRANSACTION_AGGREGATION"
            else:
                return "UC1_TRANSACTION_GENERAL"
        
        elif target_agent == "PaymentAgent":
            if any(word in message_lower for word in ["transfer", "send money", "pay"]):
                return "UC1_PAYMENT_INITIATE"
            elif any(word in message_lower for word in ["yes", "confirm", "proceed"]):
                return "UC1_PAYMENT_CONFIRMATION"
            else:
                return "UC1_PAYMENT_GENERAL"
        
        # UC2 - Product Information
        elif target_agent == "ProdInfoFAQAgent":
            if any(word in message_lower for word in ["interest rate", "rate"]):
                return "UC2_INTEREST_RATES"
            elif any(word in message_lower for word in ["open account", "new account"]):
                return "UC2_ACCOUNT_OPENING"
            elif any(word in message_lower for word in ["savings", "fixed deposit"]):
                return "UC2_SAVINGS_PRODUCTS"
            elif any(word in message_lower for word in ["loan", "credit"]):
                return "UC2_LOAN_PRODUCTS"
            else:
                return "UC2_PRODUCT_GENERAL"
        
        # UC3 - Personal Finance Coaching
        elif target_agent == "AIMoneyCoachAgent":
            if any(word in message_lower for word in ["debt", "pay off"]):
                return "UC3_DEBT_MANAGEMENT"
            elif any(word in message_lower for word in ["save", "saving", "emergency fund"]):
                return "UC3_SAVINGS_STRATEGY"
            elif any(word in message_lower for word in ["budget", "budgeting"]):
                return "UC3_BUDGETING_ADVICE"
            elif any(word in message_lower for word in ["invest", "investment"]):
                return "UC3_INVESTMENT_GUIDANCE"
            else:
                return "UC3_FINANCIAL_ADVICE_GENERAL"
        
        return "UNKNOWN_RULE"
    
    def _classify_account_query(self, message: str) -> str:
        """Classify the type of account-related query for telemetry"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["balance", "how much"]):
            return "balance_inquiry"
        elif any(word in message_lower for word in ["limit"]):
            return "limit_inquiry"
        elif any(word in message_lower for word in ["card"]):
            return "payment_methods_inquiry"
        else:
            return "general_account_inquiry"
    
    def _store_active_agent(self, agent_name: str, agent_instance, thread_id: str):
        """Store the active agent in conversation state for multi-turn conversations."""
        if thread_id and self.user_context:
            self.state_manager.set_active_agent(
                thread_id=thread_id,
                agent_name=agent_name,
                agent_instance=agent_instance,
                customer_id=self.user_context.customer_id
            )


# Helper function for streaming specialist agent responses (used in continuation)
async def _stream_specialist_agent(
    agent_instance,
    user_message: str,
    thread_id: str,
    user_context
) -> AsyncGenerator:
    """
    Stream responses from a specialist agent (for conversation continuation).
    This is called when we want to continue with an active agent without re-routing.
    """
    import time
    
    try:
        # Emit gathering_data step
        gathering_start = time.time()
        yield ("", False, None, {
            "type": "thinking",
            "step": "gathering_data",
            "message": "Fetching required information",
            "status": "in_progress",
            "timestamp": time.time()
        })
        
        # Build the agent with the thread context (it's cached so fast)
        # Determine customer_id from user_context
        customer_id = user_context.customer_id if user_context else "Somchai"
        
        # Build agent (will use cached version if available)
        af_agent = await agent_instance.build_af_agent(thread_id, customer_id=customer_id)
        
        # Get the thread instance
        thread = agent_instance.current_thread if hasattr(agent_instance, 'current_thread') else None
        actual_thread_id = thread.service_thread_id if thread else thread_id
        
        # Emit gathering_data completed (agent is ready)
        gathering_duration = time.time() - gathering_start
        yield ("", False, None, {
            "type": "thinking",
            "step": "gathering_data",
            "message": "Information retrieved",
            "status": "completed",
            "timestamp": time.time(),
            "duration": gathering_duration
        })
        
        # Emit generating step start
        generating_start = time.time()
        yield ("", False, None, {
            "type": "thinking",
            "step": "generating",
            "message": "Generating response",
            "status": "in_progress",
            "timestamp": time.time()
        })
        
        # Stream the response from the agent
        full_response = ""
        async for chunk in af_agent.run_stream(user_message, thread=thread):
            # Accumulate the full response for final yield
            if hasattr(chunk, 'text') and chunk.text:
                full_response += chunk.text
                # Yield the chunk content
                yield (chunk.text, False, None, None)
        
        # Emit generating step completed
        generating_duration = time.time() - generating_start
        yield ("", False, None, {
            "type": "thinking",
            "step": "generating",
            "message": "Response generated",
            "status": "completed",
            "timestamp": time.time(),
            "duration": generating_duration
        })
        
        # Yield final marker with thread_id
        yield ("", True, actual_thread_id, None)
        
    except Exception as e:
        logger.error(f"Error in specialist agent stream: {e}", exc_info=True)
        yield (f"An error occurred: {str(e)}", True, thread_id, None)

