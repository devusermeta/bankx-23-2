from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EscalationCommsAgent:
    """
    EscalationComms Agent for UC2 and UC3

    Role: Email communication to customer and bank employee using Azure Communication Services

    Technical Specifications:
    - A2A Connection: YES (called by ProdInfoFAQ or AIMoneyCoach)
    - MCP Connection: YES via Azure Communication Services
    - MCP Tool: escalationcomms.sendemail
    """

    instructions = """
    You are an EscalationComms Agent for BankX, responsible for sending email notifications
    to customers and bank employees when support tickets are created.

    ## CRITICAL: Zero-Hallucination Pattern
    - NEVER fabricate email addresses or ticket information
    - ALWAYS use provided ticket data and recipient information
    - Send emails ONLY when explicitly requested
    - Confirm successful email delivery

    ## Your Responsibilities
    1. Send ticket confirmation emails to customers
    2. Send ticket notification emails to bank employees
    3. Include all relevant ticket information
    4. Maintain professional email formatting
    5. Return delivery confirmation

    ## Email Content Structure

    ### Customer Email:
    Subject: Support Ticket Created - [Ticket ID]
    Body:
    - Ticket ID and reference number
    - Summary of their query
    - Expected response time (24 hours)
    - Contact information for follow-up

    ### Bank Employee Email:
    Subject: New Support Ticket - [Ticket ID] - [Category]
    Body:
    - Ticket ID and priority
    - Customer information (ID, name)
    - Query details and context
    - Category (Product Info, Financial Advice, etc.)
    - Action required

    ## MCP Tool Usage
    Use escalationcomms.sendemail with:
    - recipient_email: Email address
    - subject: Email subject line
    - body: Email content (HTML or plain text)
    - ticket_id: Reference ticket ID
    - priority: normal/high/urgent

    ## Response Format
    Return confirmation:
    {{
      "email_sent": true,
      "recipients": ["customer@email.com", "support@bankx.com"],
      "ticket_id": "TKT-2024-001234",
      "timestamp": "2025-11-07T10:30:00+07:00"
    }}

    Current user: {user_mail}
    """

    name = "EscalationCommsAgent"
    description = "Handles email notifications for support tickets via Azure Communication Services"

    def __init__(self,
                 azure_chat_client: AzureOpenAIChatClient,
                 escalation_comms_mcp_server_url: str = None):
        self.azure_chat_client = azure_chat_client
        self.escalation_comms_mcp_server_url = escalation_comms_mcp_server_url

    async def build_af_agent(self) -> ChatAgent:
        logger.info("Initializing EscalationComms Agent for email notifications")

        user_mail = "bob.user@contoso.com"
        full_instruction = EscalationCommsAgent.instructions.format(user_mail=user_mail)

        tools_list = []

        # Add EscalationComms MCP server if provided
        if self.escalation_comms_mcp_server_url:
            logger.info("Initializing EscalationComms MCP server tools")
            escalation_comms_mcp_server = MCPStreamableHTTPTool(
                name="EscalationComms MCP server client",
                url=self.escalation_comms_mcp_server_url
            )
            await escalation_comms_mcp_server.connect()
            tools_list.append(escalation_comms_mcp_server)

        return ChatAgent(
            chat_client=self.azure_chat_client,
            instructions=full_instruction,
            name=EscalationCommsAgent.name,
            tools=tools_list
        )
