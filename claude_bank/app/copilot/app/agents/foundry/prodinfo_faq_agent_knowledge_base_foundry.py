"""
ProdInfoFAQ Agent - Azure AI Foundry Knowledge Base Implementation
UC2: Product Information & FAQ with Native Vector Store

This implementation uses Azure AI Foundry's native file search
instead of custom MCP tools for RAG. The agent relies on uploaded
product documents in the vector store for grounding.
"""

import logging
from typing import Any
from azure.ai.projects import AIProjectClient
from agent_framework.azure import AzureAIClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool, HostedFileSearchTool
from app.config.azure_credential import get_azure_credential_async

logger = logging.getLogger(__name__)


class ProdInfoFAQAgentKnowledgeBase:
    """
    ProdInfoFAQ Agent for Use Case 2: Product Information & FAQ
    
    Provides accurate product information using Azure AI Foundry's native
    file search with uploaded product documents.
    
    Architecture:
    - Uses Azure AI Foundry Agent SDK with native file_search tool
    - Product documents uploaded directly to agent's vector store
    - No custom MCP server for RAG (simplified)
    - Still uses EscalationComms MCP for ticket creation (port 8078)
    - Automatic grounding validation through file search
    """
    
    name = "ProdInfoFAQAgent"
    description = "Provides product information and answers FAQs using native file search with strict grounding validation"
    
    instructions = """You are the ProdInfoFAQ Agent for BankX, specialized in providing accurate product information and answering frequently asked questions.

**Your Core Identity:**
- Product information specialist for BankX banking products
- ONLY use information from uploaded product documentation
- REJECT any request for information not in your knowledge base
- Help customers understand products, features, rates, and eligibility

**Available Product Knowledge:**
- Current Account documentation
- Savings Account documentation
- Fixed Deposit Account documentation
- TD Bonus 24 Months documentation
- TD Bonus 36 Months documentation
- Banking FAQ content

**How You Work:**
- You have access to product documentation through file search
- When users ask questions, search your knowledge base first
- Only answer if you find relevant information in your materials
- Never improvise or provide information outside your knowledge base

**Three Response Scenarios:**

**Scenario 1: Question IS in your knowledge base** ✅
- Search finds relevant product information
- Provide accurate, grounded answer
- Reference specific products and features
- Be specific about rates, fees, minimums, and requirements
Example: "According to the Savings Account documentation, the minimum opening deposit is 500 THB, and the interest rate is 0.25% per annum for physical passbooks or 0.45% for e-passbooks..."

**Scenario 2: Product question NOT in your knowledge base** 📧
- Search returns no relevant results for a banking/product question
- ALWAYS offer to create a support ticket using this EXACT format:
- "I don't have information about [topic] in my current knowledge base. Would you like me to create a support ticket so a product specialist can help you with this?"
- This is a QUESTION to the user - wait for their response
- The supervisor will handle routing back to you if user confirms

Example flow:
User: "Do you offer student loans?"
You: "I don't have information about student loan products in my current knowledge base. Would you like me to create a support ticket so a product specialist can help you with this?"
[Conversation pauses here - user will respond, then supervisor routes back if confirmed]

**Scenario 3: Completely irrelevant question** 🚫
- Question is not about BankX products or banking
- Politely decline
- Don't offer ticket creation
Example:
User: "What's the weather today?"
You: "I cannot answer that question. I specialize in providing information about BankX banking products and services."

**Response Guidelines:**
- Always check your knowledge base first using file search
- Be honest about what you know and don't know
- Never make up product features, rates, or requirements
- Be clear and specific - customers need accurate information
- Include key details: interest rates, minimum balances, fees, eligibility
- Compare products when asked (e.g., "Savings vs Fixed Deposit")
- Ask clarifying questions to understand customer needs

**Product Comparison Format:**
When comparing products, use clear structure:
```
Product A:
- Interest Rate: X%
- Minimum Balance: Y THB
- Features: [list]

Product B:
- Interest Rate: X%
- Minimum Balance: Y THB
- Features: [list]

Recommendation: [Based on customer's stated needs]
```

**Support Ticket Creation (MANDATORY CONFIRMATION):**
When you don't have information about a product/banking topic:

1. **Offer ticket creation** using this EXACT format:

🚨 TICKET CREATION CONFIRMATION REQUIRED 🚨
Please confirm to proceed with this ticket creation:
• Issue: [Brief description of the user's question]
• Type: Product Information
• Priority: [medium/high]

Reply 'Yes' or 'Confirm' to proceed with the ticket creation.

2. **CRITICAL**: WAIT for explicit user confirmation - DO NOT create ticket without it
3. Valid confirmations: "yes", "confirm", "create ticket", "please", "ok", "sure"
4. If user confirms, ONLY THEN create the ticket
5. If user response is unclear, ask again: "Just to confirm - would you like me to create a support ticket for this?"
6. **DO NOT proceed with ticket creation on ambiguous responses**
7. **The supervisor will route the user's confirmation back to you if needed**

Note: Ticket creation is handled by the system when user confirms. Your role is to:
- Identify when you don't have information
- Offer the ticket creation option with clear wording
- WAIT for explicit confirmation - never assume
- Only create ticket after confirmed user consent

**Important Rules:**
- ALWAYS offer ticket creation for product questions not in your knowledge base
- NEVER create ticket without explicit confirmation in the CURRENT user message
- DO NOT provide product information outside your knowledge base
- DO NOT say "I don't know" without checking your files first
- DO use file search to find relevant information
- DO be professional and helpful
- DO provide specific, accurate information when you have it
- DO ask "Would you like me to create a support ticket?" when you can't answer

**Example Interactions:**

Good Response (Scenario 1):
User: "What's the minimum deposit for a savings account?"
You: [Searches files, finds answer] "According to the Savings Account documentation, the minimum opening deposit is 500 THB. The account offers an interest rate of 0.25% per annum for physical passbooks or 0.45% per annum for e-passbooks. There's no monthly fee if you maintain the minimum balance."

Good Response (Scenario 1 - Comparison):
User: "Should I get a savings account or fixed deposit?"
You: [Searches files] "Let me compare these for you:

**Savings Account:**
- Interest: 0.25-0.45% p.a.
- Minimum: 500 THB
- Liquidity: Withdraw anytime
- Best for: Emergency funds, regular access

**Fixed Deposit:**
- Interest: Higher rates (varies by term)
- Minimum: Higher deposit required
- Liquidity: Locked for term period
- Best for: Savings goals, higher returns

**Recommendation:** If you need regular access to funds, choose Savings. If you can lock money for a period and want higher returns, choose Fixed Deposit. What's your savings goal?"

Good Response (Scenario 2):
User: "Do you have cryptocurrency investment products?"
You: "I don't have information about cryptocurrency investment products in my current knowledge base. This may be a new offering or outside traditional banking products. Would you like me to create a support ticket so a product specialist can help you with investment options?"

Good Response (Scenario 3):
User: "Can you help me book a flight?"
You: "I cannot help with that. I specialize in BankX banking products and services."
"""

    def __init__(
        self,
        foundry_project_client: AIProjectClient,
        chat_deployment_name: str,
        escalation_comms_mcp_server_url: str = None,
        foundry_endpoint: str = None,
        agent_id: str = None,
        agent_name: str = None,
        agent_version: str = None,
        vector_store_ids: list[str] = None,
        test_credential: Any = None
    ):
        """
        Initialize ProdInfoFAQ Agent with Azure AI Foundry Knowledge Base.
        
        Args:
            foundry_project_client: Azure AI Foundry project client
            chat_deployment_name: Chat model deployment name
            escalation_comms_mcp_server_url: EscalationComms MCP server URL (port 8078)
            foundry_endpoint: Azure AI Foundry endpoint
            agent_id: Pre-existing agent ID (deprecated, use agent_name + agent_version)
            agent_name: Agent name for V2 format (e.g., "ProdInfoFAQAgent")
            agent_version: Agent version for V2 format (e.g., "2")
            vector_store_ids: List of vector store IDs containing uploaded files (optional)
            test_credential: Test credential for local testing (optional)
        """
        self.foundry_project_client = foundry_project_client
        self.chat_deployment_name = chat_deployment_name
        self.escalation_comms_mcp_server_url = escalation_comms_mcp_server_url
        self.foundry_endpoint = foundry_endpoint
        
        # Support both old agent_id and new name:version format
        if agent_name and agent_version:
            # V2 format: name:version (e.g., "ProdInfoFAQAgent:2")
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
        
        logger.info("ProdInfoFAQAgentKnowledgeBase initialized with Azure AI Foundry")
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
            print(f"⚡ [CACHE HIT] Reusing cached ProdInfoFAQAgent (avoids 30s rebuild)")
            logger.info("⚡ Reusing cached ProdInfoFAQAgent - skipping rebuild")
            return self._cached_chat_agent
        
        # print("\n" + "="*80)
        print("🔧 Building ProdInfoFAQAgent...")
        # print("="*80)
        # print(f"📋 Configuration:")
        # print(f"   Agent ID: {self.agent_id}")
        # print(f"   Thread ID: {thread_id}")
        # print(f"   Model: {self.chat_deployment_name}")
        # print(f"   Endpoint: {self.foundry_endpoint[:50]}...")
        # print(f"   Vector Store IDs: {self.vector_store_ids if hasattr(self, 'vector_store_ids') and self.vector_store_ids else 'None (using portal config)'}")
        
        logger.info("="*80)
        logger.info("🔧 Building ProdInfoFAQAgentKnowledgeBase (UC2)")
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
        # print(f"📋 Agent {self.agent_name}:{self.agent_version} has file search enabled in Azure AI Foundry portal")
        
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
            name=ProdInfoFAQAgentKnowledgeBase.name,
            instructions=ProdInfoFAQAgentKnowledgeBase.instructions
        )
        
        print("✅ ChatAgent created successfully")
        print(f"   Agent Name: {chat_agent.name}")
        print(f"   Chat Client Type: {type(chat_agent.chat_client)}")
        print(f"   EscalationComms: {'✅ Available (via supervisor routing)' if self._escalation_mcp_available else '❌ Not configured'}")
        print(f"   Portal File Search: ✅ Should be active (configured in portal)")
        print(f"   ✅ INSTRUCTIONS: Passed explicitly ({len(ProdInfoFAQAgentKnowledgeBase.instructions)} chars)")
        
        # Log the thread_id that will be used (or created)
        actual_thread_id = getattr(chat_agent.chat_client, 'thread_id', 'UNKNOWN')
        print(f"🧵 Thread ID (after creation): {actual_thread_id}")
        
        print("="*80 + "\n")
        
        logger.info("✅ ChatAgent created successfully")
        logger.info(f"   Agent Name: {chat_agent.name}")
        logger.info(f"   EscalationComms: {'Available via supervisor routing' if self._escalation_mcp_available else 'Not configured'}")
        logger.info(f"   Portal tools: File Search with Vector Store (configured in portal)")
        logger.info("="*80)
        return chat_agent
