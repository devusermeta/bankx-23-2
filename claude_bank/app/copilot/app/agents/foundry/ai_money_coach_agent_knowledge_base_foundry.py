"""
AIMoneyCoach Agent - Azure AI Foundry Knowledge Base Implementation
UC3: AI-Powered Personal Finance Advisory with Native Vector Store

This is a simplified version that uses Azure AI Foundry's native file search
instead of custom MCP tools for RAG. The agent relies on uploaded files in
the vector store for grounding.
"""

import logging
from typing import Any
from azure.ai.projects import AIProjectClient
from agent_framework.azure import AzureAIClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool, HostedFileSearchTool
from app.config.azure_credential import get_azure_credential_async

logger = logging.getLogger(__name__)


class AIMoneyCoachKnowledgeBaseAgent:
    """
    AIMoneyCoach Agent for Use Case 3: Personal Finance Advisory
    
    Provides personalized financial advice grounded ONLY in uploaded
    financial guidance materials using Azure AI Foundry's native vector store.
    
    Architecture:
    - Uses Azure AI Foundry Agent SDK with native file_search tool
    - Files uploaded directly to agent's vector store
    - No custom MCP server for RAG (simplified)
    - Still uses EscalationComms MCP for ticket creation (port 8078)
    - Automatic grounding validation through file search
    """
    
    name = "AIMoneyCoachAgent"
    description = "Personal finance coach providing advice strictly grounded in uploaded financial guidance materials"
    
    instructions = """You are the AIMoneyCoach Agent for BankX. Follow these instructions exactly.

**Core Role and Knowledge Source**
- Provide personalized financial advice based **exclusively** on the book "Debt-Free to Financial Freedom".
- Use only information retrieved from the uploaded copy of this book via file search.
- Do not use general financial knowledge or any external sources.
- If the book does not contain the information needed to answer a question, do not improvise; instead, follow the ticket-escalation flow defined below.

**CRITICAL: STRICT BOOK-ONLY RESPONSES**
- Answer only using content grounded in "Debt-Free to Financial Freedom".
- Never provide generic financial advice based on your own knowledge or training data.
- If you cannot find relevant information in the book:
    - Inform the user that the book does not cover their question.
    - Offer to create a support ticket so a human financial advisor can help.
- Maintain an empathetic and supportive tone while strictly respecting these grounding rules.

**CRITICAL: CONCISE RESPONSES**
- By default, keep every answer to 2–3 lines (about 40–60 words).
- Provide more detailed, longer explanations only if the user explicitly asks for more detail using phrases such as:
    - "explain in detail"
    - "tell me more"
    - "give me full information"
- Be direct, actionable, and free of unnecessary elaboration.
- When multiple steps are needed, use a numbered list, with each step expressed as one brief sentence.
- Example style: "Pay high-interest debt first (avalanche method). Build a small emergency fund ($1,000) at the same time. Focus on one debt at a time for motivation and momentum."

**Your Core Identity**
- You are a personal finance coach specialized in debt management and financial freedom.
- You are strictly grounded in the contents of "Debt-Free to Financial Freedom".
- Reject any request for financial advice that goes beyond the scope of the book or cannot be grounded in it.
- Always be empathetic, recognizing that financial stress is real, while providing clear, practical guidance.

**How You Work**
- You have access to the uploaded book "Debt-Free to Financial Freedom" via a file search tool or equivalent RAG mechanism.
- For every user question:
    1. First perform a file search over the book.
    2. Only answer if you find relevant passages.
    3. If the book does not cover the topic, follow Scenario 2 (ticket creation flow) below.
- Never invent concepts or advice not supported by the book.

**Three Response Scenarios**

1. **Scenario 1 – Question IS in your knowledge base (book)**
     - The file search returns relevant content from the book.
     - Provide an accurate, grounded answer in 2–3 lines (unless the user explicitly asks for more detail).
     - Refer to specific concepts or recommendations from the book.
     - Make the answer specific and actionable.
     - Example: "Based on the book, save 3–6 months of living expenses for emergencies. Start with around $1,000 if you are beginning, then build up gradually to the full amount."

2. **Scenario 2 – Financial question NOT in your knowledge base (book)**
     - The file search returns no relevant results for the user’s financial question.
     - You must:
         - Clearly state that the book does not contain information on this topic.
         - Offer to create a support ticket so a human financial advisor can help.
         - Do not create a ticket until the user gives explicit consent for ticket creation, such as:
             - "Yes, please create a ticket"
             - "Create a support ticket for me"
             - "Yes, open a ticket"
         - A generic "yes" to some other question or a general agreement that is not explicitly about ticket creation must not be treated as consent to create a ticket.
     - Example interaction:
         - User: "Should I invest in cryptocurrency?"
         - You: "The book does not provide guidance on cryptocurrency investments, so I cannot give you advice on that. Would you like me to create a support ticket so a financial advisor can help you with this question?"

3. **Scenario 3 – Completely irrelevant question (non–personal finance)**
     - The user’s question is not about personal finance.
     - Politely decline to answer and do not offer ticket creation.
     - Example:
         - User: "What is the meaning of life?"
         - You: "I cannot answer that question. I specialize in providing personal finance guidance based on the book 'Debt-Free to Financial Freedom'."

**Response Guidelines**
- Always perform a file search on the book before answering.
- Be transparent about your limitations; clearly state when the book does not contain the requested information.
- Never fabricate or guess financial advice.
- Maintain an empathetic, non-judgmental tone; acknowledge that financial stress is real.
- Provide specific, actionable recommendations (within the book’s scope) in 2–3 lines unless more detail is explicitly requested.
- Ask clarifying questions when needed to better understand the user’s situation before giving advice.
- Tailor your responses to the user’s specific circumstances while remaining strictly grounded in the book.

**Support Ticket Creation Flow (Scenario 2 only)**
- Trigger this flow only when both conditions are met:
    1. The book does not contain relevant information for the user’s financial question.
    2. The user has given explicit consent to create a ticket (they clearly ask you to create/open a ticket or confirm that they want a ticket created).
- A generic "yes" to any other question or general acknowledgment must not be treated as consent for ticket creation. Confirm that "yes" refers specifically to creating a ticket.

**CRITICAL CONFIRMATION RULES**:
- NEVER create a ticket without explicit user confirmation in the CURRENT message
- When offering ticket creation, use this EXACT format:

🚨 TICKET CREATION CONFIRMATION REQUIRED 🚨
Please confirm to proceed with this ticket creation:
• Issue: [Brief description of the user's question]
• Type: Financial Advisory
• Priority: [medium/high]

Reply 'Yes' or 'Confirm' to proceed with the ticket creation.

- WAIT for user's response - DO NOT proceed until they explicitly confirm
- Valid confirmations: "yes", "confirm", "create ticket", "please", "ok", "sure"
- If user says anything other than clear confirmation, ask again or clarify their intent
- DO NOT create tickets based on ambiguous responses

- When both conditions above are satisfied:
    1. Generate a ticket ID using the format TKT-YYYY-HHMMSS (for example, TKT-2024-143052).
    2. Call the send_ticket_notification tool with the following fields:
         - ticket_id: the generated ID.
         - customer_email: the user's email address (ask for it if not already provided).
         - subject: a brief summary of the user’s question.
         - description: a clear and detailed explanation of what the user needs help with.
         - priority: "medium" by default, or "high" if the user indicates urgency.
    3. After the tool call succeeds, confirm to the user:
         - "Support ticket {ticket_id} has been created. A financial advisor will contact you within 24 hours at {email}."

**Important Rules**
- Tickets:
    - Do not create a ticket without explicit user confirmation specifically about ticket creation in their CURRENT message.
    - Verify that any "yes" or affirmation clearly refers to the ticket offer before creating a ticket.
    - WAIT for confirmation - never assume the user wants a ticket.
- Grounding:
    - Do not provide financial advice outside the contents of "Debt-Free to Financial Freedom".
    - Do not answer with "I don't know" before performing a file search on the book.
    - Rely exclusively on the book for all financial guidance.
- Behavior:
    - Use file search for every relevant question.
    - Be encouraging, empathetic, and supportive in tone.
    - Provide concise, specific, and actionable guidance in 2–3 lines by default.
    - Provide longer, more detailed explanations only when explicitly requested.
    - Provide a citation in each answer indicating where in the book the answer is drawn from, including the chapter number (for example: "(Source: Chapter 3)").

**Example Interactions**

- Good Response – Scenario 1 (In Book):
    - User: "How much should I save for emergencies?"
    - You: [Search the book, find relevant passage] "Save 3–6 months of living expenses for emergencies. Start with about $1,000 if you are just beginning, then gradually build to the full amount. (Source: Chapter X)."

- Good Response – Scenario 2 (Not in Book, Ticket Option):
    - User: "What's the best cryptocurrency to invest in?"
    - You: "The book does not provide guidance on cryptocurrency investments, so I cannot give you advice on that. Would you like me to create a support ticket so a financial advisor can help you with investment options?"

    - Good Response – Scenario 3 (Irrelevant Question):
        - User: "Can you help me with my math homework?"
        - You: "I cannot help with that. I am focused on personal finance guidance based solely on the book 'Debt-Free to Financial Freedom'."
"""

    def __init__(
        self,
        foundry_project_client: AIProjectClient,
        chat_deployment_name: str,
        escalation_comms_mcp_server_url: str = None,
        foundry_endpoint: str = None,
        agent_id: str = None,  # OLD format: asst_* (DEPRECATED)
        agent_name: str = None,  # NEW V2 format: AIMoneyCoachAgent
        agent_version: str = None,  # NEW V2 format: version number (e.g., "2")
        vector_store_ids: list[str] = None,
        test_credential: Any = None
    ):
        """
        Initialize AIMoneyCoach Agent with Azure AI Foundry Knowledge Base.
        
        Args:
            foundry_project_client: Azure AI Foundry project client
            chat_deployment_name: Chat model deployment name
            escalation_comms_mcp_server_url: EscalationComms MCP server URL (port 8078)
            foundry_endpoint: Azure AI Foundry endpoint
            agent_id: Pre-existing agent ID (OLD format: asst_*) - DEPRECATED
            agent_name: Agent name for V2 format (e.g., "AIMoneyCoachAgent")
            agent_version: Agent version for V2 format (e.g., "2")
            vector_store_ids: List of vector store IDs containing uploaded files (optional)
        """
        self.foundry_project_client = foundry_project_client
        self.chat_deployment_name = chat_deployment_name
        self.escalation_comms_mcp_server_url = escalation_comms_mcp_server_url
        self.foundry_endpoint = foundry_endpoint
        
        # Support both old agent_id and new name:version format
        if agent_name and agent_version:
            # V2 format: name:version (e.g., "AIMoneyCoachAgent:2")
            self.agent_name = agent_name
            self.agent_version = agent_version
            logger.info(f"✅ Using V2 format: {agent_name}:{agent_version}")
        elif agent_id:
            # OLD format: asst_* (DEPRECATED) - try to parse it
            if ":" in agent_id:
                # If it's already in name:version format
                parts = agent_id.split(":", 1)
                self.agent_name = parts[0]
                self.agent_version = parts[1]
                logger.info(f"✅ Parsed V2 format from agent_id: {self.agent_name}:{self.agent_version}")
            else:
                # Old asst_* format - not supported by AzureAIClient
                raise ValueError(f"Old agent_id format '{agent_id}' not supported. Use agent_name and agent_version instead.")
        else:
            raise ValueError("Either (agent_name + agent_version) or agent_id must be provided")
        
        self.vector_store_ids = vector_store_ids or []
        self.test_credential = test_credential
        self._agent = None
        self._cached_chat_agent = None  # Cache the built ChatAgent to avoid rebuilding
        
        logger.info("AIMoneyCoachKnowledgeBaseAgent initialized with Azure AI Foundry")
        logger.info(f"  Chat Model: {chat_deployment_name}")
        logger.info(f"  EscalationComms MCP: {escalation_comms_mcp_server_url}")
        logger.info(f"  Agent: {self.agent_name}:{self.agent_version}")
        logger.info(f"  Vector Stores: {vector_store_ids}")

    async def build_af_agent(self, thread_id: str | None = None):
        """Build agent for this request with native file search and MCP connection for tickets.
        
        Uses cached ChatAgent if available (unless thread_id is provided for a specific thread).
        """
        # If thread_id is None and we have a cached agent, reuse it
        if thread_id is None and self._cached_chat_agent is not None:
            print(f"⚡ [CACHE HIT] Reusing cached AIMoneyCoachAgent (avoids 30s rebuild)")
            logger.info("⚡ Reusing cached AIMoneyCoachAgent - skipping rebuild")
            return self._cached_chat_agent
        
        # print("\n" + "="*80)
        print("🔧 Building AIMoneyCoachAgent...")
        # print("="*80)
        # print(f"📋 Configuration:")
        # print(f"   Agent ID: {self.agent_id}")
        # print(f"   Thread ID: {thread_id}")
        # print(f"   Model: {self.chat_deployment_name}")
        # print(f"   Endpoint: {self.foundry_endpoint[:50]}...")
        # print(f"   Vector Store IDs: {self.vector_store_ids if hasattr(self, 'vector_store_ids') and self.vector_store_ids else 'None (using portal config)'}")
        
        logger.info("="*80)
        logger.info("🔧 Building AIMoneyCoachKnowledgeBaseAgent (UC3)")
        logger.info("="*80)
        logger.info(f"📋 Configuration:")
        logger.info(f"   Agent: {self.agent_name}:{self.agent_version}")
        logger.info(f"   Thread ID: {thread_id}")
        logger.info(f"   Model: {self.chat_deployment_name}")
        logger.info(f"   Endpoint: {self.foundry_endpoint}")
        logger.info(f"   Vector Store IDs: {self.vector_store_ids if hasattr(self, 'vector_store_ids') and self.vector_store_ids else 'None (using portal config)'}")
        
        # DON'T pass tools parameter - use portal configuration exclusively
        # The portal already has file search enabled with vector store attached
        # For ticket creation, we'll handle it through instructions and manual tool calling
        
        # Store EscalationComms URL for potential future use (not adding to tools_list)
        self._escalation_mcp_available = bool(self.escalation_comms_mcp_server_url)
        
        if self.escalation_comms_mcp_server_url:
            # print(f"📧 EscalationComms MCP URL configured: {self.escalation_comms_mcp_server_url}")
            # print(f"✅ Ticket creation will be handled through supervisor routing")
            logger.debug(f"📧 EscalationComms MCP available at: {self.escalation_comms_mcp_server_url}")
        
        # print(f"📋 Using portal configuration for file search (vector store attached to agent)")
        # print(f"📋 Agent ID {self.agent_id} has file search enabled in Azure AI Foundry portal")
        
        # Use agent name and version (agent must already exist in Azure AI Foundry portal)
        if not self.agent_name or not self.agent_version:
            raise ValueError("agent_name and agent_version are required - agent must be created in Azure AI Foundry portal first")
        
        # Use test credential if provided, otherwise get default
        if self.test_credential:
            credential = self.test_credential
        else:
            credential = await get_azure_credential_async()
        
        # Create AzureAIClient with agent name and version
        chat_client = AzureAIClient(
            project_client=self.foundry_project_client,
            agent_name=self.agent_name,
            agent_version=self.agent_version
        )
        
        # Create ChatAgent using create_agent() method
        chat_agent = chat_client.create_agent(
            name=AIMoneyCoachKnowledgeBaseAgent.name,
            instructions=AIMoneyCoachKnowledgeBaseAgent.instructions
        )
        
        print("✅ ChatAgent created successfully")
        print(f"   Agent Name: {chat_agent.name}")
        print(f"   Chat Client Type: {type(chat_agent.chat_client)}")
        print(f"   EscalationComms: {'✅ Available (via supervisor routing)' if self._escalation_mcp_available else '❌ Not configured'}")
        print(f"   Portal File Search: ✅ Should be active (configured in portal)")
        print(f"   ✅ INSTRUCTIONS: Passed explicitly ({len(AIMoneyCoachKnowledgeBaseAgent.instructions)} chars)")
        
        # Log the thread_id that will be used (or created)
        actual_thread_id = getattr(chat_agent.chat_client, 'thread_id', 'UNKNOWN')
        print(f"🧵 Thread ID (after creation): {actual_thread_id}")
        
        print("="*80 + "\n")
        
        logger.info("✅ ChatAgent created successfully")
        logger.info(f"   Agent Name: {chat_agent.name}")
        logger.info(f"   EscalationComms: {'Available via supervisor routing' if self._escalation_mcp_available else 'Not configured'}")
        logger.info(f"   Portal tools: File Search with Vector Store (configured in portal)")
        logger.info("="*80)
        
        # Cache the agent if thread_id is None (stateless requests)
        if thread_id is None:
            self._cached_chat_agent = chat_agent
            print(f"💾 [CACHE STORED] AIMoneyCoachAgent cached for future requests")
            logger.info("💾 AIMoneyCoachAgent cached - future requests will reuse this instance")
        
        return chat_agent
