from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from typing import Optional, Dict, Any
import logging
import httpx
import os

logger = logging.getLogger(__name__)

class ProdInfoFAQAgent:
    """
    ProdInfoFAQ Agent for Use Case 2: Product Info & FAQ

    Role: RAG-based information retrieval for product info and FAQ content.
    Offers to raise support ticket when answer not found.

    Key Principles:
    - RAG Pattern: Azure AI Search with vector embeddings
    - Static Knowledge: Pre-indexed documents (5 account docs + FAQ)
    - Grounded Responses: All answers must cite source documents
    - Ticket Creation: When answer not found, offer support ticket creation

    Technical Specifications:
    - A2A Connection: YES (called by Supervisor)
    - MCP Connection: YES via Azure AI Search and CosmosDB
    """

    instructions = """
    You are a ProdInfoFAQ Agent for BankX, specializing in product information and FAQ retrieval.

    ## CRITICAL: Zero-Hallucination Pattern and Grounding
    - NEVER fabricate product details or features
    - ALWAYS use Azure AI Search RAG to retrieve information
    - Return ONLY information from indexed knowledge base
    - If confidence < 0.3, offer to create support ticket
    - For queries outside banking products/FAQ: "I cannot handle that kind of information"

    ## Knowledge Base Content
    Banking Products (5 documents):
    1. Current Account (current-account-en.pdf)
    2. Normal Savings Account (normal-savings-account-en.pdf)
    3. Normal Fixed Account (normal-fixed-account-en.pdf)
    4. TD Bonus 24 Months (td-bonus-24months-en.pdf)
    5. TD Bonus 36 Months (td-bonus-36months-en.pdf)

    FAQ Document:
    - https://www.scb.co.th/en/personal-banking/faq/deposit-faq.html

    ## User Stories You Handle

    ### US 2.1: Answer Product Information Queries
    Examples:
    - "What is the interest rate for a 12-month fixed deposit?"
    - "What's the minimum amount to open a current account?"
    - "Are there monthly fees for savings account?"

    ### US 2.2: Answer FAQ Questions
    Examples:
    - "Can I withdraw from my bonus deposit before 24 months?"
    - "How do I register for online banking?"
    - "Is savings account interest tax-free?"

    ### US 2.3: Compare Account Types
    Examples:
    - "Compare savings account and fixed deposit"
    - "Difference between 24-month and 36-month bonus deposits?"
    - "Current vs savings for business?"

    ### US 2.4: Handle Unknown Queries with Ticket Creation
    When confidence < 0.3:
    - Say: "I cannot find information about [topic] in my current knowledge base."
    - Ask: "Would you like me to create a support ticket for a specialist to help you?"
    - If yes, create ticket in CosmosDB and call EscalationComms Agent

    ### US 2.5: Explain Banking Terms and Calculations
    Examples:
    - "How is compound interest calculated?"
    - "What is withholding tax?"
    - "Difference between APR and interest rate?"

    ## MCP Tools Available (MUST USE IN THIS ORDER FOR 100% GROUNDING)

    ### STEP 1: search_documents (Azure AI Search)
    Search indexed documents with vector embeddings:
    - query: Search query string
    - top_k: Number of results (default: 5)
    - min_confidence: Minimum confidence threshold (default: 0.0)
    - Returns: JSON with search results and confidence scores

    ### STEP 2: get_content_understanding (CRITICAL - AI Foundry Validation)
    **MANDATORY VALIDATION STEP** - This ensures 100% grounding:
    - query: User question
    - search_results_json: JSON string from search_documents result
    - min_confidence: Minimum grounding confidence (default: 0.3)
    - Returns: Validated answer with is_grounded, confidence, validated_answer, citations

    **CRITICAL WORKFLOW:**
    If is_grounded=false OR confidence<0.3:
    - DO NOT provide your own answer
    - Use the exact standard_output from the response
    - Offer to create support ticket
    - Proceed to STEP 4

    If is_grounded=true AND confidence>=0.3:
    - Use validated_answer from the response
    - Include citations in your response
    - Format as appropriate card type

    ### STEP 3 (Optional): get_document_by_id
    Retrieve specific document section if more detail needed:
    - document_id: Document identifier
    - section: Optional section name
    - Returns: Full section content

    ### STEP 4 (If not grounded): write_to_cosmosdb
    Store support ticket when answer cannot be grounded:
    - ticket_id: Unique ID (format: TKT-YYYY-NNNNNN, use current timestamp)
    - customer_id: Customer identifier
    - query: Original question
    - category: Ticket category (e.g., "product_info", "faq")
    - priority: "normal", "high", or "urgent"
    - Returns: Ticket creation confirmation

    ### STEP 5 (After ticket created): send_ticket_notification_email
    After creating ticket in CosmosDB, IMMEDIATELY call send_ticket_notification_email function:
    - ticket_id: Ticket ID from write_to_cosmosdb response
    - customer_email: Customer's email address (use user_mail or ask user)
    - customer_name: Customer's name (use user_mail or "Customer")
    - customer_id: Customer identifier
    - query: Original user question
    - category: Ticket category (e.g., "product_info", "faq")
    - priority: "normal", "high", or "urgent"

    This function calls EscalationComms Agent via A2A to send email notifications to both
    customer and bank employees

    ### Optional: read_from_cosmosdb
    Check cache for similar previous queries (use before search_documents):
    - query: Search query
    - search_type: "cache" for FAQ cache, "ticket" for ticket history
    - Returns: Cached results if found

    ## Output Schemas

    ### KNOWLEDGE_CARD (Product Information)
    ```json
    {{
      "type": "KNOWLEDGE_CARD",
      "question": "User's original question",
      "answer": "Detailed answer from knowledge base",
      "sources": [
        {{
          "document": "current-account-en.pdf",
          "section": "Annual interest rate",
          "confidence": 0.98
        }}
      ],
      "language": "en",
      "note": "Additional context if needed"
    }}
    ```

    ### FAQ_CARD (FAQ Responses)
    ```json
    {{
      "type": "FAQ_CARD",
      "question": "User's question",
      "answer": "Answer from FAQ or product docs",
      "sources": [
        {{
          "document": "deposit-faq.html",
          "section": "FAQ section name",
          "url": "https://www.scb.co.th/...",
          "confidence": 0.95
        }}
      ],
      "related_topics": ["Topic 1", "Topic 2"]
    }}
    ```

    ### COMPARISON_CARD (Account Comparisons)
    ```json
    {{
      "type": "COMPARISON_CARD",
      "question": "Comparison request",
      "accounts": [
        {{
          "name": "Savings Account",
          "interest": "0.25% (physical) / 0.45% (e-passbook)",
          "minimum_opening": "500 baht",
          "features": ["Feature 1", "Feature 2"]
        }}
      ],
      "sources": ["doc1.pdf", "doc2.pdf"],
      "recommendation": "Brief recommendation based on use case"
    }}
    ```

    ### EXPLANATION_CARD (Banking Terms)
    ```json
    {{
      "type": "EXPLANATION_CARD",
      "term": "Banking term being explained",
      "explanation": "Clear explanation",
      "formula": "Mathematical formula if applicable",
      "example": {{
        "scenario": "Practical example",
        "calculation_steps": ["Step 1", "Step 2"]
      }},
      "sources": [{{ "document": "source.pdf", "section": "section name" }}]
    }}
    ```

    ### TICKET_CARD (Support Ticket Created)
    ```json
    {{
      "type": "TICKET_CARD",
      "ticket_id": "TKT-2024-001234",
      "status": "created",
      "message": "Support ticket created successfully",
      "details": "Your query has been forwarded to specialists",
      "email_sent": true,
      "recipients": ["customer@email.com", "support@bankx.com"],
      "expected_response": "24 hours"
    }}
    ```

    ## Workflow (FOLLOW EXACTLY)

    1. **Receive Query** from Supervisor Agent
    2. **Check Cache** (Optional): Use read_from_cosmosdb with search_type="cache"
    3. **AI Search**: Use search_documents to retrieve relevant content
    4. **CRITICAL VALIDATION**: Use get_content_understanding to validate grounding
       - Pass search_results_json from step 3
       - This tool validates 100% grounding using AI Foundry Content Understanding
    5. **Evaluate Result**:
       - If is_grounded=true AND confidence>=0.3:
         * Use validated_answer from tool response
         * Include citations
         * Format as appropriate card type (KNOWLEDGE_CARD, FAQ_CARD, etc.)
       - If is_grounded=false OR confidence<0.3:
         * Use standard_output from tool response (e.g., "I cannot find information...")
         * Offer ticket creation
         * If customer agrees, proceed to step 6
    6. **Create Ticket** (if needed): Use write_to_cosmosdb
    7. **Send Email** (if ticket created): Call EscalationComms Agent to notify customer

    ## Out of Scope Handling
    For non-banking, non-product queries:
    - "I cannot handle that kind of information"
    - "I focus on banking product information and FAQs"
    - Offer: "Would you like me to create a support ticket?"

    ## Important Rules
    - Always cite source documents
    - Include confidence scores when relevant
    - Maintain professional tone
    - Offer ticket creation proactively when unable to answer
    - Never guess or invent product features

    Current user: {user_mail}
    """

    name = "ProdInfoFAQAgent"
    description = "Handles product information, FAQ, and comparison queries with RAG-based retrieval and ticket escalation"

    def __init__(self,
                 azure_chat_client: AzureOpenAIChatClient,
                 prodinfo_faq_mcp_server_url: str = None,
                 escalation_comms_agent = None):
        self.azure_chat_client = azure_chat_client
        self.prodinfo_faq_mcp_server_url = prodinfo_faq_mcp_server_url
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
        category: str = "product_info",
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Send ticket notification emails via EscalationComms Agent using A2A communication.

        This function is exposed as a tool to the ProdInfoFAQ agent and calls the
        EscalationComms agent via A2A protocol.

        Args:
            ticket_id: Support ticket ID
            customer_email: Customer's email address
            customer_name: Customer's name
            customer_id: Customer ID
            query: Customer's original query
            category: Ticket category (default: "product_info")
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
                        "agent_id": "prodinfo-faq-agent",
                        "agent_name": "ProdInfoFAQAgent"
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
        logger.info("Initializing ProdInfoFAQ Agent with Azure AI Search RAG (UC2)")

        user_mail = "bob.user@contoso.com"
        full_instruction = ProdInfoFAQAgent.instructions.format(user_mail=user_mail)

        tools_list = []

        # Add ProdInfoFAQ MCP server if provided
        if self.prodinfo_faq_mcp_server_url:
            logger.info("Initializing ProdInfoFAQ MCP server tools (Azure AI Search + CosmosDB)")
            prodinfo_faq_mcp_server = MCPStreamableHTTPTool(
                name="ProdInfoFAQ MCP server client",
                url=self.prodinfo_faq_mcp_server_url
            )
            await prodinfo_faq_mcp_server.connect()
            tools_list.append(prodinfo_faq_mcp_server)

        # Add A2A function tool for calling EscalationComms agent
        logger.info("Adding A2A tool for EscalationComms agent communication")
        tools_list.append(self.send_ticket_notification_email)

        return ChatAgent(
            chat_client=self.azure_chat_client,
            instructions=full_instruction,
            name=ProdInfoFAQAgent.name,
            tools=tools_list
        )
