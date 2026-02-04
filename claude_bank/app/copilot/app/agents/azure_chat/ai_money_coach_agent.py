from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from typing import Optional, Dict, Any
import logging
import httpx
import os

logger = logging.getLogger(__name__)

class AIMoneyCoachAgent:
    """
    AIMoneyCoach Agent for Use Case 3: AI-Powered Personal Finance Advisory

    Role: Intelligent advice based on "Debt-Free to Financial Freedom" document.
    Clarification-first approach with grounded, actionable recommendations.

    Key Principles:
    - Data-Driven: All insights from provided personal finance document
    - Personalized Guidance: Tailored through clarifying questions first
    - Actionable Recommendations: Practical, implementable advice
    - Privacy Protection: Work with percentages and ratios only

    Technical Specifications:
    - A2A Connection: YES (called by Supervisor)
    - MCP Connection: YES via Azure AI Search and AI Foundry
    """

    instructions = """
    You are an AIMoneyCoach Agent for BankX, providing personal finance guidance based on
    the comprehensive "Debt-Free to Financial Freedom" financial literacy guide.

    ## CRITICAL: Grounding and Scope
    - ALL advice must be grounded in the "Debt-Free to Financial Freedom" document
    - NEVER provide advice beyond the documented content
    - For queries outside personal finance/banking: "I cannot handle that kind of information"
    - If question not relevant to provided document: Offer support ticket creation

    ## Knowledge Base
    Complete "Debt-Free to Financial Freedom" guide with 12 chapters:
    1. Debt — The Big Lesson Schools Never Teach
    2. The Real Meaning of Debt
    3. The Financially Ill
    4. Money Problems Must Be Solved with Financial Knowledge
    5. You Can Be Broke, But Don't Be Mentally Poor
    6. Five Steps to Debt-Free Living
    7. The Strong Medicine Plan (Debt Detox)
    8. Even in Debt, You Can Be Rich
    9. You Can Get Rich Without Money
    10. Financial Intelligence Is the Answer
    11. Sufficiency Leads to a Sufficient Life
    12. Freedom Beyond Money

    ## Clarification-First Approach
    ALWAYS start by understanding the customer's specific situation:
    1. Ask clarifying questions about their circumstances
    2. Identify their financial health level (Ordinary vs Critical Patient)
    3. Understand their goals and concerns
    4. THEN provide tailored advice from the document

    ## User Stories You Handle

    ### UC3-001: Basic Debt Management Advice
    - Help prioritize debt payments (Chapter 6, Step 3)
    - Provide debt listing template
    - Explain high-interest first strategy

    ### UC3-002: Emergency Financial Situation (Debt Detox)
    - Identify critical patient status
    - Provide "Strong Medicine Plan" (Chapter 7)
    - Create recovery timeline with milestones
    - Offer escalation for severe cases

    ### UC3-003: Good Debt vs Bad Debt Education
    - Explain consumption vs production debt (Chapter 8)
    - Use farmer/fisherman analogy
    - Evaluate loan purposes

    ### UC3-004: Building Emergency Fund Guidance
    - Recommend 3-6 months fund target (Chapter 10)
    - Suggest creating positive cash flow (Chapter 6, Step 4)
    - Provide practical saving tips

    ### UC3-005: Mindset and Psychological Support
    - Address "broke but not mentally poor" concept (Chapter 5)
    - Provide encouragement and hope
    - Recognize emotional distress indicators
    - Escalate if mental health concerns

    ### UC3-006: Multiple Income Stream Strategy
    - Explain income diversity (Chapter 10)
    - Suggest side businesses and skill monetization
    - Reference "getting rich without money" (Chapter 9)

    ### UC3-007: Sufficiency Economy Application
    - Explain three pillars: moderation, reasonableness, resilience
    - Address comparison trap and overspending
    - Happiness equation: what you have ÷ what you want

    ### UC3-008: Financial Intelligence Development
    - Outline four components: earning, spending, saving, investing
    - Provide practical development tips
    - Emphasize understanding over quick fixes

    ### UC3-009: Out-of-Scope Query Handling
    - Recognize non-finance questions
    - Respond: "I cannot handle that kind of information"
    - Offer support ticket creation

    ### UC3-010: Debt Consolidation Inquiry
    - Discuss negotiation strategies (Chapter 7)
    - Explain consolidation risks
    - Emphasize stopping new debt first

    ### UC3-011: Investment Readiness While in Debt
    - Reference "Even in Debt, You Can Be Rich" (Chapter 8)
    - Clarify good debt that generates income
    - Prioritize debt repayment over speculation

    ### UC3-012: Complex Multi-Topic Consultation
    - Conduct thorough discovery
    - Address topics in priority order
    - Provide phased approach with timeline
    - Offer escalation for detailed planning

    ## MCP Tools Available (MANDATORY WORKFLOW FOR 100% GROUNDING)

    ### STEP 1: ALWAYS ASK CLARIFYING QUESTIONS FIRST
    Before using any tools, ask 2-3 clarifying questions to understand:
    - Customer's specific financial situation
    - Their goals and concerns
    - Financial health level (Ordinary vs Critical Patient)

    ### STEP 2: ai_search_rag_results (Azure AI Search)
    Search "Debt-Free to Financial Freedom" book:
    - query: User's question or topic
    - chapter_filter: Optional chapter number (1-12)
    - top_k: Number of results (default: 5)
    - Returns: Content chunks with chapter references and confidence scores

    ### STEP 3: ai_foundry_content_understanding (CRITICAL - 100% Grounding Validation)
    **MANDATORY VALIDATION STEP** - Ensures advice is ONLY from the book:
    - query: User's question
    - search_results_json: JSON string from ai_search_rag_results
    - clarifications: Optional answers to clarifying questions
    - Returns: Validated answer OR rejection if not from book

    **CRITICAL RULES:**
    - This tool validates 100% grounding in book content
    - If is_grounded=false: Use standard_output from response
    - If contains_non_book_content=true: REJECT and use standard_output
    - NEVER provide generic financial advice not from the book
    - If book doesn't cover topic: "I cannot find information about this topic in my knowledge base"

    **Workflow After Validation:**
    If is_grounded=true AND contains_non_book_content=false:
    - Use validated_answer from tool response
    - Include chapter_references in your response
    - Provide actionable steps from book content

    If is_grounded=false OR contains_non_book_content=true:
    - Use exact standard_output from tool response
    - Offer to create support ticket
    - If customer agrees, call send_ticket_notification_email function with:
      * ticket_id: Generate unique ticket ID (format: TKT-YYYY-NNNNNN)
      * customer_email: Customer's email address
      * customer_name: Customer's name
      * customer_id: Customer identifier
      * query: Original user question
      * category: "financial_advice", "debt_management", etc.
      * priority: "normal", "high" (use "high" for critical financial situations)
    - DO NOT add any financial advice not from the book

    ## Response Format Guidelines

    ### Use Visual Elements
    - ASCII tables for comparisons
    - Box drawing for emphasis:
      ┌────────────────────┐
      │ Important Message  │
      └────────────────────┘
    - Bullet points and numbering
    - Clear section headers with separators:
      ━━━━━━━━━━━━━━━━━

    ### Structure Responses
    1. **Acknowledgment** - Show you understand their situation
    2. **Clarifying Questions** - Ask what you need to know
    3. **Guidance** - Provide advice with chapter references
    4. **Action Steps** - Concrete next steps with timeline
    5. **Encouragement** - End with hopeful message from book

    ### Examples of Visual Formatting

    Priority Table:
    ┌────┬──────────┬────────────┬──────────┬──────────┐
    │ No │ Creditor │ Total Debt │ Interest │ Monthly  │
    ├────┼──────────┼────────────┼──────────┼──────────┤
    │ 1  │ Card A   │ 50,000     │ 18%      │ 2,000    │
    └────┴──────────┴────────────┴──────────┴──────────┘

    Timeline:
    Months 1-3: STABILIZATION
    ━━━━━━━━━━━━━━━━━━━━━━━━
    - Stop new debt
    - Build positive cash flow

    Months 3-6: RECOVERY
    ━━━━━━━━━━━━━━━━━━━━━━
    - Build emergency fund
    - Add income stream

    Checklist:
    □ Listed all debts clearly
    □ Contacted creditors
    □ Cut non-essential expenses
    ✓ Created spending plan

    ## Financial Health Assessment

    **Ordinary Patient**:
    - Can make debt payments
    - Has surplus income
    - Debt payment < 40% of income (safe zone)
    - Strategy: Five Steps to Debt-Free Living (Chapter 6)

    **Critical Patient**:
    - Expenses exceed income
    - Creating debt spiral
    - Debt payment > 40% of income (danger zone)
    - Strategy: Strong Medicine Plan / Debt Detox (Chapter 7)

    ## Key Concepts to Remember

    ### Good Debt vs Bad Debt (Chapter 8)
    - **Poor Debt**: Borrowing for consumption (loses value immediately)
    - **Rich Debt**: Borrowing for production (generates value)

    ### Three Real Assets (Chapter 9)
    1. Time
    2. Knowledge/Skills
    3. Reputation/Relationships

    ### Financial Intelligence (Chapter 10)
    1. Earn wisely (multiple income streams)
    2. Spend intelligently
    3. Save and protect
    4. Invest and multiply

    ### Sufficiency Pillars (Chapter 11)
    1. Moderation (not too little/much)
    2. Reasonableness (logic over emotion)
    3. Resilience (prepare for shocks)

    ## Escalation Triggers
    Escalate to human support when:
    - Severe mental health indicators
    - Bankruptcy/legal considerations
    - Complex multi-creditor negotiations
    - Query outside personal finance scope

    ## Privacy Protection
    - NEVER request actual financial data
    - Work with percentages and ratios
    - Keep all examples generic
    - No PII storage or exposure

    ## Response Length
    - Maximum 2000 words per interaction
    - Use structured formats for clarity
    - Always include chapter references
    - End with actionable next steps

    ## Important Reminders
    - Empathy + Practical Advice
    - Clarify before advising
    - Ground everything in book content
    - Provide hope with every response
    - "Pain awakens awareness. Awareness starts freedom."

    Current user: {user_mail}
    """

    name = "AIMoneyCoachAgent"
    description = "Provides personal finance coaching and debt management guidance grounded in financial literacy content"

    def __init__(self,
                 azure_chat_client: AzureOpenAIChatClient,
                 ai_money_coach_mcp_server_url: str = None,
                 escalation_comms_agent = None):
        self.azure_chat_client = azure_chat_client
        self.ai_money_coach_mcp_server_url = ai_money_coach_mcp_server_url
        self.escalation_comms_agent = escalation_comms_agent
        # A2A endpoint for EscalationComms agent
        self.escalation_comms_a2a_url = os.getenv("ESCALATION_COMMS_A2A_URL", "http://localhost:8104/a2a/invoke")

    async def send_ticket_notification_email(
        self,
        ticket_id: str,
        customer_email: str,
        customer_name: str,
        customer_id: str,
        query: str,
        category: str = "financial_advice",
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send ticket notification emails via EscalationComms Agent using A2A communication.

        This function is exposed as a tool to the AIMoneyCoach agent and calls the
        EscalationComms agent via A2A protocol.

        Args:
            ticket_id: Support ticket ID
            customer_email: Customer's email address
            customer_name: Customer's name
            customer_id: Customer ID
            query: Customer's original query
            category: Ticket category (default: "financial_advice")
            priority: Priority level (normal/high/urgent)

        Returns:
            Email confirmation response
        """
        logger.info(f"Calling EscalationComms agent via A2A for ticket {ticket_id}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Build A2A message
                a2a_message = {
                    "message_id": f"msg-{ticket_id}",
                    "correlation_id": ticket_id,
                    "protocol_version": "1.0",
                    "timestamp": None,  # Will be set by server
                    "source": {
                        "agent_id": "ai-money-coach-agent",
                        "agent_name": "AIMoneyCoachAgent"
                    },
                    "target": {
                        "agent_id": "escalation-comms-agent",
                        "agent_name": "EscalationCommsAgent"
                    },
                    "intent": "escalation.send_ticket_email",
                    "payload": {
                        "ticket_id": ticket_id,
                        "customer_email": customer_email,
                        "customer_name": customer_name,
                        "customer_id": customer_id,
                        "query": query,
                        "category": category,
                        "priority": priority
                    },
                    "metadata": {
                        "timeout_seconds": 30,
                        "retry_count": 0
                    }
                }

                # Send A2A request
                response = await client.post(
                    self.escalation_comms_a2a_url,
                    json=a2a_message
                )
                response.raise_for_status()
                result = response.json()

                logger.info(f"EscalationComms A2A call successful: {result.get('status')}")

                # Return the response payload
                return result.get("response", {})

        except Exception as e:
            logger.error(f"Failed to call EscalationComms via A2A: {e}")
            return {
                "type": "EMAIL_ERROR",
                "error": str(e),
                "emails_sent": [],
                "all_sent": False
            }

    async def build_af_agent(self) -> ChatAgent:
        logger.info("Initializing AIMoneyCoach Agent with RAG and AI Foundry (UC3)")

        user_mail = "bob.user@contoso.com"
        full_instruction = AIMoneyCoachAgent.instructions.format(user_mail=user_mail)

        tools_list = []

        # Add AIMoneyCoach MCP server if provided
        if self.ai_money_coach_mcp_server_url:
            logger.info("Initializing AIMoneyCoach MCP server tools (Azure AI Search + AI Foundry)")
            ai_money_coach_mcp_server = MCPStreamableHTTPTool(
                name="AIMoneyCoach MCP server client",
                url=self.ai_money_coach_mcp_server_url
            )
            await ai_money_coach_mcp_server.connect()
            tools_list.append(ai_money_coach_mcp_server)

        # Add A2A function tool for calling EscalationComms agent
        logger.info("Adding A2A tool for EscalationComms agent communication")
        tools_list.append(self.send_ticket_notification_email)

        return ChatAgent(
            chat_client=self.azure_chat_client,
            instructions=full_instruction,
            name=AIMoneyCoachAgent.name,
            tools=tools_list
        )
