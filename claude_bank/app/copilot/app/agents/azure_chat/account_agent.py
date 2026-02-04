from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool

import logging


logger = logging.getLogger(__name__)

class AccountAgent :
    instructions = """
    You are an Account Agent for BankX, specializing in account details, balances, and transaction limits.

    ## CRITICAL: Zero-Hallucination Pattern
    - NEVER fabricate account data
    - ALWAYS use MCP tools to retrieve real data
    - Return ONLY structured outputs (BALANCE_CARD)
    - NO conversational filler

    ## User Story You Handle

    ### US 1.3: Balance and Limits
    User requests: "What's my balance?" or "Show my transfer limits"
    1. Call getAccountDetails(accountId) for balance
    2. Call getAccountLimits(accountId) for limits (Limits Service port 8073)
    3. Return BALANCE_CARD structured output
    4. Call logDecision for audit

    ## Output Schema: BALANCE_CARD
    ```json
    {{
      "type": "BALANCE_CARD",
      "account_id": "CHK-001",
      "account_name": "Somchai's Checking",
      "currency": "THB",
      "ledger_balance": 100950.00,
      "available_balance": 100950.00,
      "limits": {{
        "per_transaction_limit": 50000.00,
        "daily_limit": 200000.00,
        "remaining_today": 200000.00,
        "daily_used": 0.00,
        "utilization_percent": 0.0
      }},
      "advisory": "You have full daily limit available. Per-transaction limit is 50,000 THB."
    }}
    ```

    ## Governance: ALWAYS call logDecision after action
    Example:
    logDecision(
        conversationId="{{conversation_id}}",
        customerId="{{customer_id}}",
        agentName="AccountAgent",
        action="VIEW_BALANCE",
        input={{"account_id": "CHK-001"}},
        output={{"type": "BALANCE_CARD", "available_balance": 100950.00}},
        rationale="Retrieved balance and limits. Daily limit fully available (0% used)."
    )

    Current user: {user_mail}
    """
    name = "AccountAgent"
    description = "Handles account details, balances, and transaction limits with structured outputs"

    def __init__(self, azure_chat_client: AzureOpenAIChatClient,
                 account_mcp_server_url: str,
                 limits_mcp_server_url: str = None,
                 audit_mcp_server_url: str = None):
        self.azure_chat_client = azure_chat_client
        self.account_mcp_server_url = account_mcp_server_url
        self.limits_mcp_server_url = limits_mcp_server_url
        self.audit_mcp_server_url = audit_mcp_server_url



    async def build_af_agent(self)-> ChatAgent:

      logger.info("Initializing Account Agent connection for account api ")

      user_mail="bob.user@contoso.com"
      full_instruction = AccountAgent.instructions.format(user_mail=user_mail)

      logger.info("Initializing Account MCP server tools ")
      account_mcp_server = MCPStreamableHTTPTool(
            name="Account MCP server client",
            url=self.account_mcp_server_url)
      await account_mcp_server.connect()

      tools_list = [account_mcp_server]

      # Add Limits MCP server if provided (for balance and limits)
      if self.limits_mcp_server_url:
          logger.info("Initializing Limits MCP server tools ")
          limits_mcp_server = MCPStreamableHTTPTool(
            name="Limits MCP server client",
            url=self.limits_mcp_server_url
         )
          await limits_mcp_server.connect()
          tools_list.append(limits_mcp_server)

      # Add Audit MCP server if provided (for governance logging)
      if self.audit_mcp_server_url:
          logger.info("Initializing Audit MCP server tools ")
          audit_mcp_server = MCPStreamableHTTPTool(
            name="Audit MCP server client",
            url=self.audit_mcp_server_url
         )
          await audit_mcp_server.connect()
          tools_list.append(audit_mcp_server)

      return ChatAgent(
            chat_client=self.azure_chat_client,
            instructions=full_instruction,
            name=AccountAgent.name,
            tools=tools_list
        )
    
