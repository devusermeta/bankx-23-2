from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from datetime import datetime

import logging


logger = logging.getLogger(__name__)

class TransactionAgent :
    instructions = """
    You are a Transaction Agent for BankX, specializing in transaction history, aggregations, and financial insights.

    ## CRITICAL: Zero-Hallucination Pattern
    - NEVER fabricate transaction data
    - ALWAYS use MCP tools to retrieve real data
    - Return ONLY structured outputs (TXN_TABLE, INSIGHTS_CARD, TXN_DETAIL)
    - NO conversational filler

    ## User Stories You Handle

    ### US 1.1: View Transactions
    User requests: "Show transactions for last week"
    1. Parse natural language date → ISO dates
    2. Call searchTransactions(accountId, fromDate, toDate)
    3. Return TXN_TABLE (structured JSON only)
    4. Call logDecision for audit

    ### US 1.2: Transaction Aggregations
    User requests: "How many transactions last week?"
    1. Determine metric: COUNT, SUM_IN, SUM_OUT, NET
    2. Call aggregateTransactions(accountId, fromDate, toDate, metricType)
    3. Return INSIGHTS_CARD
    4. Call logDecision for audit

    ### US 1.5: Transaction Details
    User requests: "Show details for TXN-064"
    1. Call getTransactionDetails(transactionId)
    2. Return TXN_DETAIL
    3. Call logDecision for audit

    ## Date Normalization (Week = Monday-Sunday)
    - "last week" → previous Monday-Sunday
    - "last Friday" → most recent Friday
    - Timezone: Asia/Bangkok (+07:00)

    ## Governance: ALWAYS call logDecision after each action
    Example:
    logDecision(
        conversationId="{conversation_id}",
        customerId="{customer_id}",
        agentName="TransactionAgent",
        action="VIEW_TRANSACTIONS",
        input={{"account_id": "CHK-001", "from_date": "2025-10-20", "to_date": "2025-10-26"}},
        output={{"type": "TXN_TABLE", "total_count": 10}},
        rationale="Retrieved 10 transactions for last week"
    )

    Current user: {user_mail}
    Current timestamp: {current_date_time}
    """
    name = "TransactionAgent"
    description = "Handles transaction history, aggregations, and financial insights with structured outputs"

    def __init__(self, azure_chat_client: AzureOpenAIChatClient,
                 account_mcp_server_url: str,
                 transaction_mcp_server_url: str,
                 audit_mcp_server_url: str = None
                  ):
        self.azure_chat_client = azure_chat_client
        self.account_mcp_server_url = account_mcp_server_url
        self.transaction_mcp_server_url = transaction_mcp_server_url
        self.audit_mcp_server_url = audit_mcp_server_url
      


    async def build_af_agent(self) -> ChatAgent:

      logger.info("Building request scoped transaction agent run ")

      user_mail="bob.user@contoso.com"
      current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      full_instruction = TransactionAgent.instructions.format(user_mail=user_mail, current_date_time=current_date_time)

      logger.info("Initializing Account MCP server tools ")
      account_mcp_server = MCPStreamableHTTPTool(
        name="Account MCP server client",
        url=self.account_mcp_server_url
     )
      await account_mcp_server.connect()

      logger.info("Initializing Transaction MCP server tools ")
      transaction_mcp_server = MCPStreamableHTTPTool(
        name="Transaction MCP server client",
        url=self.transaction_mcp_server_url
     )
      await transaction_mcp_server.connect()

      tools_list = [account_mcp_server, transaction_mcp_server]

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
            name=TransactionAgent.name,
            tools=tools_list,
        )