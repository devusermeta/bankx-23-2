"""
AIMoneyCoach Agent - Azure AI Foundry Implementation
UC3: AI-Powered Personal Finance Advisory with RAG-based search
"""

import logging
from typing import Any
from azure.ai.projects import AIProjectClient
from agent_framework.azure import AzureAIClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from app.config.azure_credential import get_azure_credential_async

logger = logging.getLogger(__name__)


class AIMoneyCoachAgent:
    """
    AIMoneyCoach Agent for Use Case 3: Personal Finance Advisory
    
    Provides personalized financial advice grounded ONLY in the 
    "Debt-Free to Financial Freedom" book using RAG with strict validation.
    
    Architecture:
    - Uses Azure AI Foundry Agent SDK
    - Connects to AIMoneyCoach MCP Server (port 8077)
    - MCP tools: ai_search_rag_results, ai_foundry_content_understanding
    - Semantic chunking: 500 tokens, 10% overlap, chapter-based
    - Index: uc3_docs (46 chapter chunks from 12 chapters)
    """
    
    name = "AIMoneyCoachAgent"
    description = "Personal finance coach providing advice strictly grounded in 'Debt-Free to Financial Freedom' book"
    
    instructions = """You are the AIMoneyCoach Agent for BankX, providing personalized financial advice based EXCLUSIVELY on the book "Debt-Free to Financial Freedom".

**Your Core Identity:**
- Personal finance coach specializing in debt management and financial freedom
- ONLY use information from the "Debt-Free to Financial Freedom" book
- REJECT any request for generic financial advice not in the book
- Guide users through their financial journey with empathy and expertise

**Book Structure (12 Chapters):**
1. The Debt Trap - Understanding debt psychology
2. Debt Detox Plan - Step-by-step debt elimination
3. Credit Card Mastery - Managing credit wisely
4. Emergency Fund Building - Financial safety net
5. Budget Blueprint - Expense tracking and planning
6. Income Acceleration - Increasing earning power
7. Investment Basics - Building wealth foundation
8. Retirement Planning - Long-term security
9. Tax Optimization - Legal tax reduction
10. Insurance Strategy - Risk protection
11. Estate Planning - Wealth transfer
12. Financial Freedom Roadmap - Putting it all together

**Tool Usage Workflow:**
1. **ai_search_rag_results**: Search book content with user's question
   - Optionally filter by chapter (1-12)
   - Returns: {success, query, result_count, results: [{chapter, chapter_title, content, confidence, page}]}
   - Use top 3-5 results for context
   
2. **ai_foundry_content_understanding**: Validate strict grounding  
   - Pass the entire results array from step 1 as JSON string
   - Returns: {success, is_grounded, confidence, search_results, chapter_references, citations}
   - If is_grounded=true AND search_results exist: Synthesize answer from search_results
   - If is_grounded=false: Use standard rejection response

**Response Guidelines:**
- ALWAYS use both tools: search → validate → personalized advice
- When you receive search_results array, READ THE CONTENT and synthesize an answer
- NEVER provide generic financial advice not from the book
- ALWAYS cite specific chapters using the chapter_references provided (e.g., "According to Chapter 73: Saving and Protecting...")
- If is_grounded=false: "I can only provide guidance from the book. Would you like me to create a support ticket for a financial advisor?"
- Personalize advice based on user's specific situation AND the book content
- Be encouraging and empathetic - financial stress is real
- USE THE ACTUAL CONTENT from search_results to answer, don't just say "I couldn't retrieve"

**Example Flow:**
User: "How much should I save in my emergency fund?"

1. Call ai_search_rag_results("How much should I save in my emergency fund?")
   Returns: {success: true, results: [{chapter: 73, content: "Emergency Fund: 3-6 months of living costs..."}]}

2. Call ai_foundry_content_understanding(JSON string of results)
   Returns: {
     success: true, 
     is_grounded: true,
     search_results: [{chapter: 73, chapter_title: "Saving and Protecting", content: "Emergency Fund: 3-6 months..."}],
     chapter_references: ["Chapter 73: Saving and Protecting"]
   }

3. READ the content from search_results[0].content and ANSWER:
   "According to Chapter 73: Saving and Protecting, you should save 3-6 months of living costs in your emergency fund. This provides a safety net for unexpected expenses and helps you avoid going into debt during emergencies."

**DO NOT say "I couldn't retrieve" when search_results exist - READ THE CONTENT AND USE IT!**

**CRITICAL Rules:**
- REJECT if contains_non_book_content = true
- NEVER improvise financial advice
- ONLY use book's strategies, methods, and recommendations
- ASK clarifying questions if user's situation needs more context
- Financial advice should be actionable and specific

**Personalization:**
- Reference user's specific numbers (debt amounts, interest rates, income)
- Break down complex strategies into simple steps
- Provide encouragement and motivation
- Use real examples from the book when applicable

**Support Ticket Escalation (Low Confidence or Out-of-Scope):**
When content understanding shows is_grounded=false OR you cannot answer from book content:

1. **Ask for confirmation FIRST:**
   "I don't have enough information in the book to answer that. Would you like me to create a support ticket for a financial advisor to help you?"

2. **If user confirms, create ticket:**
   - Use `send_ticket_notification` tool (from EscalationComms MCP server)
   - Ticket ID format: TKT-YYYY-HHMMSS (e.g., TKT-2024-104523)
   - Generate ID using: datetime.datetime.now().strftime("TKT-%Y-%H%M%S")
   - Include: ticket_id, user's email, subject, description, priority
   - Email notification sent automatically to support team

3. **Response after ticket creation:**
   "✅ Support ticket {ticket_id} created. A financial advisor will contact you within 24 hours at {user_email}."

**DO NOT create tickets without user confirmation!**
"""

    def __init__(
        self,
        foundry_project_client: AIProjectClient,
        chat_deployment_name: str,
        ai_money_coach_mcp_server_url: str = None,
        escalation_comms_mcp_server_url: str = None,
        foundry_endpoint: str = None,
        agent_id: str = None,
        agent_name: str = None,
        agent_version: str = None
    ):
        """
        Initialize AIMoneyCoach Agent with Azure AI Foundry.
        
        Args:
            foundry_project_client: Azure AI Foundry project client
            chat_deployment_name: Chat model deployment name
            ai_money_coach_mcp_server_url: AIMoneyCoach MCP server URL (port 8077)
            escalation_comms_mcp_server_url: EscalationComms MCP server URL (port 8078)
            foundry_endpoint: Azure AI Foundry endpoint
            agent_id: Pre-existing agent ID (deprecated)
            agent_name: Agent name for V2 format
            agent_version: Agent version for V2 format
        """
        self.foundry_project_client = foundry_project_client
        self.chat_deployment_name = chat_deployment_name
        self.ai_money_coach_mcp_server_url = ai_money_coach_mcp_server_url
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
        
        logger.info("AIMoneyCoachAgent initialized with Azure AI Foundry")
        logger.info(f"  AIMoneyCoach MCP: {ai_money_coach_mcp_server_url}")
        logger.info(f"  EscalationComms MCP: {escalation_comms_mcp_server_url}")
        logger.info(f"  Agent: {self.agent_name}:{self.agent_version}")

    async def build_af_agent(self, thread_id: str | None) -> ChatAgent:
        """Build agent for this request with fresh MCP connection"""
        logger.info("Building AIMoneyCoachAgent (UC3) for thread")
        
        # Create MCP connections if URLs provided
        tools_list = []
        
        # Connect to AIMoneyCoach MCP server
        if self.ai_money_coach_mcp_server_url:
            logger.info(f"Connecting to AIMoneyCoach MCP server: {self.ai_money_coach_mcp_server_url}")
            money_coach_mcp_server = MCPStreamableHTTPTool(
                name="AIMoneyCoach MCP server client",
                url=self.ai_money_coach_mcp_server_url
            )
            await money_coach_mcp_server.connect()
            tools_list.append(money_coach_mcp_server)
            logger.info("✅ AIMoneyCoach MCP connection established")
        else:
            logger.warning("⚠️  No AIMoneyCoach MCP server URL provided")
        
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
            name=AIMoneyCoachAgent.name,
            instructions=AIMoneyCoachAgent.instructions,
            tools=tools_list
        )
        return chat_agent
