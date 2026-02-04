from typing import Any, AsyncGenerator
from agent_framework import ChatAgent
from agent_framework.exceptions import AgentThreadException
from agent_framework.azure import AzureOpenAIChatClient
from app.agents.azure_chat.account_agent import AccountAgent
from app.agents.azure_chat.transaction_agent import TransactionHistoryAgent
from app.agents.azure_chat.payment_agent import PaymentAgent
from app.agents.azure_chat.prodinfo_faq_agent import ProdInfoFAQAgent
from app.agents.azure_chat.ai_money_coach_agent import AIMoneyCoachAgent
from uuid import uuid4
import logging


logger = logging.getLogger(__name__)

class SupervisorAgent :

    instructions = """
      You are a Supervisor Agent for BankX, routing customer requests to specialized domain agents.

      ## Your Responsibilities
      1. Classify user intent
      2. Route to appropriate agent (Account, Transaction, or Payment)
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
      Examples: US 1.3 (Balance and Limits)

      ### Route to TransactionHistoryAgent (Transaction History, Aggregations, Insights)
      - "Show transactions for last week"
      - "How many transactions did I have?"
      - "What's my total spending in October?"
      - "Show details for transaction TXN-064"
      Examples: US 1.1 (View Transactions), US 1.2 (Aggregations), US 1.5 (Transaction Details)

      ### Route to PaymentAgent (Transfers, Money Movement)
      - "Transfer 1000 THB to Nattaporn"
      - "Send money to account 123-456-002"
      - "Pay 500 to Somchai"
      - "Make a transfer"
      Examples: US 1.4 (Transfer Approval)

      ### Route to ProdInfoFAQAgent (Product Information, FAQs, Banking Terms)
      - "What is a Current Account?"
      - "Tell me about savings account features"
      - "What are the interest rates for time deposits?"
      - "Compare fixed account vs savings account"
      - "What is the minimum balance for current account?"
      - "How do I open a savings account?"
      - "What products do you offer?"
      - "Explain compound interest calculation"
      - "What is withholding tax?"
      Examples: UC2 (Product Info & FAQ)

      ### Route to AIMoneyCoachAgent (Personal Finance Coaching, Debt Management)
      - "How can I manage my debt?"
      - "What is good debt vs bad debt?"
      - "How to become debt-free?"
      - "I'm drowning in debt, help!"
      - "Should I consolidate my loans?"
      - "How to build an emergency fund?"
      - "Financial advice for multiple debts"
      - "I feel hopeless about my finances"
      Examples: UC3 (AI Money Coach)

      ## Agent Capabilities

      **AccountAgent** (UC1):
      - Balance inquiries
      - Transaction limits (per-txn, daily, remaining)
      - Account details
      - Output: BALANCE_CARD

      **TransactionHistoryAgent** (UC1):
      - Transaction history with date ranges
      - Aggregations (COUNT, SUM_IN, SUM_OUT, NET)
      - Transaction details
      - Output: TXN_TABLE, INSIGHTS_CARD, TXN_DETAIL

      **PaymentAgent** (UC1):
      - Money transfers with approval workflow
      - Beneficiary management
      - Policy Gate validation
      - Output: TRANSFER_APPROVAL, TRANSFER_RESULT

      **ProdInfoFAQAgent** (UC2):
      - Product information with RAG retrieval
      - FAQ responses with source citations
      - Account type comparisons
      - Banking term explanations
      - Support ticket creation when answer not found
      - Output: KNOWLEDGE_CARD, FAQ_CARD, COMPARISON_CARD, EXPLANATION_CARD, TICKET_CARD

      **AIMoneyCoachAgent** (UC3):
      - Personal finance coaching grounded in "Debt-Free to Financial Freedom"
      - Clarification-first approach
      - Debt management strategies
      - Financial health assessment (Ordinary vs Critical Patient)
      - Mindset and psychological support
      - Multiple income stream guidance
      - Support ticket creation for out-of-scope queries
      - Output: Conversational with ASCII tables and visual elements

      ## Important Notes

      1. **Single routing per request** - Route to ONE agent only
      2. **Pass complete context** - Include full user message
      3. **Return agent response as-is** - Don't modify structured outputs
      4. **Log routing decisions** - For governance and analytics
      5. **Context preservation** - Maintain conversation thread

      ## Example Routing

      User: "What's my balance?"
      → Route to AccountAgent

      User: "Show transactions from last Friday"
      → Route to TransactionHistoryAgent

      User: "Transfer 1000 to Nattaporn"
      → Route to PaymentAgent

      User: "What is a Current Account?"
      → Route to ProdInfoFAQAgent

      User: "How can I manage my debt?"
      → Route to AIMoneyCoachAgent
    """
    name = "SupervisorAgent"
    description = "Routes customer requests to specialized domain agents (Account, Transaction, Payment, ProdInfoFAQ, AIMoneyCoach) with context-aware handling"

    """ A simple in-memory store [thread_id,serialized Thread state] to keep track of threads per user/session. 
    In production, this should be replaced with a persistent store like a database or distributed cache.
    """
    thread_store: dict[str, dict[str, Any]] = {}

    """ like the thread_store but only with supervisor generated messages. it's used for improve accuracy of agent selection avoiding to innclude messages from sub-agents."""
    supervisor_thread_store: dict[str, dict[str, Any]] = {}

    def __init__(self,
                 azure_chat_client: AzureOpenAIChatClient,
                 account_agent: AccountAgent,
                 transaction_agent: TransactionHistoryAgent,
                 payment_agent: PaymentAgent,
                 prodinfo_faq_agent: ProdInfoFAQAgent = None,
                 ai_money_coach_agent: AIMoneyCoachAgent = None
                                ):
      self.azure_chat_client = azure_chat_client
      self.account_agent = account_agent
      self.transaction_agent = transaction_agent
      self.payment_agent = payment_agent
      self.prodinfo_faq_agent = prodinfo_faq_agent
      self.ai_money_coach_agent = ai_money_coach_agent



    async def _build_af_agent(self) -> ChatAgent:

      # Build tools list with all available agents
      tools = [self.route_to_account_agent, self.route_to_transaction_agent, self.route_to_payment_agent]

      if self.prodinfo_faq_agent:
          tools.append(self.route_to_prodinfo_faq_agent)

      if self.ai_money_coach_agent:
          tools.append(self.route_to_ai_money_coach_agent)

      return ChatAgent(
            chat_client=self.azure_chat_client,
            instructions=SupervisorAgent.instructions,
            name=SupervisorAgent.name,
            tools=tools
        )

    async def route_to_account_agent(self, user_message: str) -> str:
       """ Route the conversation to Account Agent"""
       af_account_agent = await self.account_agent.build_af_agent()

      #Please note we are using the original user message and not the one generated by the supervisor agent.
       response = await af_account_agent.run(self.user_message, thread=self.current_thread)
       return response.text
    
    async def route_to_transaction_agent(self, user_message: str) -> str:
       """ Route the conversation to Transaction History Agent"""
       af_transaction_agent = await self.transaction_agent.build_af_agent()
      
      #Please note we are using the original user message and not the one generated by the supervisor agent.
       response = await af_transaction_agent.run(self.user_message, thread=self.current_thread)
       return response.text
    
    async def route_to_payment_agent(self, user_message: str) -> str:
       """ Route the conversation to Payment Agent"""
       af_payment_agent = await self.payment_agent.build_af_agent()

      #Please note we are using the original user message and not the one generated by the supervisor agent.
       response = await af_payment_agent.run(self.user_message, thread=self.current_thread)
       return response.text

    async def route_to_prodinfo_faq_agent(self, user_message: str) -> str:
       """ Route the conversation to ProdInfoFAQ Agent for product information and FAQs (UC2)"""
       if not self.prodinfo_faq_agent:
           return "Product information service is currently unavailable. Please contact customer service."

       af_prodinfo_faq_agent = await self.prodinfo_faq_agent.build_af_agent()

      #Please note we are using the original user message and not the one generated by the supervisor agent.
       response = await af_prodinfo_faq_agent.run(self.user_message, thread=self.current_thread)
       return response.text

    async def route_to_ai_money_coach_agent(self, user_message: str) -> str:
       """ Route the conversation to AIMoneyCoach Agent for personal finance coaching (UC3)"""
       if not self.ai_money_coach_agent:
           return "AI Money Coach service is currently unavailable. Please contact customer service."

       af_ai_money_coach_agent = await self.ai_money_coach_agent.build_af_agent()

      #Please note we are using the original user message and not the one generated by the supervisor agent.
       response = await af_ai_money_coach_agent.run(self.user_message, thread=self.current_thread)
       return response.text

    async def processMessageStream(self, user_message: str , thread_id : str | None) -> AsyncGenerator[tuple[str, bool, str | None], None]:
      """Process a chat message and stream the response.

      Yields:
          tuple[str, bool, str | None]: (content_chunk, is_final, thread_id)
              - content_chunk: The text chunk to send
              - is_final: Whether this is the final chunk
              - thread_id: The thread ID (only set on final chunk)
      """
      try:
          # Set up agent and thread (same as processMessage)
          agent = await self._build_af_agent()

          processed_thread_id = thread_id
          supervisor_resumed_thread = agent.get_new_thread()

          # Handle thread creation or resumption
          if processed_thread_id is None:
              self.current_thread = agent.get_new_thread()
              processed_thread_id = str(uuid4())
              SupervisorAgent.thread_store[processed_thread_id] = await self.current_thread.serialize()
              SupervisorAgent.supervisor_thread_store[processed_thread_id] = await supervisor_resumed_thread.serialize()
          else:
              serialized_thread = SupervisorAgent.thread_store.get(processed_thread_id, None)
              supervisor_serialized_thread = SupervisorAgent.supervisor_thread_store.get(processed_thread_id, None)
              
              if serialized_thread is None or supervisor_serialized_thread is None:
                  raise AgentThreadException(f"Thread id {processed_thread_id} not found in thread stores")
              
              resumed_thread = agent.get_new_thread()
              await resumed_thread.update_from_thread_state(serialized_thread)
              self.current_thread = resumed_thread
              await supervisor_resumed_thread.update_from_thread_state(supervisor_serialized_thread)

          # Save the original user message
          self.user_message = user_message

          # Stream the response
          full_response = ""

          try:
              # Use streaming
              async for chunk in agent.run_stream(user_message, thread=supervisor_resumed_thread):
                  if hasattr(chunk, 'text') and chunk.text:
                      content = chunk.text
                      full_response += content
                      # Yield intermediate chunk
                      yield (content, False, None)
          except Exception as stream_error:
              logger.error(f"Error during streaming: {str(stream_error)}", exc_info=True)
              error_message = f"Streaming failed: {str(stream_error)}. Please try again or disable streaming."
              yield (error_message, True, processed_thread_id)
              return

          # Update thread stores
          SupervisorAgent.thread_store[processed_thread_id] = await self.current_thread.serialize()
          SupervisorAgent.supervisor_thread_store[processed_thread_id] = await supervisor_resumed_thread.serialize()

          # Yield final chunk with thread_id
          yield ("", True, processed_thread_id)
          
      except Exception as e:
          logger.error(f"Error in processMessageStream: {str(e)}", exc_info=True)
          # Yield error message as content
          error_message = f"I apologize, but I encountered an error while processing your request: {str(e)}"
          yield (error_message, True, thread_id)

    async def processMessage(self, user_message: str , thread_id : str | None) -> tuple[str, str | None]:
      """Process a chat message using the injected Azure Chat Completion service and return response and thread id."""
      #For azure chat based agents we need to provide the message history externally as there is no built-in memory thread implementation per thread id.
      
      agent = await self._build_af_agent()

      processed_thread_id = thread_id
      supervisor_resumed_thread =  agent.get_new_thread()
      # The AgentThread doesn't allow to provide an external id when using azure openai chat completion agent. so we need to manage the thread id externally.
      if processed_thread_id is None:
         self.current_thread = agent.get_new_thread()
         processed_thread_id = str(uuid4())
         SupervisorAgent.thread_store[processed_thread_id] = await  self.current_thread.serialize()
         SupervisorAgent.supervisor_thread_store[processed_thread_id] = await supervisor_resumed_thread.serialize()

      else :
        serialized_thread = SupervisorAgent.thread_store.get(processed_thread_id, None)
        supervisor_serialized_thread = SupervisorAgent.supervisor_thread_store.get(processed_thread_id, None)
        
        if serialized_thread is None or supervisor_serialized_thread is None:
           raise AgentThreadException(f"Thread id {processed_thread_id} not found in thread stores")
        # set the thread as class instance variable so that it can be shared by agents called in the tools
        
        # there is bug in agent framework. I'll use update_from_thread_state as workaround
        # self.current_thread = await agent.deserialize_thread(serialized_thread)
        resumed_thread =  agent.get_new_thread()
        
        await resumed_thread.update_from_thread_state(serialized_thread)
        self.current_thread = resumed_thread

        
        await supervisor_resumed_thread.update_from_thread_state(supervisor_serialized_thread)

      #save the original user message to that can be used by sub-agents. we don't want to use the generated message from supervisor agent as input for sub-agents.
      # this is a hack when implementing supervisor pattern using agent-as-tool implementation. Once hand-off pattern will be available in agent framework it won't be required
      #as the context will be handed-off to the sub-agent who will take the control of the conversation and directly respond to the user.
      self.user_message = user_message

      response = await agent.run(user_message, thread=supervisor_resumed_thread)

      #make sure to update the thread store with the latest thread state
      SupervisorAgent.thread_store[processed_thread_id] = await self.current_thread.serialize()
      SupervisorAgent.supervisor_thread_store[processed_thread_id] = await supervisor_resumed_thread.serialize()
      
      return response.text, processed_thread_id

    