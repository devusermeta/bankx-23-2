"""
ProdInfoFAQ Agent - Azure AI Foundry Implementation
UC2: Product Information & FAQ with RAG-based search
"""

import logging
from typing import Any
from azure.ai.projects import AIProjectClient
from agent_framework.azure import AzureAIClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from app.config.azure_credential import get_azure_credential_async

logger = logging.getLogger(__name__)


class ProdInfoFAQAgent:
    """
    ProdInfoFAQ Agent for Use Case 2: Product Information & FAQ
    
    Provides accurate product information using RAG with Azure AI Search and
    Content Understanding for 100% grounding validation.
    
    Architecture:
    - Uses Azure AI Foundry Agent SDK
    - Connects to ProdInfoFAQ MCP Server (port 8076)
    - MCP tools: search_documents, get_content_understanding
    - Semantic chunking: 500 tokens, 10% overlap
    - Index: uc2_docs (39 product documents)
    """
    
    name = "ProdInfoFAQAgent"
    description = "Provides product information and answers FAQs using RAG-based search with strict grounding validation"
    
    instructions = """You are the ProdInfoFAQ Agent for BankX, specialized in providing accurate product information and answering frequently asked questions.

**Your Core Responsibilities:**
1. Answer questions about BankX products (accounts, deposits, loans)
2. Provide accurate product features, rates, and eligibility criteria
3. Use RAG-based search to retrieve relevant product documentation
4. Validate all answers with Content Understanding for 100% grounding
5. Create support tickets when information is not available

**Available Products:**
- Current Account
- Savings Account
- Fixed Deposit Account
- TD Bonus 24 Months
- TD Bonus 36 Months

**Tool Usage Workflow:**
1. **search_documents**: Search product knowledge base with user's query
   - Returns: Relevant document chunks with confidence scores
   - Use top 3-5 results for context
   
2. **get_content_understanding**: Validate grounding before answering
   - Pass search results as JSON string
   - Returns either validated_answer OR search_results array
   - **CRITICAL**: If validated_answer is null/None, READ the search_results array
   - Only answer if confidence >= 0.3
   - Include citations from source documents
   
3. **write_to_cosmosdb**: Create ticket if answer not found (confidence < 0.3)
   - Generate ticket ID in format: TKT-2024-NNNNNN
   - Store ticket with customer query and metadata
   
4. **send_ticket_notification**: Send email notification after ticket creation
   - Call IMMEDIATELY after write_to_cosmosdb
   - Use customer email from context (or use "customer@bankx.com" for demo)
   - Sends email to customer with ticket ID and CC to support team
   - Provide ticket ID to customer in your response

**Response Guidelines:**
- ALWAYS use both tools in sequence: search → validate → answer
- **When Content Understanding returns search_results**: READ the content field from each result and synthesize the answer yourself
- **Example**: If search_results contains [{"content": "Minimum balance: $100", "source": "Savings.pdf"}], extract the answer "$100" from the content
- ALWAYS cite source documents (e.g., "According to Current Account documentation...")
- If grounding confidence < 0.3, create support ticket instead
- Be concise but thorough - include key details like rates, fees, requirements
- **DO NOT** say "I couldn't retrieve" when search_results exist - READ THE CONTENT AND USE IT!

**Ticket ID Generation:**
- Format: TKT-YYYYMMDD-NNNNNN (e.g., TKT-20251112-000123) — a per-day sequential ID.
- The system will auto-generate the ticket ID when creating a ticket. Do NOT invent your own IDs.
- Flow: when confidence < 0.3, ASK the user for confirmation. If the user confirms, call write_to_cosmosdb with confirmed=True and let the service generate the ticket id.

**Example Flow:**
User: "What is the minimum balance for a savings account?"
1. Call search_documents with query
2. Call get_content_understanding with search results
3. If grounded (confidence >= 0.3): Answer with citation
4. If not grounded (confidence < 0.3):
   a. ASK USER: "I couldn't find this information. Would you like me to create a support ticket for further assistance?"
   b. If user confirms (says yes/ok/sure/please):
      - Generate ticket ID: TKT-YYYY-HHMMSS using current timestamp
      - Call write_to_cosmosdb to create ticket
      - Call send_ticket_notification to email customer
      - Tell customer: "I've created ticket [ID] and sent you an email confirmation"
   c. If user declines: "No problem!"

**Important:**
- You MUST validate every answer with Content Understanding
- Do NOT improvise or use general banking knowledge
- ONLY use information from the search results
- Products change over time - always search for current information
"""

    def __init__(
        self,
        foundry_project_client: AIProjectClient,
        chat_deployment_name: str,
        prodinfo_faq_mcp_server_url: str = None,
        escalation_comms_mcp_server_url: str = None,
        foundry_endpoint: str = None,
        agent_id: str = None,
        agent_name: str = None,
        agent_version: str = None
    ):
        """
        Initialize ProdInfoFAQ Agent with Azure AI Foundry.
        
        Args:
            foundry_project_client: Azure AI Foundry project client
            chat_deployment_name: Chat model deployment name
            prodinfo_faq_mcp_server_url: ProdInfoFAQ MCP server URL (port 8076)
            escalation_comms_mcp_server_url: EscalationComms MCP server URL (port 8078)
            foundry_endpoint: Azure AI Foundry endpoint
            agent_id: Pre-existing agent ID (deprecated)
            agent_name: Agent name for V2 format
            agent_version: Agent version for V2 format
        """
        self.foundry_project_client = foundry_project_client
        self.chat_deployment_name = chat_deployment_name
        self.prodinfo_faq_mcp_server_url = prodinfo_faq_mcp_server_url
        self.escalation_comms_mcp_server_url = escalation_comms_mcp_server_url
        self.foundry_endpoint = foundry_endpoint
        
        # Support both old agent_id and new name:version format
        if agent_name and agent_version:
            self.agent_name = agent_name
            self.agent_version = agent_version
            logger.info(f"✅ Using V2 format: {agent_name}:{agent_version}")
        elif agent_id:
            if ":" in agent_id:
                parts = agent_id.split(":", 1)
                self.agent_name = parts[0]
                self.agent_version = parts[1]
                logger.info(f"✅ Parsed V2 format from agent_id: {self.agent_name}:{self.agent_version}")
            else:
                raise ValueError(f"Old agent_id format '{agent_id}' not supported. Use agent_name and agent_version instead.")
        else:
            raise ValueError("Either (agent_name + agent_version) or agent_id must be provided")
        
        self._agent = None
        
        logger.info("ProdInfoFAQAgent initialized with Azure AI Foundry")
        logger.info(f"  ProdInfoFAQ MCP Server: {prodinfo_faq_mcp_server_url}")
        logger.info(f"  EscalationComms MCP Server: {escalation_comms_mcp_server_url}")
        logger.info(f"  Agent: {self.agent_name}:{self.agent_version}")

    async def build_af_agent(self, thread_id: str | None) -> ChatAgent:
        """Build agent for this request with fresh MCP connection"""
        logger.info("Building ProdInfoFAQAgent (UC2) for thread")
        
        # Create MCP connections for both ProdInfoFAQ and EscalationComms servers
        tools_list = []
        
        # Connect to ProdInfoFAQ MCP server
        if self.prodinfo_faq_mcp_server_url:
            logger.info(f"Connecting to ProdInfoFAQ MCP server: {self.prodinfo_faq_mcp_server_url}")
            prodinfo_mcp_server = MCPStreamableHTTPTool(
                name="ProdInfoFAQ MCP server client",
                url=self.prodinfo_faq_mcp_server_url
            )
            await prodinfo_mcp_server.connect()
            tools_list.append(prodinfo_mcp_server)
            logger.info("✅ ProdInfoFAQ MCP connection established")
        else:
            logger.warning("⚠️  No ProdInfoFAQ MCP server URL provided")
        
        # Connect to EscalationComms MCP server
        if self.escalation_comms_mcp_server_url:
            logger.info(f"Connecting to EscalationComms MCP server: {self.escalation_comms_mcp_server_url}")
            escalation_mcp_server = MCPStreamableHTTPTool(
                name="EscalationComms MCP server client",
                url=self.escalation_comms_mcp_server_url
            )
            await escalation_mcp_server.connect()
            tools_list.append(escalation_mcp_server)
            logger.info("✅ EscalationComms MCP connection established")
        else:
            logger.warning("⚠️  No EscalationComms MCP server URL provided")
        
        # Get or create agent if needed (V2 format: name:version)
        if not self._agent:
            # Azure AI Foundry V2: Use name:version format
            # Agent must already exist in Azure AI Foundry portal
            agent_version = "1"
        
        credential = await get_azure_credential_async()
        
        # Create AzureAIClient with agent name and version
        chat_client = AzureAIClient(
            project_client=self.foundry_project_client,
            agent_name=self.agent_name,
            agent_version=self.agent_version
        )
        
        # Create ChatAgent using create_agent() method with tools
        chat_agent = chat_client.create_agent(
            name=ProdInfoFAQAgent.name,
            instructions=ProdInfoFAQAgent.instructions,
            tools=tools_list
        )
        return chat_agent
